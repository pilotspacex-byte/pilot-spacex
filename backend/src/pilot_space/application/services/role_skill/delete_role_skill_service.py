"""DeleteRoleSkillService for removing user role skills.

Implements CQRS-lite command pattern.

Source: 011-role-based-skills, T009, FR-009
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pilot_space.domain.exceptions import ForbiddenError, NotFoundError
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


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
            NotFoundError: If skill not found.
            ForbiddenError: If user doesn't own the skill or workspace mismatch.
        """
        from pilot_space.infrastructure.database.repositories.role_skill_repository import (
            RoleSkillRepository,
        )

        repo = RoleSkillRepository(self._session)

        skill = await repo.get_by_id(payload.skill_id)
        if skill is None or skill.is_deleted:
            msg = "Role skill not found"
            raise NotFoundError(msg)

        # Ownership check (defense-in-depth alongside RLS)
        if skill.user_id != payload.user_id:
            msg = "Not authorized to delete this skill"
            raise ForbiddenError(msg)

        if skill.workspace_id != payload.workspace_id:
            msg = "Skill does not belong to this workspace"
            raise ForbiddenError(msg)

        await repo.delete(skill)

        logger.info(
            "Role skill deleted",
            extra={
                "skill_id": str(payload.skill_id),
                "user_id": str(payload.user_id),
            },
        )


__all__ = ["DeleteRoleSkillPayload", "DeleteRoleSkillService"]
