"""Repository for EditorPlugin entities.

Provides workspace-scoped CRUD operations for editor plugins.
Primary query patterns:
- list_by_workspace: all non-deleted plugins for admin list
- get_enabled_by_workspace: hot-path for editor bootstrap
- get_by_name: lookup by (workspace_id, name) business key

Source: Phase 45, PLUG-01..03
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import and_, select

from pilot_space.infrastructure.database.models.editor_plugin import EditorPlugin
from pilot_space.infrastructure.database.repositories.base import BaseRepository

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class EditorPluginRepository(BaseRepository[EditorPlugin]):
    """Repository for EditorPlugin entities.

    All write operations use flush() (no commit) -- callers own transaction
    boundaries via the session context.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, EditorPlugin)

    async def list_by_workspace(
        self,
        workspace_id: UUID,
    ) -> Sequence[EditorPlugin]:
        """Get all non-deleted editor plugins for a workspace.

        Ordered by display_name ascending for consistent UI ordering.

        Args:
            workspace_id: The workspace UUID.

        Returns:
            All non-deleted EditorPlugin rows for the workspace.
        """
        query = (
            select(EditorPlugin)
            .where(
                and_(
                    EditorPlugin.workspace_id == workspace_id,
                    EditorPlugin.is_deleted == False,  # noqa: E712
                )
            )
            .order_by(EditorPlugin.display_name.asc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_enabled_by_workspace(
        self,
        workspace_id: UUID,
    ) -> Sequence[EditorPlugin]:
        """Get enabled editor plugins for a workspace (editor bootstrap).

        Returns only rows where status='enabled' AND is_deleted=False.

        Args:
            workspace_id: The workspace UUID.

        Returns:
            Enabled EditorPlugin rows ordered by display_name.
        """
        query = (
            select(EditorPlugin)
            .where(
                and_(
                    EditorPlugin.workspace_id == workspace_id,
                    EditorPlugin.status == "enabled",
                    EditorPlugin.is_deleted == False,  # noqa: E712
                )
            )
            .order_by(EditorPlugin.display_name.asc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_name(
        self,
        workspace_id: UUID,
        name: str,
    ) -> EditorPlugin | None:
        """Look up a plugin by its workspace + name business key.

        Finds a non-deleted plugin matching workspace and name.

        Args:
            workspace_id: The workspace UUID.
            name: Plugin identifier (e.g. 'my-chart-plugin').

        Returns:
            The matching plugin or None.
        """
        query = select(EditorPlugin).where(
            and_(
                EditorPlugin.workspace_id == workspace_id,
                EditorPlugin.name == name,
                EditorPlugin.is_deleted == False,  # noqa: E712
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create(self, entity: EditorPlugin) -> EditorPlugin:  # type: ignore[override]
        """Create a new editor plugin.

        Args:
            entity: The EditorPlugin instance to persist.

        Returns:
            The persisted EditorPlugin with generated ID.
        """
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def update(self, entity: EditorPlugin) -> EditorPlugin:
        """Update an existing editor plugin.

        Caller mutates the entity, then calls update() to flush changes.

        Args:
            entity: The EditorPlugin instance with updated fields.

        Returns:
            The updated EditorPlugin.
        """
        merged = await self.session.merge(entity)
        await self.session.flush()
        await self.session.refresh(merged)
        return merged

    async def hard_delete(self, plugin_id: UUID) -> None:
        """Hard-delete an editor plugin by ID.

        Args:
            plugin_id: The UUID of the plugin to delete.
        """
        plugin = await self.get_by_id(plugin_id)
        if plugin is not None:
            await self.session.delete(plugin)
            await self.session.flush()


__all__ = ["EditorPluginRepository"]
