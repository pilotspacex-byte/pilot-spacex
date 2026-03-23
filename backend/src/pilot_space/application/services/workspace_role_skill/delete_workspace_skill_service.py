"""DeleteWorkspaceSkillService — soft-delete a workspace role skill.

Source: Phase 16, WRSKL-01
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pilot_space.application.services.workspace_role_skill.types import (
    DeleteWorkspaceSkillPayload,
)
from pilot_space.domain.exceptions import ForbiddenError, NotFoundError
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


class DeleteWorkspaceSkillService:
    """Soft-delete a workspace role skill.

    Validates skill existence and workspace ownership before soft-deleting.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def execute(self, payload: DeleteWorkspaceSkillPayload) -> None:
        """Soft-delete a workspace role skill.

        Args:
            payload: Contains skill_id and workspace_id for ownership validation.

        Raises:
            NotFoundError: If skill not found or already deleted.
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
            msg = f"Workspace role skill {payload.skill_id} is already deleted"
            raise NotFoundError(msg)

        if skill.workspace_id != payload.workspace_id:
            msg = f"Workspace role skill {payload.skill_id} does not belong to workspace {payload.workspace_id}"
            raise ForbiddenError(msg)

        await repo.soft_delete(payload.skill_id)

        logger.info(
            "Workspace role skill deleted",
            extra={
                "skill_id": str(payload.skill_id),
                "workspace_id": str(payload.workspace_id),
            },
        )


__all__ = ["DeleteWorkspaceSkillService"]
