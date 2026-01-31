"""Unit tests for CommandRegistry.

Tests cover:
- CommandParameter dataclass
- CommandDefinition parsing and matching
- CommandRegistry discovery and caching
- Argument parsing
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from pilot_space.ai.sdk.command_registry import (
    CommandDefinition,
    CommandParameter,
    CommandRegistry,
)


class TestCommandParameter:
    """Tests for CommandParameter dataclass."""

    def test_default_values(self) -> None:
        """Test CommandParameter has correct defaults."""
        param = CommandParameter(name="target")

        assert param.name == "target"
        assert param.description == ""
        assert param.required is False
        assert param.type == "string"
        assert param.default is None

    def test_custom_values(self) -> None:
        """Test CommandParameter accepts custom values."""
        param = CommandParameter(
            name="file",
            description="Target file to process",
            required=True,
            type="file",
            default="main.py",
        )

        assert param.name == "file"
        assert param.description == "Target file to process"
        assert param.required is True
        assert param.type == "file"
        assert param.default == "main.py"


class TestCommandDefinition:
    """Tests for CommandDefinition dataclass."""

    @pytest.fixture
    def basic_command(self) -> CommandDefinition:
        """Create a basic command for testing."""
        return CommandDefinition(
            name="implement",
            description="Implement a feature",
            category="development",
            parameters=[
                CommandParameter(name="target", description="Target file"),
                CommandParameter(name="type", default="feature"),
            ],
            aliases=["dev", "imp"],
        )

    def test_triggers_includes_name_and_aliases(
        self, basic_command: CommandDefinition
    ) -> None:
        """Test triggers property includes name and all aliases."""
        triggers = basic_command.triggers

        assert "/implement" in triggers
        assert "/dev" in triggers
        assert "/imp" in triggers
        assert len(triggers) == 3

    def test_matches_canonical_name(self, basic_command: CommandDefinition) -> None:
        """Test matches returns True for canonical name."""
        assert basic_command.matches("/implement file.py") is True
        assert basic_command.matches("/implement") is True

    def test_matches_aliases(self, basic_command: CommandDefinition) -> None:
        """Test matches returns True for aliases."""
        assert basic_command.matches("/dev file.py") is True
        assert basic_command.matches("/imp") is True

    def test_matches_case_insensitive(self, basic_command: CommandDefinition) -> None:
        """Test matches is case insensitive."""
        assert basic_command.matches("/IMPLEMENT file.py") is True
        assert basic_command.matches("/Dev file.py") is True

    def test_matches_with_whitespace(self, basic_command: CommandDefinition) -> None:
        """Test matches handles leading whitespace."""
        assert basic_command.matches("  /implement file.py") is True

    def test_does_not_match_partial(self, basic_command: CommandDefinition) -> None:
        """Test matches requires word boundary."""
        assert basic_command.matches("/implements file.py") is False
        assert basic_command.matches("/implementation") is False

    def test_does_not_match_other_commands(
        self, basic_command: CommandDefinition
    ) -> None:
        """Test matches returns False for other commands."""
        assert basic_command.matches("/other command") is False
        assert basic_command.matches("not a command") is False

    def test_parse_arguments_positional(
        self, basic_command: CommandDefinition
    ) -> None:
        """Test parse_arguments extracts positional arguments."""
        args = basic_command.parse_arguments("/implement file.py feature")

        assert args["target"] == "file.py"
        assert args["type"] == "feature"

    def test_parse_arguments_with_defaults(
        self, basic_command: CommandDefinition
    ) -> None:
        """Test parse_arguments uses defaults for missing args."""
        args = basic_command.parse_arguments("/implement file.py")

        assert args["target"] == "file.py"
        assert args["type"] == "feature"  # Default value

    def test_parse_arguments_empty_input(
        self, basic_command: CommandDefinition
    ) -> None:
        """Test parse_arguments handles command with no args."""
        args = basic_command.parse_arguments("/implement")

        assert args.get("target") is None
        assert args["type"] == "feature"  # Default value

    def test_parse_arguments_with_alias(
        self, basic_command: CommandDefinition
    ) -> None:
        """Test parse_arguments works with alias trigger."""
        args = basic_command.parse_arguments("/dev file.py")

        assert args["target"] == "file.py"

    def test_to_sdk_format(self, basic_command: CommandDefinition) -> None:
        """Test to_sdk_format returns correctly structured dict."""
        sdk_format = basic_command.to_sdk_format()

        assert sdk_format["name"] == "implement"
        assert sdk_format["description"] == "Implement a feature"
        assert "/implement" in sdk_format["triggers"]
        assert len(sdk_format["parameters"]) == 2
        assert sdk_format["parameters"][0]["name"] == "target"


class TestCommandRegistry:
    """Tests for CommandRegistry."""

    @pytest.fixture
    def temp_commands_dir(self) -> Path:
        """Create a temporary commands directory with sample commands."""
        with tempfile.TemporaryDirectory() as tmpdir:
            commands_dir = Path(tmpdir)

            # Create a valid command file
            (commands_dir / "implement.md").write_text(
                """---
name: implement
description: Implement a feature
category: development
parameters:
  - name: target
    description: Target file
    required: false
aliases:
  - dev
  - imp
---

# Command: /implement

Implement features in the codebase.
"""
            )

            # Create another command
            (commands_dir / "test.md").write_text(
                """---
name: test
description: Run tests
category: testing
---

# Command: /test

Run the test suite.
"""
            )

            # Create CLAUDE.md (should be skipped)
            (commands_dir / "CLAUDE.md").write_text("# Metadata\n")

            yield commands_dir

    @pytest.fixture
    def registry(self, temp_commands_dir: Path) -> CommandRegistry:
        """Create registry with temp commands."""
        return CommandRegistry(temp_commands_dir)

    def test_get_command_by_name(self, registry: CommandRegistry) -> None:
        """Test get_command returns command by name."""
        cmd = registry.get_command("implement")

        assert cmd is not None
        assert cmd.name == "implement"
        assert cmd.description == "Implement a feature"

    def test_get_command_by_alias(self, registry: CommandRegistry) -> None:
        """Test get_command returns command by alias."""
        cmd = registry.get_command("dev")

        assert cmd is not None
        assert cmd.name == "implement"

    def test_get_command_returns_none_for_unknown(
        self, registry: CommandRegistry
    ) -> None:
        """Test get_command returns None for unknown command."""
        cmd = registry.get_command("unknown")

        assert cmd is None

    def test_find_matching_command(self, registry: CommandRegistry) -> None:
        """Test find_matching_command finds command from input."""
        cmd = registry.find_matching_command("/implement file.py")

        assert cmd is not None
        assert cmd.name == "implement"

    def test_find_matching_command_with_alias(self, registry: CommandRegistry) -> None:
        """Test find_matching_command works with aliases."""
        cmd = registry.find_matching_command("/dev file.py")

        assert cmd is not None
        assert cmd.name == "implement"

    def test_find_matching_command_returns_none(
        self, registry: CommandRegistry
    ) -> None:
        """Test find_matching_command returns None for no match."""
        cmd = registry.find_matching_command("/unknown command")

        assert cmd is None

    def test_list_commands(self, registry: CommandRegistry) -> None:
        """Test list_commands returns all commands."""
        commands = registry.list_commands()

        assert len(commands) == 2
        names = [cmd.name for cmd in commands]
        assert "implement" in names
        assert "test" in names

    def test_list_by_category(self, registry: CommandRegistry) -> None:
        """Test list_by_category groups commands by category."""
        by_category = registry.list_by_category()

        assert "development" in by_category
        assert "testing" in by_category
        assert len(by_category["development"]) == 1
        assert len(by_category["testing"]) == 1

    def test_skips_claude_md(self, registry: CommandRegistry) -> None:
        """Test CLAUDE.md is not parsed as command."""
        commands = registry.list_commands()
        names = [cmd.name for cmd in commands]

        assert "CLAUDE" not in names

    def test_reload_refreshes_cache(
        self, temp_commands_dir: Path, registry: CommandRegistry
    ) -> None:
        """Test reload refreshes the command cache."""
        # Initial load
        commands = registry.list_commands()
        assert len(commands) == 2

        # Add new command file
        (temp_commands_dir / "new-command.md").write_text(
            """---
name: new-command
description: A new command
---

# New Command
"""
        )

        # Reload
        registry.reload()
        commands = registry.list_commands()

        assert len(commands) == 3

    def test_handles_invalid_command_files(self) -> None:
        """Test registry skips invalid command files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            commands_dir = Path(tmpdir)

            # Invalid: no frontmatter
            (commands_dir / "invalid.md").write_text("# No frontmatter")

            # Valid command
            (commands_dir / "valid.md").write_text(
                """---
name: valid
description: Valid command
---

# Valid
"""
            )

            registry = CommandRegistry(commands_dir)
            commands = registry.list_commands()

            assert len(commands) == 1
            assert commands[0].name == "valid"

    def test_handles_missing_directory(self) -> None:
        """Test registry handles missing commands directory."""
        registry = CommandRegistry(Path("/nonexistent/path"))
        commands = registry.list_commands()

        assert commands == []

    def test_command_has_content(self, registry: CommandRegistry) -> None:
        """Test parsed command includes full markdown content."""
        cmd = registry.get_command("implement")

        assert cmd is not None
        assert "# Command: /implement" in cmd.content
        assert "---" in cmd.content  # Frontmatter included

    def test_command_has_file_path(self, registry: CommandRegistry) -> None:
        """Test parsed command includes source file path."""
        cmd = registry.get_command("implement")

        assert cmd is not None
        assert cmd.file_path is not None
        assert cmd.file_path.name == "implement.md"
