"""Repository for WorkspacePlugin entities.

Provides workspace-scoped CRUD operations for installed plugins.
Primary query patterns:
- get_active_by_workspace: hot-path for materializer injection
- get_installed_by_workspace: admin list (all non-deleted rows)
- get_by_workspace_and_name: lookup by (workspace_id, repo_owner, repo_name, skill_name)

Source: Phase 19, SKRG-01..05
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import and_, select, update

from pilot_space.infrastructure.database.models.workspace_plugin import WorkspacePlugin
from pilot_space.infrastructure.database.repositories.base import BaseRepository

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class WorkspacePluginRepository(BaseRepository[WorkspacePlugin]):
    """Repository for WorkspacePlugin entities.

    All write operations use flush() (no commit) -- callers own transaction
    boundaries via the session context.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, WorkspacePlugin)

    async def get_active_by_workspace(
        self,
        workspace_id: UUID,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> Sequence[WorkspacePlugin]:
        """Get active plugins for a workspace (materializer hot-path).

        Returns only rows where is_active=True AND is_deleted=False.

        Args:
            workspace_id: The workspace UUID.
            limit: Maximum number of rows to return (None = no limit).
            offset: Number of rows to skip for pagination.

        Returns:
            Active WorkspacePlugin rows ordered by display_name.
        """
        query = (
            select(WorkspacePlugin)
            .where(
                and_(
                    WorkspacePlugin.workspace_id == workspace_id,
                    WorkspacePlugin.is_active == True,  # noqa: E712
                    WorkspacePlugin.is_deleted == False,  # noqa: E712
                )
            )
            .order_by(WorkspacePlugin.display_name.asc())
            .offset(offset)
        )
        if limit is not None:
            query = query.limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_installed_by_workspace(
        self,
        workspace_id: UUID,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> Sequence[WorkspacePlugin]:
        """Get all non-deleted plugins for a workspace (admin list view).

        Ordered by created_at descending so newest plugins appear first.

        Args:
            workspace_id: The workspace UUID.
            limit: Maximum number of rows to return (None = no limit).
            offset: Number of rows to skip for pagination.

        Returns:
            All non-deleted WorkspacePlugin rows for the workspace.
        """
        query = (
            select(WorkspacePlugin)
            .where(
                and_(
                    WorkspacePlugin.workspace_id == workspace_id,
                    WorkspacePlugin.is_deleted == False,  # noqa: E712
                )
            )
            .order_by(WorkspacePlugin.created_at.desc())
            .offset(offset)
        )
        if limit is not None:
            query = query.limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_workspace_and_repo(
        self,
        workspace_id: UUID,
        repo_owner: str,
        repo_name: str,
    ) -> Sequence[WorkspacePlugin]:
        """Get all non-deleted plugins from a specific repo in a workspace.

        Args:
            workspace_id: The workspace UUID.
            repo_owner: GitHub owner/org.
            repo_name: GitHub repository name.

        Returns:
            All non-deleted WorkspacePlugin rows from this repo.
        """
        query = (
            select(WorkspacePlugin)
            .where(
                and_(
                    WorkspacePlugin.workspace_id == workspace_id,
                    WorkspacePlugin.repo_owner == repo_owner,
                    WorkspacePlugin.repo_name == repo_name,
                    WorkspacePlugin.is_deleted == False,  # noqa: E712
                )
            )
            .order_by(WorkspacePlugin.display_name.asc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_workspace_and_name(
        self,
        workspace_id: UUID,
        repo_owner: str,
        repo_name: str,
        skill_name: str,
    ) -> WorkspacePlugin | None:
        """Look up a plugin by its composite business key.

        Finds a non-deleted plugin matching workspace + repo + skill name.

        Args:
            workspace_id: The workspace UUID.
            repo_owner: GitHub owner/org.
            repo_name: GitHub repository name.
            skill_name: Skill identifier within the repo.

        Returns:
            The matching plugin or None.
        """
        query = select(WorkspacePlugin).where(
            and_(
                WorkspacePlugin.workspace_id == workspace_id,
                WorkspacePlugin.repo_owner == repo_owner,
                WorkspacePlugin.repo_name == repo_name,
                WorkspacePlugin.skill_name == skill_name,
                WorkspacePlugin.is_deleted == False,  # noqa: E712
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create(self, entity: WorkspacePlugin) -> WorkspacePlugin:  # type: ignore[override]
        """Create a new workspace plugin.

        Args:
            entity: The WorkspacePlugin instance to persist.

        Returns:
            The persisted WorkspacePlugin with generated ID.
        """
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def update(self, entity: WorkspacePlugin) -> WorkspacePlugin:
        """Update an existing workspace plugin.

        Caller mutates the entity, then calls update() to flush changes.

        Args:
            entity: The WorkspacePlugin instance with updated fields.

        Returns:
            The updated WorkspacePlugin.
        """
        merged = await self.session.merge(entity)
        await self.session.flush()
        await self.session.refresh(merged)
        return merged

    async def bulk_set_active(
        self,
        plugin_ids: list[UUID],
        is_active: bool,
    ) -> int:
        """Bulk toggle the is_active flag for a list of plugins.

        Args:
            plugin_ids: List of plugin UUIDs to update.
            is_active: The new active state to set.

        Returns:
            Number of rows updated.
        """
        if not plugin_ids:
            return 0
        stmt = (
            update(WorkspacePlugin)
            .where(WorkspacePlugin.id.in_(plugin_ids))
            .values(is_active=is_active)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount  # type: ignore[return-value]

    async def bulk_soft_delete(
        self,
        plugin_ids: list[UUID],
    ) -> int:
        """Bulk soft-delete a list of plugins.

        Sets is_deleted=True and is_active=False for all matching rows.

        Args:
            plugin_ids: List of plugin UUIDs to soft-delete.

        Returns:
            Number of rows updated.
        """
        if not plugin_ids:
            return 0
        stmt = (
            update(WorkspacePlugin)
            .where(WorkspacePlugin.id.in_(plugin_ids))
            .values(is_deleted=True, is_active=False, deleted_at=datetime.now(tz=UTC))
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount  # type: ignore[return-value]

    async def soft_delete(  # type: ignore[override]
        self,
        plugin: WorkspacePlugin,
    ) -> None:
        """Soft-delete a workspace plugin.

        Sets is_deleted=True, deleted_at=now(), and is_active=False
        atomically to ensure immediate exclusion from materializer.

        Args:
            plugin: The WorkspacePlugin to soft-delete.
        """
        plugin.is_active = False
        plugin.is_deleted = True
        plugin.deleted_at = datetime.now(tz=UTC)
        await self.session.flush()


__all__ = ["WorkspacePluginRepository"]
