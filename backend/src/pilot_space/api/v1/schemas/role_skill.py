"""Role skill API schemas.

Request and response schemas for role template and role skill endpoints.

Source: 011-role-based-skills, T008
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from pilot_space.api.v1.schemas.base import BaseSchema

# ---------------------------------------------------------------------------
# Role Templates
# ---------------------------------------------------------------------------


class RoleTemplateResponse(BaseSchema):
    """Schema for a single role template.

    Source: FR-001, US1
    """

    id: UUID = Field(description="Template ID")
    role_type: str = Field(description="Enum key (e.g., 'developer')")
    display_name: str = Field(description="Human-readable name")
    description: str = Field(description="Brief role description")
    icon: str = Field(description="Frontend icon identifier")
    sort_order: int = Field(description="Display order")
    version: int = Field(description="Template version number")
    default_skill_content: str = Field(description="Default SKILL.md content")


class RoleTemplateListResponse(BaseSchema):
    """Wrapper for role template list.

    GET /api/v1/role-templates
    """

    templates: list[RoleTemplateResponse] = Field(description="List of role templates")


# ---------------------------------------------------------------------------
# Role Skills
# ---------------------------------------------------------------------------


class RoleSkillResponse(BaseSchema):
    """Schema for a single user role skill.

    Source: FR-009, US6
    """

    id: UUID = Field(description="Skill record ID")
    role_type: str = Field(description="Role type")
    role_name: str = Field(description="Display name")
    skill_content: str = Field(description="Full SKILL.md markdown content")
    experience_description: str | None = Field(
        default=None, description="User's input for AI generation"
    )
    is_primary: bool = Field(description="Primary role flag")
    template_version: int | None = Field(default=None, description="Version of template used")
    template_update_available: bool = Field(
        default=False, description="True if template has newer version"
    )
    word_count: int = Field(description="Computed word count of skill_content")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")


class RoleSkillListResponse(BaseSchema):
    """Wrapper for role skill list.

    GET /api/v1/workspaces/{workspace_id}/role-skills
    """

    skills: list[RoleSkillResponse] = Field(
        description="List of user's role skills in this workspace"
    )


class CreateRoleSkillRequest(BaseSchema):
    """Request to create a new role skill.

    POST /api/v1/workspaces/{workspace_id}/role-skills
    Source: FR-002, FR-018, FR-020, US1, US6
    """

    role_type: str = Field(description="One of predefined types or 'custom'")
    role_name: str = Field(min_length=1, max_length=100, description="Display name (1-100 chars)")
    skill_content: str = Field(
        min_length=1, max_length=15000, description="SKILL.md content (1-15000 chars)"
    )
    experience_description: str | None = Field(
        default=None, max_length=5000, description="Experience for AI generation"
    )
    is_primary: bool = Field(
        default=False,
        description="If true and another primary exists, demotes the other",
    )


class UpdateRoleSkillRequest(BaseSchema):
    """Request to update an existing role skill.

    PUT /api/v1/workspaces/{workspace_id}/role-skills/{skill_id}
    Source: FR-009, FR-010, US6
    """

    role_name: str | None = Field(
        default=None, min_length=1, max_length=100, description="Display name"
    )
    skill_content: str | None = Field(
        default=None,
        min_length=1,
        max_length=15000,
        description="SKILL.md content",
    )
    is_primary: bool | None = Field(default=None, description="If true, demotes other primary")


# ---------------------------------------------------------------------------
# AI Generation
# ---------------------------------------------------------------------------


class GenerateRoleSkillRequest(BaseSchema):
    """Request to generate a role skill via AI.

    POST /api/v1/workspaces/{workspace_id}/role-skills/generate
    Source: FR-003, FR-004, US2
    """

    role_type: str = Field(description="One of predefined types or 'custom'")
    role_name: str | None = Field(
        default=None,
        max_length=100,
        description="Optional role name; AI generates one if omitted",
    )
    experience_description: str = Field(
        min_length=10,
        max_length=5000,
        description="User's experience description (10-5000 chars)",
    )

    @field_validator("experience_description")
    @classmethod
    def validate_experience_meaningful(cls, v: str) -> str:
        """Ensure experience description has meaningful content."""
        stripped = v.strip()
        if len(stripped) < 10:
            msg = "Experience description must be at least 10 characters"
            raise ValueError(msg)
        return stripped


class GenerateRoleSkillResponse(BaseSchema):
    """Response from AI role skill generation.

    Source: FR-003, FR-004, US2
    """

    skill_content: str = Field(description="Generated SKILL.md content")
    suggested_role_name: str = Field(description="AI-generated role name based on description")
    word_count: int = Field(description="Word count of generated content")
    generation_model: str = Field(description="Model used for generation")
    generation_time_ms: int = Field(description="Generation latency in ms")


class RegenerateRoleSkillRequest(BaseSchema):
    """Request to regenerate an existing role skill via AI.

    POST /api/v1/workspaces/{workspace_id}/role-skills/{skill_id}/regenerate
    Source: FR-003, FR-015, US6
    """

    experience_description: str = Field(
        min_length=10,
        max_length=5000,
        description="Updated experience description (10-5000 chars)",
    )

    @field_validator("experience_description")
    @classmethod
    def validate_experience_meaningful(cls, v: str) -> str:
        """Ensure experience description has meaningful content."""
        stripped = v.strip()
        if len(stripped) < 10:
            msg = "Experience description must be at least 10 characters"
            raise ValueError(msg)
        return stripped


class RegenerateRoleSkillResponse(GenerateRoleSkillResponse):
    """Response from AI role skill regeneration.

    Extends generate response with previous content for comparison.
    """

    previous_skill_content: str = Field(description="Current skill content for comparison")
    previous_role_name: str = Field(description="Current role name for comparison")


__all__ = [
    "CreateRoleSkillRequest",
    "GenerateRoleSkillRequest",
    "GenerateRoleSkillResponse",
    "RegenerateRoleSkillRequest",
    "RegenerateRoleSkillResponse",
    "RoleSkillListResponse",
    "RoleSkillResponse",
    "RoleTemplateListResponse",
    "RoleTemplateResponse",
    "UpdateRoleSkillRequest",
]
