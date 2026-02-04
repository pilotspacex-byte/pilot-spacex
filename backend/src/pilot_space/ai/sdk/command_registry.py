"""Command registry for slash commands in .claude/commands/.

Provides discovery, parsing, and execution of file-based slash commands.
Commands are simpler than skills - they represent direct actions rather
than multi-step AI workflows.

Reference: docs/architect/claude-agent-sdk-architecture.md
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class CommandParameter:
    """Parameter definition for a command.

    Attributes:
        name: Parameter name (used in parsing)
        description: Human-readable description
        required: Whether parameter is required
        type: Parameter type (string, number, boolean, file)
        default: Default value if not provided
    """

    name: str
    description: str = ""
    required: bool = False
    type: str = "string"
    default: Any = None


@dataclass
class CommandDefinition:
    """Parsed command definition from .md file.

    Commands are defined in .claude/commands/{name}.md files with
    YAML frontmatter containing metadata and markdown body with
    detailed instructions.

    Attributes:
        name: Canonical command name (e.g., "implement")
        description: Brief description for discovery
        category: Category for grouping (development, workflow, etc.)
        parameters: List of parameter definitions
        aliases: Alternative trigger names (e.g., ["dev", "d"])
        content: Full markdown content including instructions
        file_path: Path to the source .md file
    """

    name: str
    description: str
    category: str = "general"
    parameters: list[CommandParameter] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    content: str = ""
    file_path: Path | None = None

    @property
    def triggers(self) -> list[str]:
        """Get all trigger patterns for this command.

        Returns:
            List of slash command triggers (e.g., ["/implement", "/dev"])
        """
        return [f"/{self.name}"] + [f"/{alias}" for alias in self.aliases]

    def matches(self, input_text: str) -> bool:
        """Check if input matches this command's trigger.

        Args:
            input_text: User input text

        Returns:
            True if input starts with any of this command's triggers
        """
        input_lower = input_text.strip().lower()
        for trigger in self.triggers:
            if input_lower.startswith(trigger.lower()):
                # Check for word boundary (space or end of string)
                rest = input_lower[len(trigger) :]
                if not rest or rest[0].isspace():
                    return True
        return False

    def parse_arguments(self, input_text: str) -> dict[str, Any]:
        """Parse arguments from input text.

        Args:
            input_text: Full user input (e.g., "/implement src/main.py")

        Returns:
            Dictionary mapping parameter names to values
        """
        # Remove the trigger from input
        remaining = input_text.strip()
        for trigger in self.triggers:
            if remaining.lower().startswith(trigger.lower()):
                remaining = remaining[len(trigger) :].strip()
                break

        # Simple positional argument parsing
        # Future: Support --flags and key=value syntax
        words = remaining.split() if remaining else []
        args: dict[str, Any] = {}

        for i, param in enumerate(self.parameters):
            if i < len(words):
                args[param.name] = words[i]
            elif param.default is not None:
                args[param.name] = param.default

        return args

    def to_sdk_format(self) -> dict[str, Any]:
        """Format for Claude SDK command discovery.

        Returns:
            Dictionary suitable for SDK's command system
        """
        return {
            "name": self.name,
            "description": self.description,
            "triggers": self.triggers,
            "parameters": [
                {
                    "name": p.name,
                    "description": p.description,
                    "required": p.required,
                    "type": p.type,
                }
                for p in self.parameters
            ],
        }


class CommandRegistry:
    """Registry for slash commands in .claude/commands/.

    Discovers, parses, and caches command definitions from markdown files.
    Commands must have YAML frontmatter with at minimum `name` and
    `description` fields.

    Attributes:
        commands_dir: Path to commands directory
    """

    def __init__(self, commands_dir: Path | str) -> None:
        """Initialize command registry.

        Args:
            commands_dir: Path to .claude/commands/ directory
        """
        self._commands_dir = Path(commands_dir)
        self._cache: dict[str, CommandDefinition] = {}
        self._alias_map: dict[str, str] = {}  # alias -> canonical name
        self._loaded = False

    def _discover_commands(self) -> None:
        """Discover all command .md files."""
        if not self._commands_dir.exists():
            logger.debug(f"Commands directory not found: {self._commands_dir}")
            return

        for cmd_file in self._commands_dir.glob("*.md"):
            # Skip metadata files
            if cmd_file.name in ("CLAUDE.md", "README.md"):
                continue

            try:
                cmd_def = self._parse_command_file(cmd_file)
                self._cache[cmd_def.name] = cmd_def

                # Build alias map
                for alias in cmd_def.aliases:
                    self._alias_map[alias] = cmd_def.name

                logger.debug(f"Loaded command: /{cmd_def.name}")

            except Exception as e:
                logger.warning(f"Failed to parse command {cmd_file}: {e}")
                continue

    async def async_discover_commands(self) -> None:
        """Async version of _discover_commands for use in async contexts."""
        if not self._commands_dir.exists():
            logger.debug(f"Commands directory not found: {self._commands_dir}")
            return

        loop = asyncio.get_event_loop()

        for cmd_file in self._commands_dir.glob("*.md"):
            # Skip metadata files
            if cmd_file.name in ("CLAUDE.md", "README.md"):
                continue

            try:
                cmd_def = await loop.run_in_executor(None, self._parse_command_file, cmd_file)
                self._cache[cmd_def.name] = cmd_def

                # Build alias map
                for alias in cmd_def.aliases:
                    self._alias_map[alias] = cmd_def.name

                logger.debug(f"Loaded command: /{cmd_def.name}")

            except Exception as e:
                logger.warning(f"Failed to parse command {cmd_file}: {e}")
                continue

    def _parse_command_file(self, cmd_file: Path) -> CommandDefinition:
        """Parse command .md file.

        Args:
            cmd_file: Path to command markdown file

        Returns:
            Parsed CommandDefinition

        Raises:
            ValueError: If file is missing required frontmatter
        """
        content = cmd_file.read_text(encoding="utf-8")

        # Extract YAML frontmatter
        match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
        if not match:
            raise ValueError(f"Missing YAML frontmatter in {cmd_file}")

        frontmatter = yaml.safe_load(match.group(1))

        if not frontmatter:
            raise ValueError(f"Empty frontmatter in {cmd_file}")

        name = frontmatter.get("name") or cmd_file.stem
        description = frontmatter.get("description", "")

        if not description:
            logger.warning(f"Command {name} has no description")

        # Parse parameters
        params = []
        for p in frontmatter.get("parameters", []):
            params.append(
                CommandParameter(
                    name=p.get("name", ""),
                    description=p.get("description", ""),
                    required=p.get("required", False),
                    type=p.get("type", "string"),
                    default=p.get("default"),
                )
            )

        return CommandDefinition(
            name=name,
            description=description,
            category=frontmatter.get("category", "general"),
            parameters=params,
            aliases=frontmatter.get("aliases", []),
            content=content,
            file_path=cmd_file,
        )

    def get_command(self, name: str) -> CommandDefinition | None:
        """Get command by name or alias.

        Args:
            name: Command name or alias

        Returns:
            CommandDefinition if found, None otherwise
        """
        if not self._loaded:
            self._discover_commands()
            self._loaded = True

        # Check alias map first
        canonical = self._alias_map.get(name, name)
        return self._cache.get(canonical)

    def find_matching_command(self, input_text: str) -> CommandDefinition | None:
        """Find command matching input text.

        Args:
            input_text: User input (e.g., "/dev src/main.py")

        Returns:
            Matching CommandDefinition or None
        """
        if not self._loaded:
            self._discover_commands()
            self._loaded = True

        for cmd in self._cache.values():
            if cmd.matches(input_text):
                return cmd
        return None

    def list_commands(self) -> list[CommandDefinition]:
        """List all available commands.

        Returns:
            List of all discovered CommandDefinitions
        """
        if not self._loaded:
            self._discover_commands()
            self._loaded = True
        return list(self._cache.values())

    def list_by_category(self) -> dict[str, list[CommandDefinition]]:
        """List commands grouped by category.

        Returns:
            Dictionary mapping category to list of commands
        """
        if not self._loaded:
            self._discover_commands()
            self._loaded = True

        by_category: dict[str, list[CommandDefinition]] = {}
        for cmd in self._cache.values():
            if cmd.category not in by_category:
                by_category[cmd.category] = []
            by_category[cmd.category].append(cmd)
        return by_category

    def reload(self) -> None:
        """Reload all commands from filesystem.

        Useful for development when commands are being modified.
        """
        self._cache.clear()
        self._alias_map.clear()
        self._loaded = False
        self._discover_commands()
        self._loaded = True
        logger.info(f"Reloaded {len(self._cache)} commands")
