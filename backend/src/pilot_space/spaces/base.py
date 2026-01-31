"""Base interfaces for Space abstractions.

Defines the SpaceInterface contract that enables the transition from
Local (MVP) to Distributed (Scale) deployments without changing agent logic.

Reference: docs/architect/scalable-agent-architecture.md
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SpaceContext:
    """Context for an initialized user space.

    Provides all information needed by the Claude SDK to operate
    within a sandboxed workspace environment.

    Attributes:
        id: Unique identifier for this space instance
        path: Absolute path to workspace root (CWD for SDK)
        env: Environment variables to inject into SDK execution
    """

    id: str
    path: Path
    env: dict[str, str] = field(default_factory=dict)

    @property
    def claude_dir(self) -> Path:
        """Path to .claude directory within space."""
        return self.path / ".claude"

    @property
    def skills_dir(self) -> Path:
        """Path to skills directory."""
        return self.claude_dir / "skills"

    @property
    def commands_dir(self) -> Path:
        """Path to commands directory."""
        return self.claude_dir / "commands"

    @property
    def rules_dir(self) -> Path:
        """Path to rules directory."""
        return self.claude_dir / "rules"

    @property
    def hooks_file(self) -> Path:
        """Path to hooks.json configuration file."""
        return self.claude_dir / "hooks.json"

    def to_sdk_env(self) -> dict[str, str]:
        """Get environment variables for SDK execution.

        Returns:
            Dictionary of environment variables including space context.
        """
        return {
            **self.env,
            "PILOT_SPACE_ID": self.id,
            "PILOT_SPACE_PATH": str(self.path),
        }


class SpaceInterface(ABC):
    """Abstract contract for a User Space.

    Implementations provide workspace isolation for agent execution.
    The lifecycle is: prepare() → use → cleanup()

    MVP: LocalFileSystemSpace (local directory)
    Scale: ContainerSpace (K8s Pod or Firecracker MicroVM)
    """

    @abstractmethod
    async def prepare(self) -> SpaceContext:
        """Hydrate and ready the environment.

        This method:
        1. Creates/validates the workspace directory
        2. Hydrates system skills/commands/rules
        3. Returns context with paths and environment

        Returns:
            SpaceContext with initialized workspace information.

        Raises:
            SpacePreparationError: If space cannot be prepared.
        """

    @abstractmethod
    async def cleanup(self) -> None:
        """Persist state and teardown.

        This method:
        1. Saves any ephemeral state (for container spaces)
        2. Releases resources
        3. Optionally archives workspace content

        Note: LocalFileSystemSpace typically does nothing here
        as local workspaces persist between sessions.
        """

    @asynccontextmanager
    async def session(self) -> AsyncIterator[SpaceContext]:
        """Context manager for space lifecycle.

        Usage:
            async with space.session() as context:
                # context.path is the workspace root
                sdk_options = configure_sdk_for_space(context)
                async for message in query(..., options=sdk_options):
                    yield message
            # cleanup() called automatically

        Yields:
            SpaceContext for the active session.
        """
        context = await self.prepare()
        try:
            yield context
        finally:
            await self.cleanup()


class SpaceError(Exception):
    """Base exception for space-related errors."""


class SpacePreparationError(SpaceError):
    """Raised when space preparation fails."""


class SpaceNotFoundError(SpaceError):
    """Raised when a space cannot be found."""
