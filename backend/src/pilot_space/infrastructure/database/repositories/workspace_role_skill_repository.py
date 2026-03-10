"""Repository for WorkspaceRoleSkill entities.

Provides workspace-scoped CRUD operations for workspace-level role skills.
Primary query patterns:
- get_active_by_workspace: hot-path for materializer injection
- get_by_workspace: admin list (all non-deleted rows)

Source: Phase 16, WRSKL-01..04
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import and_, select

from pilot_space.infrastructure.database.models.workspace_role_skill import WorkspaceRoleSkill
from pilot_space.infrastructure.database.repositories.base import BaseRepository

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class WorkspaceRoleSkillRepository(BaseRepository[WorkspaceRoleSkill]):
    """Repository for WorkspaceRoleSkill entities.

    All write operations use flush() (no commit) — callers own transaction
    boundaries via the session context.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, WorkspaceRoleSkill)

    async def create(  # type: ignore[override]
        self,
        *,
        workspace_id: UUID,
        created_by: UUID,
        role_type: str,
        role_name: str,
        skill_content: str,
        experience_description: str | None = None,
    ) -> WorkspaceRoleSkill:
        """Create a new workspace role skill.

        New skills are inactive by default (is_active=False) — requires
        explicit activation by an admin (WRSKL-02 approval gate).

        Args:
            workspace_id: Owning workspace UUID.
            created_by: Admin user UUID who creates the skill.
            role_type: SDLC role identifier (e.g., 'developer').
            role_name: Human-readable display name.
            skill_content: SKILL.md-format markdown content.
            experience_description: Optional natural language input for AI generation.

        Returns:
            Newly created WorkspaceRoleSkill with is_active=False.
        """
        skill = WorkspaceRoleSkill(
            workspace_id=workspace_id,
            created_by=created_by,
            role_type=role_type,
            role_name=role_name,
            skill_content=skill_content,
            experience_description=experience_description,
            is_active=False,
        )
        self.session.add(skill)
        await self.session.flush()
        await self.session.refresh(skill)
        return skill

    async def get_by_id(  # type: ignore[override]
        self,
        skill_id: UUID,
    ) -> WorkspaceRoleSkill | None:
        """Get a workspace role skill by its primary key.

        Does not filter by is_deleted — caller handles deleted state check.

        Args:
            skill_id: The skill UUID.

        Returns:
            The skill if found, None otherwise.
        """
        query = select(WorkspaceRoleSkill).where(WorkspaceRoleSkill.id == skill_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_workspace(
        self,
        workspace_id: UUID,
    ) -> Sequence[WorkspaceRoleSkill]:
        """Get all non-deleted skills for a workspace (admin list view).

        Ordered by created_at descending so newest skills appear first.

        Args:
            workspace_id: The workspace UUID.

        Returns:
            All non-deleted WorkspaceRoleSkill rows for the workspace.
        """
        query = (
            select(WorkspaceRoleSkill)
            .where(
                and_(
                    WorkspaceRoleSkill.workspace_id == workspace_id,
                    WorkspaceRoleSkill.is_deleted == False,  # noqa: E712
                )
            )
            .order_by(WorkspaceRoleSkill.created_at.desc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_active_by_workspace(
        self,
        workspace_id: UUID,
    ) -> Sequence[WorkspaceRoleSkill]:
        """Get active skills for a workspace (materializer hot-path).

        Returns only rows where is_active=True AND is_deleted=False.
        This is the injection point for the WRSKL-03 materializer extension.

        Args:
            workspace_id: The workspace UUID.

        Returns:
            Active WorkspaceRoleSkill rows for the workspace.
        """
        query = (
            select(WorkspaceRoleSkill)
            .where(
                and_(
                    WorkspaceRoleSkill.workspace_id == workspace_id,
                    WorkspaceRoleSkill.is_active == True,  # noqa: E712
                    WorkspaceRoleSkill.is_deleted == False,  # noqa: E712
                )
            )
            .order_by(WorkspaceRoleSkill.role_type.asc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def activate(
        self,
        skill_id: UUID,
    ) -> WorkspaceRoleSkill | None:
        """Activate a workspace role skill.

        Sets is_active=True. Returns the updated skill or None if not found.

        Args:
            skill_id: The skill UUID to activate.

        Returns:
            Updated WorkspaceRoleSkill with is_active=True, or None.
        """
        skill = await self.get_by_id(skill_id)
        if skill is None or skill.is_deleted:
            return None
        skill.is_active = True
        await self.session.flush()
        await self.session.refresh(skill)
        return skill

    async def deactivate(
        self,
        skill_id: UUID,
    ) -> WorkspaceRoleSkill | None:
        """Deactivate a workspace role skill.

        Sets is_active=False. Returns the updated skill or None if not found.

        Args:
            skill_id: The skill UUID to deactivate.

        Returns:
            Updated WorkspaceRoleSkill with is_active=False, or None.
        """
        skill = await self.get_by_id(skill_id)
        if skill is None or skill.is_deleted:
            return None
        skill.is_active = False
        await self.session.flush()
        await self.session.refresh(skill)
        return skill

    async def soft_delete(  # type: ignore[override]
        self,
        skill_id: UUID,
    ) -> WorkspaceRoleSkill | None:
        """Soft-delete a workspace role skill.

        Sets is_deleted=True and deleted_at=now(). Returns the updated skill
        or None if not found. Deactivates the skill before marking deleted so
        it is excluded from all active queries immediately.

        Args:
            skill_id: The skill UUID to soft-delete.

        Returns:
            Updated WorkspaceRoleSkill with is_deleted=True, or None.
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


__all__ = ["WorkspaceRoleSkillRepository"]
