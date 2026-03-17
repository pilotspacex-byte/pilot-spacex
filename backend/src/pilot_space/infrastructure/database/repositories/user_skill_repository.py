"""Repository for UserSkill entities.

Provides user-workspace-scoped CRUD operations for user skills.
Primary query patterns:
- get_by_user_workspace: user's active skills for materializer/UI
- get_by_user_workspace_template: check if user already has skill from template

Source: Phase 20, P20-02
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import and_, select
from sqlalchemy.orm import selectinload

from pilot_space.infrastructure.database.models.user_skill import UserSkill
from pilot_space.infrastructure.database.repositories.base import BaseRepository

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class UserSkillRepository(BaseRepository[UserSkill]):
    """Repository for UserSkill entities.

    All write operations use flush() (no commit) -- callers own transaction
    boundaries via the session context.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, UserSkill)

    async def get_by_id_with_template(
        self,
        skill_id: UUID,
    ) -> UserSkill | None:
        """Get a user skill by ID with template relationship eagerly loaded.

        Needed because UserSkill.template uses lazy='raise', so the
        relationship must be explicitly loaded before accessing template.name
        in response serialization.

        Args:
            skill_id: The skill UUID.

        Returns:
            The UserSkill with template loaded, or None.
        """
        query = (
            select(UserSkill)
            .options(selectinload(UserSkill.template))
            .where(
                and_(
                    UserSkill.id == skill_id,
                    UserSkill.is_deleted == False,  # noqa: E712
                )
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create(  # type: ignore[override]
        self,
        *,
        user_id: UUID,
        workspace_id: UUID,
        skill_content: str,
        template_id: UUID | None = None,
        experience_description: str | None = None,
        skill_name: str | None = None,
        is_active: bool = True,
    ) -> UserSkill:
        """Create a new user skill.

        Args:
            user_id: Skill owner UUID.
            workspace_id: Owning workspace UUID.
            skill_content: SKILL.md-format markdown content.
            template_id: Source template UUID (optional).
            experience_description: Natural language input for AI generation.
            skill_name: User-visible skill name (AI-suggested or user-edited).
            is_active: Whether skill is materialized into agent context.

        Returns:
            Newly created UserSkill.
        """
        skill = UserSkill(
            user_id=user_id,
            workspace_id=workspace_id,
            template_id=template_id,
            skill_content=skill_content,
            experience_description=experience_description,
            skill_name=skill_name,
            is_active=is_active,
        )
        self.session.add(skill)
        await self.session.flush()
        await self.session.refresh(skill)
        # Eagerly load template relationship so _to_schema() can access
        # template.name without triggering lazy="raise".
        if skill.template_id is not None:
            query = (
                select(UserSkill)
                .options(selectinload(UserSkill.template))
                .where(UserSkill.id == skill.id)
            )
            result = await self.session.execute(query)
            loaded = result.scalar_one_or_none()
            if loaded is not None:
                return loaded
        return skill

    async def get_by_user_workspace(
        self,
        user_id: UUID,
        workspace_id: UUID,
    ) -> Sequence[UserSkill]:
        """Get all non-deleted skills for a user in a workspace.

        Returns rows where is_deleted=False (includes both active and inactive).
        Inactive skills are shown with reduced opacity in the UI so the user
        can toggle them back to active.

        For the materializer hot-path (only active skills), use
        :meth:`get_active_by_user_workspace` instead.

        Args:
            user_id: The user UUID.
            workspace_id: The workspace UUID.

        Returns:
            All non-deleted UserSkill rows for the user in the workspace.
        """
        query = (
            select(UserSkill)
            .options(selectinload(UserSkill.template))
            .where(
                and_(
                    UserSkill.user_id == user_id,
                    UserSkill.workspace_id == workspace_id,
                    UserSkill.is_deleted == False,  # noqa: E712
                )
            )
            .order_by(UserSkill.created_at.asc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_active_by_user_workspace(
        self,
        user_id: UUID,
        workspace_id: UUID,
    ) -> Sequence[UserSkill]:
        """Get active, non-deleted skills for a user in a workspace.

        Materializer hot-path: only returns skills where is_active=True
        so that deactivated skills are NOT written to the agent sandbox.

        Args:
            user_id: The user UUID.
            workspace_id: The workspace UUID.

        Returns:
            Active UserSkill rows for the user in the workspace.
        """
        query = (
            select(UserSkill)
            .options(selectinload(UserSkill.template))
            .where(
                and_(
                    UserSkill.user_id == user_id,
                    UserSkill.workspace_id == workspace_id,
                    UserSkill.is_active == True,  # noqa: E712
                    UserSkill.is_deleted == False,  # noqa: E712
                )
            )
            .order_by(UserSkill.created_at.asc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_user_workspace_template(
        self,
        user_id: UUID,
        workspace_id: UUID,
        template_id: UUID,
    ) -> UserSkill | None:
        """Get a specific skill by user, workspace, and template.

        Used to check if a user already has a skill from a given template.

        Args:
            user_id: The user UUID.
            workspace_id: The workspace UUID.
            template_id: The template UUID.

        Returns:
            The user skill if found, None otherwise.
        """
        query = select(UserSkill).where(
            and_(
                UserSkill.user_id == user_id,
                UserSkill.workspace_id == workspace_id,
                UserSkill.template_id == template_id,
                UserSkill.is_deleted == False,  # noqa: E712
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def update(  # type: ignore[override]
        self,
        skill: UserSkill,
    ) -> UserSkill:
        """Update a user skill.

        Args:
            skill: The skill to update (already modified in-memory).

        Returns:
            Updated UserSkill.
        """
        await self.session.flush()
        await self.session.refresh(skill)
        return skill

    async def soft_delete(
        self,
        skill_id: UUID,
    ) -> UserSkill | None:
        """Soft-delete a user skill.

        Sets is_deleted=True, deleted_at=now(), and is_active=False.

        Args:
            skill_id: The skill UUID to soft-delete.

        Returns:
            Updated UserSkill with is_deleted=True, or None.
        """
        skill = await self.get_by_id(skill_id)
        if skill is None:
            return None
        skill.is_active = False
        skill.is_deleted = True
        skill.deleted_at = datetime.now(tz=UTC)
        await self.session.flush()
        await self.session.refresh(skill)
        return skill


__all__ = ["UserSkillRepository"]
