"""Pydantic v2 request/response schemas for user skill endpoints.

Source: Phase 20, P20-06
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UserSkillSchema(BaseModel):
    """Response schema for a single user skill.

    Includes computed template_name from joined SkillTemplate relationship.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    workspace_id: UUID
    template_id: UUID | None
    skill_content: str
    experience_description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    template_name: str | None = None


class UserSkillCreate(BaseModel):
    """Request body for creating a user skill.

    Either template_id (template-based) or skill_content (custom) is required.
    """

    template_id: UUID | None = Field(default=None, description="Source template UUID")
    skill_content: str | None = Field(
        default=None,
        description="Skill markdown content (for custom skills without template)",
        max_length=15000,
    )
    experience_description: str | None = Field(
        default=None,
        description="Natural language input for AI personalization",
    )


class UserSkillUpdate(BaseModel):
    """Request body for updating a user skill.

    All fields optional -- only provided fields are applied.
    """

    is_active: bool | None = None
    experience_description: str | None = None


__all__ = [
    "UserSkillCreate",
    "UserSkillSchema",
    "UserSkillUpdate",
]
