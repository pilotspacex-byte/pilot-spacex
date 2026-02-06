"""Repositories for role-based skills.

RoleSkillRepository: CRUD for UserRoleSkill (per user-workspace).
RoleTemplateRepository: Read-only access to predefined role templates.

Source: 011-role-based-skills, FR-002, FR-004, FR-005, FR-009
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import and_, asc, func, select

from pilot_space.infrastructure.database.models.user_role_skill import (
    RoleTemplate,
    UserRoleSkill,
)
from pilot_space.infrastructure.database.repositories.base import BaseRepository

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class RoleSkillRepository(BaseRepository[UserRoleSkill]):
    """Repository for UserRoleSkill entities.

    Provides workspace-scoped queries for user role skills.
    Primary query pattern: get all skills for a user in a workspace.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, UserRoleSkill)

    async def get_by_user_workspace(
        self,
        user_id: UUID,
        workspace_id: UUID,
    ) -> Sequence[UserRoleSkill]:
        """Get all role skills for a user in a workspace.

        Returns primary role first, then ordered by creation date.

        Args:
            user_id: The user UUID.
            workspace_id: The workspace UUID.

        Returns:
            List of role skills, primary first.
        """
        query = (
            select(UserRoleSkill)
            .where(
                and_(
                    UserRoleSkill.user_id == user_id,
                    UserRoleSkill.workspace_id == workspace_id,
                    UserRoleSkill.is_deleted == False,  # noqa: E712
                )
            )
            .order_by(
                UserRoleSkill.is_primary.desc(),
                UserRoleSkill.created_at.asc(),
            )
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_primary_by_user_workspace(
        self,
        user_id: UUID,
        workspace_id: UUID,
    ) -> UserRoleSkill | None:
        """Get the primary role skill for a user in a workspace.

        Args:
            user_id: The user UUID.
            workspace_id: The workspace UUID.

        Returns:
            Primary role skill if exists, None otherwise.
        """
        query = select(UserRoleSkill).where(
            and_(
                UserRoleSkill.user_id == user_id,
                UserRoleSkill.workspace_id == workspace_id,
                UserRoleSkill.is_primary == True,  # noqa: E712
                UserRoleSkill.is_deleted == False,  # noqa: E712
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def count_by_user_workspace(
        self,
        user_id: UUID,
        workspace_id: UUID,
    ) -> int:
        """Count role skills for a user in a workspace.

        Used to enforce the max 3 roles per user-workspace constraint.

        Args:
            user_id: The user UUID.
            workspace_id: The workspace UUID.

        Returns:
            Number of active (non-deleted) role skills.
        """
        query = (
            select(func.count())
            .select_from(UserRoleSkill)
            .where(
                and_(
                    UserRoleSkill.user_id == user_id,
                    UserRoleSkill.workspace_id == workspace_id,
                    UserRoleSkill.is_deleted == False,  # noqa: E712
                )
            )
        )
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_by_user_workspace_role_type(
        self,
        user_id: UUID,
        workspace_id: UUID,
        role_type: str,
    ) -> UserRoleSkill | None:
        """Get a specific role skill by user, workspace, and role type.

        Args:
            user_id: The user UUID.
            workspace_id: The workspace UUID.
            role_type: The role type string.

        Returns:
            The role skill if found, None otherwise.
        """
        query = select(UserRoleSkill).where(
            and_(
                UserRoleSkill.user_id == user_id,
                UserRoleSkill.workspace_id == workspace_id,
                UserRoleSkill.role_type == role_type,
                UserRoleSkill.is_deleted == False,  # noqa: E712
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()


class RoleTemplateRepository(BaseRepository[RoleTemplate]):
    """Repository for RoleTemplate entities.

    Read-only access to predefined SDLC role templates.
    Templates are seeded via migration and not modified by users.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, RoleTemplate)

    async def get_all_ordered(self) -> Sequence[RoleTemplate]:
        """Get all role templates ordered by sort_order.

        Returns:
            All templates sorted by display order.
        """
        query = (
            select(RoleTemplate)
            .where(RoleTemplate.is_deleted == False)  # noqa: E712
            .order_by(asc(RoleTemplate.sort_order))
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_role_type(self, role_type: str) -> RoleTemplate | None:
        """Get a template by its role type key.

        Args:
            role_type: The role type string (e.g., 'developer').

        Returns:
            The template if found, None otherwise.
        """
        query = select(RoleTemplate).where(
            and_(
                RoleTemplate.role_type == role_type,
                RoleTemplate.is_deleted == False,  # noqa: E712
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()


__all__ = ["RoleSkillRepository", "RoleTemplateRepository"]
