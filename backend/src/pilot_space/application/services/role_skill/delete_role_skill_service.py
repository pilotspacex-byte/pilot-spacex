"""DeleteRoleSkillService for removing user role skills.

Implements CQRS-lite command pattern.

Source: 011-role-based-skills, T009, FR-009
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DeleteRoleSkillPayload:
    """Payload for deleting a role skill."""

    user_id: UUID
    skill_id: UUID
    workspace_id: UUID


class DeleteRoleSkillService:
    """Service for soft-deleting a role skill.

    Validates ownership before deletion.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def execute(self, payload: DeleteRoleSkillPayload) -> None:
        """Soft-delete a role skill.

        Args:
            payload: Deletion parameters.

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
            msg = "Not authorized to delete this skill"
            raise ValueError(msg)

        if skill.workspace_id != payload.workspace_id:
            msg = "Skill does not belong to this workspace"
            raise ValueError(msg)

        await repo.delete(skill)

        logger.info(
            "Role skill deleted",
            extra={
                "skill_id": str(payload.skill_id),
                "user_id": str(payload.user_id),
            },
        )


__all__ = ["DeleteRoleSkillPayload", "DeleteRoleSkillService"]
