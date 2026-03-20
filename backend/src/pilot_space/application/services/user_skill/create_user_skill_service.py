"""CreateUserSkillService -- AI-based user skill creation from template.

User picks a template, provides experience description, AI generates
personalized skill content, and a UserSkill row is created.

Source: Phase 20, P20-08
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pilot_space.application.services.role_skill.generate_role_skill_service import (
    GenerateRoleSkillPayload,
    GenerateRoleSkillService,
)
from pilot_space.infrastructure.database.models.skill_template import SkillTemplate
from pilot_space.infrastructure.database.repositories.skill_template_repository import (
    SkillTemplateRepository,
)
from pilot_space.infrastructure.database.repositories.user_skill_repository import (
    UserSkillRepository,
)
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.models.user_skill import UserSkill

logger = get_logger(__name__)


class CreateUserSkillService:
    """Service for creating personalized user skills from templates.

    Flow:
    1. Load and validate template (active, correct workspace).
    2. Check for duplicate (user already has skill from this template).
    3. Generate personalized skill content via AI (with template fallback).
    4. Create UserSkill row.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with a database session.

        Args:
            session: Active async database session.
        """
        self._session = session

    async def create(
        self,
        *,
        user_id: UUID,
        workspace_id: UUID,
        template_id: UUID | None,
        experience_description: str,
        skill_content: str | None = None,
        skill_name: str | None = None,
        tags: list[str] | None = None,
        usage: str | None = None,
    ) -> UserSkill:
        """Create a user skill from template or custom content.

        Args:
            user_id: The user creating the skill.
            workspace_id: The workspace context.
            template_id: Source template UUID (None for custom skills).
            experience_description: User's experience for AI personalization.
            skill_content: Pre-generated skill content (for custom skills).
            skill_name: User-visible skill name (AI-suggested or user-edited).
            tags: Ability tags for discoverability.
            usage: When/how this skill should be activated.

        Returns:
            The created UserSkill.

        Raises:
            ValueError: If template not found, inactive, deleted, wrong workspace,
                or user already has a skill from this template.
        """
        user_skill_repo = UserSkillRepository(self._session)

        if template_id is not None:
            # Template-based: validate, check duplicate
            template_repo = SkillTemplateRepository(self._session)
            template = await template_repo.get_by_id(template_id)
            if template is None:
                msg = f"Template not found: {template_id}"
                raise ValueError(msg)

            if (
                not template.is_active
                or template.is_deleted
                or template.workspace_id != workspace_id
            ):
                msg = f"Template {template_id} is not active in workspace {workspace_id}"
                raise ValueError(msg)

            existing = await user_skill_repo.get_by_user_workspace_template(
                user_id, workspace_id, template_id
            )
            if existing is not None:
                msg = f"User already has a skill from template {template_id}"
                raise ValueError(msg)

            if skill_content and skill_content.strip():
                # Frontend already generated + user may have edited — use as-is
                content = skill_content
            else:
                # No pre-generated content — AI-generate from template
                content = await self._generate_content(
                    template=template,
                    experience_description=experience_description,
                    user_id=user_id,
                    workspace_id=workspace_id,
                )
        else:
            # Custom skill: use provided content directly
            if not skill_content or not skill_content.strip():
                msg = "skill_content is required for custom skills (no template_id)"
                raise ValueError(msg)
            content = skill_content

        user_skill = await user_skill_repo.create(
            user_id=user_id,
            workspace_id=workspace_id,
            template_id=template_id,
            skill_content=content,
            experience_description=experience_description,
            skill_name=skill_name,
            tags=tags,
            usage=usage,
        )

        logger.info(
            "Created user skill template=%s user=%s workspace=%s",
            template_id,
            user_id,
            workspace_id,
        )

        return user_skill

    async def _generate_content(
        self,
        *,
        template: SkillTemplate,
        experience_description: str,
        user_id: UUID,
        workspace_id: UUID,
    ) -> str:
        """Generate personalized skill content via AI.

        Reuses GenerateRoleSkillService pattern with template content
        as context. Falls back to template content + experience if AI unavailable.

        Args:
            template: SkillTemplate with name, skill_content, role_type.
            experience_description: User's experience description.
            user_id: The user UUID for rate limiting.
            workspace_id: The workspace UUID for API key resolution.

        Returns:
            Generated skill content markdown.
        """
        role_type = template.role_type or "custom"
        template_name = template.name

        gen_service = GenerateRoleSkillService(self._session)
        payload = GenerateRoleSkillPayload(
            role_type=role_type,
            experience_description=experience_description,
            role_name=template_name,
            workspace_id=workspace_id,
            user_id=user_id,
        )

        result = await gen_service.execute(payload)
        return result.skill_content


__all__ = ["CreateUserSkillService"]
