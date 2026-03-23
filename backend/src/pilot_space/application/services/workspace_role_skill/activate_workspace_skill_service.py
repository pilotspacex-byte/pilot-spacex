"""ActivateWorkspaceSkillService — set is_active=True on a workspace role skill.

Source: Phase 16, WRSKL-02
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pilot_space.application.services.workspace_role_skill.types import (
    ActivateWorkspaceSkillPayload,
)
from pilot_space.domain.exceptions import ForbiddenError, NotFoundError
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.models.workspace_role_skill import (
        WorkspaceRoleSkill,
    )

logger = get_logger(__name__)


class ActivateWorkspaceSkillService:
    """Activate a workspace role skill (WRSKL-02 approval gate).

    Fetches the skill, validates workspace ownership, then sets is_active=True.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def execute(self, payload: ActivateWorkspaceSkillPayload) -> WorkspaceRoleSkill:
        """Activate a workspace role skill.

        Args:
            payload: Contains skill_id and workspace_id for ownership validation.

        Returns:
            Updated WorkspaceRoleSkill with is_active=True.

        Raises:
            NotFoundError: If skill not found, already deleted, or activation fails.
            ForbiddenError: If workspace mismatch.
        """
        from pilot_space.infrastructure.database.repositories.workspace_role_skill_repository import (
            WorkspaceRoleSkillRepository,
        )

        repo = WorkspaceRoleSkillRepository(self._session)
        skill = await repo.get_by_id(payload.skill_id)

        if skill is None:
            msg = f"Workspace role skill {payload.skill_id} not found"
            raise NotFoundError(msg)

        if skill.is_deleted:
            msg = f"Workspace role skill {payload.skill_id} has been deleted"
            raise NotFoundError(msg)

        if skill.workspace_id != payload.workspace_id:
            msg = f"Workspace role skill {payload.skill_id} does not belong to workspace {payload.workspace_id}"
            raise ForbiddenError(msg)

        activated = await repo.activate(payload.skill_id)
        if activated is None:
            msg = f"Failed to activate workspace role skill {payload.skill_id}"
            raise NotFoundError(msg)

        logger.info(
            "Workspace role skill activated",
            extra={
                "skill_id": str(payload.skill_id),
                "workspace_id": str(payload.workspace_id),
            },
        )

        return activated


__all__ = ["ActivateWorkspaceSkillService"]
