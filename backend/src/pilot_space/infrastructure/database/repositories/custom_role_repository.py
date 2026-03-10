"""Repository for CustomRole entities — AUTH-05.

Provides workspace-scoped CRUD for custom_roles table.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import and_, select, update

from pilot_space.infrastructure.database.models.custom_role import CustomRole
from pilot_space.infrastructure.database.repositories.base import BaseRepository

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession


class CustomRoleRepository(BaseRepository[CustomRole]):
    """Repository for CustomRole entities.

    All methods are workspace-scoped: callers must provide a workspace_id
    to ensure multi-tenant isolation. The base BaseRepository soft-delete
    pattern is used (is_deleted=True, not hard-delete).
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize CustomRoleRepository."""
        super().__init__(session, CustomRole)

    async def get(
        self,
        role_id: UUID,
        workspace_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> CustomRole | None:
        """Get a custom role by ID, scoped to workspace.

        Args:
            role_id: The role UUID.
            workspace_id: Owning workspace UUID.
            include_deleted: If True, include soft-deleted roles.

        Returns:
            CustomRole or None if not found / wrong workspace.
        """
        stmt = select(CustomRole).where(
            and_(
                CustomRole.id == role_id,
                CustomRole.workspace_id == workspace_id,
            )
        )
        if not include_deleted:
            stmt = stmt.where(CustomRole.is_deleted == False)  # noqa: E712
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(
        self,
        workspace_id: UUID,
        name: str,
        *,
        exclude_id: UUID | None = None,
        include_deleted: bool = False,
    ) -> CustomRole | None:
        """Get a custom role by name within a workspace.

        Used for uniqueness validation before create/update.

        Args:
            workspace_id: Owning workspace UUID.
            name: Role name to look up.
            exclude_id: Optional role ID to exclude (for update checks).
            include_deleted: If True, include soft-deleted roles.

        Returns:
            Matching CustomRole or None.
        """
        stmt = select(CustomRole).where(
            and_(
                CustomRole.workspace_id == workspace_id,
                CustomRole.name == name,
            )
        )
        if not include_deleted:
            stmt = stmt.where(CustomRole.is_deleted == False)  # noqa: E712
        if exclude_id is not None:
            stmt = stmt.where(CustomRole.id != exclude_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_workspace(
        self,
        workspace_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Sequence[CustomRole]:
        """List all custom roles for a workspace, ordered by name.

        Args:
            workspace_id: Owning workspace UUID.
            include_deleted: If True, include soft-deleted roles.

        Returns:
            Sequence of CustomRole objects ordered by name.
        """
        stmt = select(CustomRole).where(CustomRole.workspace_id == workspace_id)
        if not include_deleted:
            stmt = stmt.where(CustomRole.is_deleted == False)  # noqa: E712
        stmt = stmt.order_by(CustomRole.name)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def soft_delete(
        self,
        role_id: UUID,
        workspace_id: UUID,
    ) -> bool:
        """Soft-delete a custom role by setting is_deleted=True.

        Args:
            role_id: The role UUID.
            workspace_id: Owning workspace UUID (safety check).

        Returns:
            True if a row was deleted, False if not found.
        """
        from datetime import UTC, datetime

        stmt = (
            update(CustomRole)
            .where(
                and_(
                    CustomRole.id == role_id,
                    CustomRole.workspace_id == workspace_id,
                    CustomRole.is_deleted == False,  # noqa: E712
                )
            )
            .values(is_deleted=True, deleted_at=datetime.now(tz=UTC))
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0  # type: ignore[attr-defined]


__all__ = ["CustomRoleRepository"]
