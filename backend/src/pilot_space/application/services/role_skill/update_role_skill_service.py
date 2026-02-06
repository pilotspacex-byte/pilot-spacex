"""UpdateRoleSkillService for updating user role skills.

Implements CQRS-lite command pattern.

Source: 011-role-based-skills, T009, FR-009, FR-010
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.models.user_role_skill import (
        UserRoleSkill,
    )

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class UpdateRoleSkillPayload:
    """Payload for updating a role skill."""

    user_id: UUID
    skill_id: UUID
    workspace_id: UUID
    role_name: str | None = None
    skill_content: str | None = None
    is_primary: bool | None = None


class UpdateRoleSkillService:
    """Service for updating an existing role skill.

    Validates ownership and handles primary demotion.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def execute(self, payload: UpdateRoleSkillPayload) -> UserRoleSkill:
        """Update a role skill.

        Args:
            payload: Update parameters.

        Returns:
            Updated UserRoleSkill entity.

        Raises:
            ValueError: If skill not found or user doesn't own it.
        """
        from pilot_space.infrastructure.database.repositories.role_skill_repository import (
            RoleSkillRepository,
        )

        repo = RoleSkillRepository(self._session)

        skill = await repo.get_by_id(payload.skill_id)
        if skill is None or skill.is_deleted:
            msg = "Role skill not found"
            raise ValueError(msg)

        # Ownership check (defense-in-depth alongside RLS)
        if skill.user_id != payload.user_id:
            msg = "Not authorized to update this skill"
            raise ValueError(msg)

        if skill.workspace_id != payload.workspace_id:
            msg = "Skill does not belong to this workspace"
            raise ValueError(msg)

        # Handle primary demotion before update
        if payload.is_primary is True and not skill.is_primary:
            existing_primary = await repo.get_primary_by_user_workspace(
                payload.user_id, payload.workspace_id
            )
            if existing_primary is not None and existing_primary.id != skill.id:
                existing_primary.is_primary = False
                await repo.update(existing_primary)

        # Apply partial updates
        if payload.role_name is not None:
            skill.role_name = payload.role_name
        if payload.skill_content is not None:
            skill.skill_content = payload.skill_content
        if payload.is_primary is not None:
            skill.is_primary = payload.is_primary

        updated = await repo.update(skill)

        logger.info(
            "Role skill updated",
            extra={
                "skill_id": str(payload.skill_id),
                "user_id": str(payload.user_id),
            },
        )

        return updated


__all__ = ["UpdateRoleSkillPayload", "UpdateRoleSkillService"]
