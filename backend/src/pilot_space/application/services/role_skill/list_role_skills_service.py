"""ListRoleSkillsService for querying user role skills.

Implements CQRS-lite query pattern.

Source: 011-role-based-skills, T009, FR-009
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ListRoleSkillsPayload:
    """Payload for listing role skills."""

    user_id: UUID
    workspace_id: UUID


@dataclass(frozen=True, slots=True)
class RoleSkillItem:
    """Single role skill in list result."""

    id: UUID
    role_type: str
    role_name: str
    skill_content: str
    experience_description: str | None
    is_primary: bool
    template_version: int | None
    template_update_available: bool
    word_count: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ListRoleSkillsResult:
    """Result from listing role skills."""

    skills: list[RoleSkillItem] = field(default_factory=list)


class ListRoleSkillsService:
    """Service for listing user role skills in a workspace.

    Returns skills with computed template_update_available and word_count.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def execute(self, payload: ListRoleSkillsPayload) -> ListRoleSkillsResult:
        """List all role skills for a user in a workspace.

        Args:
            payload: User and workspace IDs.

        Returns:
            ListRoleSkillsResult with skills ordered primary-first.
        """
        from pilot_space.infrastructure.database.repositories.role_skill_repository import (
            RoleSkillRepository,
            RoleTemplateRepository,
        )

        skill_repo = RoleSkillRepository(self._session)
        template_repo = RoleTemplateRepository(self._session)

        skills = await skill_repo.get_by_user_workspace(payload.user_id, payload.workspace_id)

        # Build template version lookup for update detection
        templates = await template_repo.get_all_ordered()
        template_versions: dict[str, int] = {t.role_type: t.version for t in templates}

        items: list[RoleSkillItem] = []
        for skill in skills:
            current_template_version = template_versions.get(skill.role_type)
            update_available = (
                skill.template_version is not None
                and current_template_version is not None
                and current_template_version > skill.template_version
            )

            items.append(
                RoleSkillItem(
                    id=skill.id,
                    role_type=skill.role_type,
                    role_name=skill.role_name,
                    skill_content=skill.skill_content,
                    experience_description=skill.experience_description,
                    is_primary=skill.is_primary,
                    template_version=skill.template_version,
                    template_update_available=update_available,
                    word_count=len(skill.skill_content.split()),
                    created_at=skill.created_at,
                    updated_at=skill.updated_at,
                )
            )

        return ListRoleSkillsResult(skills=items)


__all__ = [
    "ListRoleSkillsPayload",
    "ListRoleSkillsResult",
    "ListRoleSkillsService",
    "RoleSkillItem",
]
