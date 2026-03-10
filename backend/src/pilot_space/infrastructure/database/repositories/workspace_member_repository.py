"""Repository for WorkspaceMember RBAC operations — AUTH-05.

Provides targeted queries for custom role assignment and clearing.
General workspace_member access (list, add, remove) is handled by
WorkspaceRepository to preserve existing code paths.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import and_, select, update

from pilot_space.infrastructure.database.models.workspace_member import WorkspaceMember
from pilot_space.infrastructure.database.repositories.base import BaseRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class WorkspaceMemberRepository(BaseRepository[WorkspaceMember]):
    """Targeted repository for WorkspaceMember RBAC operations.

    Focused on custom role assignment / clearing.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize WorkspaceMemberRepository."""
        super().__init__(session, WorkspaceMember)

    async def get_by_user_workspace(
        self,
        user_id: UUID,
        workspace_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> WorkspaceMember | None:
        """Get a membership record for a specific user in a specific workspace.

        Args:
            user_id: The user UUID.
            workspace_id: The workspace UUID.
            include_deleted: If True, include soft-deleted records.

        Returns:
            WorkspaceMember or None.
        """
        stmt = select(WorkspaceMember).where(
            and_(
                WorkspaceMember.user_id == user_id,
                WorkspaceMember.workspace_id == workspace_id,
            )
        )
        if not include_deleted:
            stmt = stmt.where(WorkspaceMember.is_deleted == False)  # noqa: E712
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, entity: WorkspaceMember) -> WorkspaceMember:
        """Flush and refresh the member entity.

        Args:
            entity: The WorkspaceMember to persist.

        Returns:
            The refreshed WorkspaceMember.
        """
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def clear_custom_role_assignments(
        self,
        role_id: UUID,
        session: AsyncSession,
    ) -> int:
        """Set custom_role_id=NULL for all members assigned this custom role.

        Called before soft-deleting a custom role to prevent orphaned FK refs.

        Args:
            role_id: The custom role UUID to clear.
            session: Async DB session.

        Returns:
            Number of rows updated.
        """
        stmt = (
            update(WorkspaceMember)
            .where(WorkspaceMember.custom_role_id == role_id)
            .values(custom_role_id=None)
        )
        result = await session.execute(stmt)
        await session.flush()
        return result.rowcount  # type: ignore[attr-defined]


__all__ = ["WorkspaceMemberRepository"]
