"""CreateRoleSkillService for creating user role skills.

Implements CQRS-lite command pattern.

Source: 011-role-based-skills, T009, FR-002, FR-018, FR-020
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pilot_space.application.services.role_skill.types import (
    MAX_ROLES_PER_USER_WORKSPACE,
    VALID_ROLE_TYPES,
)
from pilot_space.domain.exceptions import ValidationError
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.models.user_role_skill import (
        UserRoleSkill,
    )
    from pilot_space.infrastructure.database.repositories.role_skill_repository import (
        RoleSkillRepository,
    )

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class CreateRoleSkillPayload:
    """Payload for creating a role skill."""

    user_id: UUID
    workspace_id: UUID
    role_type: str
    role_name: str
    skill_content: str
    experience_description: str | None = None
    tags: list[str] | None = None
    usage: str | None = None
    is_primary: bool = False


class CreateRoleSkillService:
    """Service for creating a new role skill.

    Validates max roles, duplicate role_type, and handles primary demotion.
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        from pilot_space.infrastructure.database.repositories.role_skill_repository import (
            RoleSkillRepository,
        )

        self._session = session
        self._repo = RoleSkillRepository(session)

    async def execute(self, payload: CreateRoleSkillPayload) -> UserRoleSkill:
        """Create a new role skill.

        Args:
            payload: Creation parameters.

        Returns:
            Created UserRoleSkill entity.

        Raises:
            ValidationError: If validation fails (max roles, duplicate type, invalid type).
        """
        from pilot_space.infrastructure.database.models.user_role_skill import (
            UserRoleSkill,
        )
        from pilot_space.infrastructure.database.repositories.role_skill_repository import (
            RoleTemplateRepository,
        )

        template_repo = RoleTemplateRepository(self._session)

        # Validate role_type
        if payload.role_type not in VALID_ROLE_TYPES:
            msg = f"Invalid role type: {payload.role_type}"
            raise ValidationError(msg)

        # Check max roles constraint
        count = await self._repo.count_by_user_workspace(payload.user_id, payload.workspace_id)
        if count >= MAX_ROLES_PER_USER_WORKSPACE:
            msg = f"Maximum {MAX_ROLES_PER_USER_WORKSPACE} roles per workspace"
            raise ValidationError(msg)

        # Get template version if predefined type
        template_version: int | None = None
        if payload.role_type != "custom":
            template = await template_repo.get_by_role_type(payload.role_type)
            if template:
                template_version = template.version

        # Handle primary demotion
        if payload.is_primary:
            await self._demote_existing_primary(self._repo, payload.user_id, payload.workspace_id)

        skill = UserRoleSkill(
            user_id=payload.user_id,
            workspace_id=payload.workspace_id,
            role_type=payload.role_type,
            role_name=payload.role_name,
            skill_content=payload.skill_content,
            experience_description=payload.experience_description,
            tags=payload.tags if payload.tags is not None else [],
            usage=payload.usage,
            is_primary=payload.is_primary,
            template_version=template_version,
        )

        created = await self._repo.create(skill)

        logger.info(
            "Role skill created",
            extra={
                "user_id": str(payload.user_id),
                "workspace_id": str(payload.workspace_id),
                "role_type": payload.role_type,
                "is_primary": payload.is_primary,
            },
        )

        return created

    async def _demote_existing_primary(
        self,
        repo: RoleSkillRepository,
        user_id: UUID,
        workspace_id: UUID,
    ) -> None:
        """Demote existing primary role skill to secondary."""
        existing_primary = await repo.get_primary_by_user_workspace(user_id, workspace_id)
        if existing_primary is not None:
            existing_primary.is_primary = False
            await repo.update(existing_primary)


__all__ = ["CreateRoleSkillPayload", "CreateRoleSkillService"]
