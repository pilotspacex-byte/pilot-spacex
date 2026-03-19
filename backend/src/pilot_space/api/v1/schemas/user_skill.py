"""Pydantic v2 request/response schemas for user skill endpoints.

Source: Phase 20, P20-06
"""

from __future__ import annotations

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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
    tags: list[str] = Field(default_factory=list)
    usage: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    template_name: str | None = None
    skill_name: str | None = None


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
    skill_name: str | None = Field(
        default=None,
        description="User-visible skill name (AI-suggested or user-edited)",
        max_length=200,
    )
    tags: list[str] = Field(default_factory=list, max_length=20)
    usage: str | None = Field(default=None, max_length=500)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        """Strip whitespace and enforce max 30 chars per tag."""
        return [tag.strip()[:30] for tag in v if tag.strip()]

    @model_validator(mode="after")
    def require_template_or_content(self) -> Self:
        """Ensure either template_id or skill_content is provided."""
        if not self.template_id and not self.skill_content:
            msg = "Either template_id or skill_content is required"
            raise ValueError(msg)
        return self


class UserSkillUpdate(BaseModel):
    """Request body for updating a user skill.

    All fields optional -- only provided fields are applied.
    """

    is_active: bool | None = None
    experience_description: str | None = None
    skill_content: str | None = Field(
        default=None,
        description="Updated skill markdown content",
        max_length=15000,
    )
    skill_name: str | None = Field(
        default=None,
        description="Updated user-visible skill name",
        max_length=200,
    )
    tags: list[str] | None = Field(default=None, max_length=20)
    usage: str | None = Field(default=None, max_length=500)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str] | None) -> list[str] | None:
        """Strip whitespace and enforce max 30 chars per tag."""
        if v is None:
            return v
        return [tag.strip()[:30] for tag in v if tag.strip()]


__all__ = [
    "UserSkillCreate",
    "UserSkillSchema",
    "UserSkillUpdate",
]
