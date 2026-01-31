"""Local filesystem-based space implementation.

Provides sandboxed workspace directories for MVP deployment.
Uses Claude SDK's SandboxSettings to enforce path isolation.

Reference: docs/architect/scalable-agent-architecture.md
"""

from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID

from pilot_space.spaces.base import (
    SpaceContext,
    SpaceInterface,
    SpacePreparationError,
)
from pilot_space.spaces.bootstrapper import ProjectBootstrapper

logger = logging.getLogger(__name__)


class LocalFileSystemSpace(SpaceInterface):
    """Local filesystem-based space for MVP deployment.

    Creates user workspaces under a configurable storage root:
    STORAGE_ROOT/{workspace_id}/{user_id}/

    Features:
    - Persistent storage between sessions
    - System skill hydration via ProjectBootstrapper
    - Claude SDK sandbox isolation via CWD binding

    Attributes:
        storage_root: Base path for all user workspaces
        workspace_id: Workspace UUID for directory structure
        user_id: User UUID for directory structure
        bootstrapper: ProjectBootstrapper for skill hydration
    """

    def __init__(
        self,
        storage_root: Path,
        workspace_id: UUID,
        user_id: UUID,
        bootstrapper: ProjectBootstrapper,
    ) -> None:
        """Initialize local space.

        Args:
            storage_root: Base directory for all user workspaces
            workspace_id: Workspace UUID for this space
            user_id: User UUID for this space
            bootstrapper: ProjectBootstrapper instance for hydration
        """
        self._storage_root = storage_root
        self._workspace_id = workspace_id
        self._user_id = user_id
        self._bootstrapper = bootstrapper
        self._context: SpaceContext | None = None

    @property
    def space_path(self) -> Path:
        """Get the path for this user's workspace.

        Returns:
            Path to STORAGE_ROOT/{workspace_id}/{user_id}/
        """
        return self._storage_root / str(self._workspace_id) / str(self._user_id)

    async def prepare(self) -> SpaceContext:
        """Prepare local filesystem space.

        Creates the workspace directory if needed and hydrates
        system skills/commands/rules.

        Returns:
            SpaceContext with workspace path and environment.

        Raises:
            SpacePreparationError: If directory creation or hydration fails.
        """
        try:
            # Create workspace directory
            self.space_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Prepared space at {self.space_path}")

            # Hydrate .claude directory with system content
            await self._bootstrapper.hydrate(self.space_path)

            # Create context
            self._context = SpaceContext(
                id=f"{self._workspace_id}:{self._user_id}",
                path=self.space_path,
                env={
                    "PILOT_WORKSPACE_ID": str(self._workspace_id),
                    "PILOT_USER_ID": str(self._user_id),
                    "PILOT_SPACE_TYPE": "local",
                },
            )

            return self._context

        except OSError as e:
            raise SpacePreparationError(
                f"Failed to prepare local space at {self.space_path}: {e}"
            ) from e

    async def cleanup(self) -> None:
        """Cleanup local space.

        For local spaces, cleanup is a no-op since content persists.
        The directory remains for future sessions.
        """
        logger.debug(f"Cleanup called for local space {self.space_path} (no-op)")
        self._context = None

    def exists(self) -> bool:
        """Check if this space already exists.

        Returns:
            True if workspace directory exists.
        """
        return self.space_path.exists()

    async def delete(self) -> None:
        """Delete this workspace entirely.

        Use with caution - this removes all user content.

        Raises:
            OSError: If deletion fails.
        """
        if self.space_path.exists():
            import shutil

            shutil.rmtree(self.space_path)
            logger.warning(f"Deleted space at {self.space_path}")
