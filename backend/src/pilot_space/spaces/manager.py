"""Space manager factory service.

Provides the appropriate SpaceInterface implementation based on
deployment mode and configuration.

Reference: docs/architect/scalable-agent-architecture.md
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from uuid import UUID

from pilot_space.spaces.base import SpaceInterface
from pilot_space.spaces.bootstrapper import ProjectBootstrapper
from pilot_space.spaces.local import LocalFileSystemSpace

logger = logging.getLogger(__name__)


class SpaceManager:
    """Factory service for obtaining SpaceInterface implementations.

    Determines the appropriate space implementation based on:
    - PILOT_DEPLOYMENT_MODE environment variable
    - Available infrastructure (K8s, local storage)

    Usage:
        manager = SpaceManager(bootstrapper)
        space = manager.get_space(workspace_id, user_id)
        async with space.session() as context:
            # Use context.path as CWD for SDK
            pass

    Attributes:
        bootstrapper: ProjectBootstrapper for hydrating workspaces
        deployment_mode: Current deployment mode (local, container)
        storage_root: Base path for local workspaces
    """

    def __init__(
        self,
        bootstrapper: ProjectBootstrapper,
        storage_root: Path | str | None = None,
        deployment_mode: str | None = None,
    ) -> None:
        """Initialize space manager.

        Args:
            bootstrapper: ProjectBootstrapper for workspace hydration
            storage_root: Override for PILOT_STORAGE_ROOT env var
            deployment_mode: Override for PILOT_DEPLOYMENT_MODE env var
        """
        self._bootstrapper = bootstrapper
        self._deployment_mode = deployment_mode or os.getenv(
            "PILOT_DEPLOYMENT_MODE", "local"
        )

        # Determine storage root
        if storage_root:
            self._storage_root = Path(storage_root)
        else:
            default_root = Path.home() / ".pilot-space" / "workspaces"
            self._storage_root = Path(
                os.getenv("PILOT_STORAGE_ROOT", str(default_root))
            )

        # Ensure storage root exists
        self._storage_root.mkdir(parents=True, exist_ok=True)
        logger.info(
            f"SpaceManager initialized: mode={self._deployment_mode}, "
            f"root={self._storage_root}"
        )

    @property
    def deployment_mode(self) -> str:
        """Get current deployment mode."""
        return self._deployment_mode

    @property
    def storage_root(self) -> Path:
        """Get storage root path."""
        return self._storage_root

    def get_space(self, workspace_id: UUID, user_id: UUID) -> SpaceInterface:
        """Get appropriate space implementation for user/workspace.

        Args:
            workspace_id: Workspace UUID
            user_id: User UUID

        Returns:
            SpaceInterface implementation (LocalFileSystemSpace for MVP)

        Raises:
            NotImplementedError: If deployment mode is not supported
        """
        if self._deployment_mode == "container":
            # Future: ContainerSpace for K8s/MicroVM
            raise NotImplementedError(
                "ContainerSpace not yet implemented. "
                "Set PILOT_DEPLOYMENT_MODE=local for MVP."
            )

        return LocalFileSystemSpace(
            storage_root=self._storage_root,
            workspace_id=workspace_id,
            user_id=user_id,
            bootstrapper=self._bootstrapper,
        )

    def get_existing_space(
        self, workspace_id: UUID, user_id: UUID
    ) -> LocalFileSystemSpace | None:
        """Get existing space if it exists.

        Unlike get_space(), this doesn't create a new space if it
        doesn't exist.

        Args:
            workspace_id: Workspace UUID
            user_id: User UUID

        Returns:
            LocalFileSystemSpace if exists, None otherwise
        """
        space = LocalFileSystemSpace(
            storage_root=self._storage_root,
            workspace_id=workspace_id,
            user_id=user_id,
            bootstrapper=self._bootstrapper,
        )

        if space.exists():
            return space
        return None

    def list_workspaces(self) -> list[UUID]:
        """List all workspace IDs that have spaces.

        Returns:
            List of workspace UUIDs with existing spaces.
        """
        workspaces = []
        if self._storage_root.exists():
            for ws_dir in self._storage_root.iterdir():
                if ws_dir.is_dir():
                    try:
                        workspaces.append(UUID(ws_dir.name))
                    except ValueError:
                        continue  # Skip non-UUID directories
        return workspaces

    def list_user_spaces(self, workspace_id: UUID) -> list[UUID]:
        """List all user IDs with spaces in a workspace.

        Args:
            workspace_id: Workspace UUID to list

        Returns:
            List of user UUIDs with spaces in this workspace.
        """
        users = []
        ws_dir = self._storage_root / str(workspace_id)
        if ws_dir.exists():
            for user_dir in ws_dir.iterdir():
                if user_dir.is_dir():
                    try:
                        users.append(UUID(user_dir.name))
                    except ValueError:
                        continue  # Skip non-UUID directories
        return users


def create_space_manager(templates_dir: Path | str | None = None) -> SpaceManager:
    """Factory function to create a configured SpaceManager.

    Args:
        templates_dir: Path to templates directory. If None, uses
            backend/src/pilot_space/ai/templates/

    Returns:
        Configured SpaceManager instance.
    """
    if templates_dir is None:
        # Default to package templates directory
        templates_dir = (
            Path(__file__).parent.parent / "ai" / "templates"
        )

    bootstrapper = ProjectBootstrapper(templates_dir)
    return SpaceManager(bootstrapper)
