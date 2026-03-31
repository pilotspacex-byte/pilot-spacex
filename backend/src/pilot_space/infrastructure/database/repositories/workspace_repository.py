"""Workspace repository for workspace data access.

Provides specialized methods for workspace-related queries.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import joinedload, lazyload

from pilot_space.infrastructure.database.models.workspace import Workspace
from pilot_space.infrastructure.database.models.workspace_member import (
    WorkspaceMember,
    WorkspaceRole,
)
from pilot_space.infrastructure.database.repositories.base import BaseRepository

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class WorkspaceRepository(BaseRepository[Workspace]):
    """Repository for Workspace entities.

    Extends BaseRepository with workspace-specific queries.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize WorkspaceRepository.

        Args:
            session: The async database session.
        """
        super().__init__(session, Workspace)

    async def get_by_slug(
        self,
        slug: str,
        *,
        include_deleted: bool = False,
    ) -> Workspace | None:
        """Get workspace by URL slug.

        Args:
            slug: The workspace's URL-friendly identifier.
            include_deleted: Whether to include soft-deleted workspaces.

        Returns:
            The workspace if found, None otherwise.
        """
        query = select(Workspace).where(Workspace.slug == slug)
        if not include_deleted:
            query = query.where(Workspace.is_deleted == False)  # noqa: E712
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_slug_scalar(
        self,
        slug: str,
        *,
        include_deleted: bool = False,
    ) -> Workspace | None:
        """Get workspace by slug loading only scalar columns.

        Overrides model-level eager loading (7 selectin relationships)
        to prevent unnecessary queries when only workspace ID/slug is needed.

        Args:
            slug: The workspace's URL-friendly identifier.
            include_deleted: Whether to include soft-deleted workspaces.

        Returns:
            Workspace with scalar columns only, or None.
        """
        query = select(Workspace).options(lazyload("*")).where(Workspace.slug == slug)
        if not include_deleted:
            query = query.where(Workspace.is_deleted == False)  # noqa: E712
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_slug_with_members(
        self,
        slug: str,
        *,
        include_deleted: bool = False,
    ) -> Workspace | None:
        """Get workspace by slug with members eagerly loaded.

        Args:
            slug: The workspace slug.
            include_deleted: Whether to include soft-deleted workspaces.

        Returns:
            The workspace with members loaded, or None.
        """
        query = (
            select(Workspace)
            .options(
                joinedload(Workspace.members.and_(WorkspaceMember.is_deleted == False)).joinedload(  # noqa: E712
                    WorkspaceMember.user
                )
            )
            .where(Workspace.slug == slug)
        )
        if not include_deleted:
            query = query.where(Workspace.is_deleted == False)  # noqa: E712
        result = await self.session.execute(query)
        return result.unique().scalar_one_or_none()

    async def slug_exists(
        self,
        slug: str,
        *,
        exclude_id: UUID | None = None,
    ) -> bool:
        """Check if workspace slug is already in use.

        Args:
            slug: The slug to check.
            exclude_id: Workspace ID to exclude from check (for updates).

        Returns:
            True if slug exists, False otherwise.
        """
        query = select(Workspace).where(
            Workspace.slug == slug,
            Workspace.is_deleted == False,  # noqa: E712
        )
        if exclude_id:
            query = query.where(Workspace.id != exclude_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

    async def get_by_owner(
        self,
        owner_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Sequence[Workspace]:
        """Get all workspaces owned by a user.

        Args:
            owner_id: The owner's user ID.
            include_deleted: Whether to include soft-deleted workspaces.

        Returns:
            List of workspaces owned by the user.
        """
        return await self.find_by(owner_id=owner_id, include_deleted=include_deleted)

    async def get_user_workspaces(
        self,
        user_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Sequence[Workspace]:
        """Get all workspaces a user is a member of.

        Args:
            user_id: The user's ID.
            include_deleted: Whether to include soft-deleted workspaces.

        Returns:
            List of workspaces the user belongs to.
        """
        query = (
            select(Workspace)
            .join(WorkspaceMember, Workspace.id == WorkspaceMember.workspace_id)
            .where(WorkspaceMember.user_id == user_id)
            .where(WorkspaceMember.is_deleted == False)  # noqa: E712
        )
        if not include_deleted:
            query = query.where(Workspace.is_deleted == False)  # noqa: E712
        query = query.order_by(Workspace.created_at.desc())
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_with_members(
        self,
        workspace_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Workspace | None:
        """Get workspace with members eagerly loaded.

        Args:
            workspace_id: The workspace ID.
            include_deleted: Whether to include soft-deleted workspace.

        Returns:
            Workspace with members loaded, or None if not found.
        """
        query = (
            select(Workspace)
            .options(
                joinedload(Workspace.members.and_(WorkspaceMember.is_deleted == False)).joinedload(  # noqa: E712
                    WorkspaceMember.user
                )
            )
            .where(Workspace.id == workspace_id)
        )
        if not include_deleted:
            query = query.where(Workspace.is_deleted == False)  # noqa: E712
        result = await self.session.execute(query)
        return result.unique().scalar_one_or_none()

    async def get_member_count(
        self,
        workspace_id: UUID,
    ) -> int:
        """Get count of active members in workspace.

        Args:
            workspace_id: The workspace ID.

        Returns:
            Count of active members.
        """
        query = (
            select(func.count())
            .select_from(WorkspaceMember)
            .where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.is_deleted == False,  # noqa: E712
            )
        )
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def is_member(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> bool:
        """Check if user is a member of workspace.

        Args:
            workspace_id: The workspace ID.
            user_id: The user ID.

        Returns:
            True if user is a member, False otherwise.
        """
        query = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
            WorkspaceMember.is_deleted == False,  # noqa: E712
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

    async def get_member_role(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> WorkspaceRole | None:
        """Get user's role in workspace.

        Args:
            workspace_id: The workspace ID.
            user_id: The user ID.

        Returns:
            The user's role if member, None otherwise.
        """
        query = select(WorkspaceMember.role).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
            WorkspaceMember.is_deleted == False,  # noqa: E712
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def add_member(
        self,
        workspace_id: UUID,
        user_id: UUID,
        role: WorkspaceRole = WorkspaceRole.MEMBER,
    ) -> WorkspaceMember:
        """Add a member to workspace.

        Args:
            workspace_id: The workspace ID.
            user_id: The user ID.
            role: The member's role.

        Returns:
            The created WorkspaceMember.
        """
        member = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=user_id,
            role=role,
        )
        self.session.add(member)
        await self.session.flush()
        member_result = await self.session.execute(
            select(WorkspaceMember)
            .options(joinedload(WorkspaceMember.user))
            .where(WorkspaceMember.id == member.id)
        )
        return member_result.scalar_one()

    async def upsert_member(
        self,
        workspace_id: UUID,
        user_id: UUID,
        role: WorkspaceRole = WorkspaceRole.MEMBER,
    ) -> WorkspaceMember:
        """Add or reactivate a workspace member using upsert.

        Handles re-invite of a previously soft-deleted member without raising
        a UniqueConstraint error on (user_id, workspace_id).

        On conflict with the unique constraint ``uq_workspace_members_user_workspace``:
        - Restores the row: sets is_deleted=False, deleted_at=None, is_active=True
        - Updates the role to the newly requested role

        Args:
            workspace_id: The workspace ID.
            user_id: The user ID.
            role: The member's role.

        Returns:
            The created or reactivated WorkspaceMember.
        """
        now = datetime.now(tz=UTC)
        stmt = (
            pg_insert(WorkspaceMember)
            .values(
                workspace_id=workspace_id,
                user_id=user_id,
                role=role,
                is_deleted=False,
                deleted_at=None,
                is_active=True,
                updated_at=now,
            )
            .on_conflict_do_update(
                index_elements=[
                    WorkspaceMember.__table__.c.user_id,
                    WorkspaceMember.__table__.c.workspace_id,
                ],
                set_={
                    "role": role,
                    "is_deleted": False,
                    "deleted_at": None,
                    "is_active": True,
                    "updated_at": now,
                },
            )
            .returning(WorkspaceMember.id)
        )
        result = await self.session.execute(stmt)
        member_id = result.scalar_one()

        # Fetch the full ORM object after upsert
        member_result = await self.session.execute(
            select(WorkspaceMember)
            .options(joinedload(WorkspaceMember.user))
            .where(WorkspaceMember.id == member_id)
        )
        return member_result.scalar_one()

    async def update_member_role(
        self,
        workspace_id: UUID,
        user_id: UUID,
        role: WorkspaceRole,
    ) -> WorkspaceMember | None:
        """Update a member's role in workspace.

        Args:
            workspace_id: The workspace ID.
            user_id: The user ID.
            role: The new role.

        Returns:
            Updated WorkspaceMember or None if not found.
        """
        query = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
            WorkspaceMember.is_deleted == False,  # noqa: E712
        )
        result = await self.session.execute(query)
        member = result.scalar_one_or_none()
        if member:
            member.role = role
            await self.session.flush()
            await self.session.refresh(member)
        return member

    async def remove_member(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> bool:
        """Remove a member from workspace (soft delete).

        Args:
            workspace_id: The workspace ID.
            user_id: The user ID.

        Returns:
            True if member was removed, False if not found.
        """
        query = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
            WorkspaceMember.is_deleted == False,  # noqa: E712
        )
        result = await self.session.execute(query)
        member = result.scalar_one_or_none()
        if member:
            member.is_deleted = True
            member.deleted_at = datetime.now(tz=UTC)
            await self.session.flush()
            return True
        return False
