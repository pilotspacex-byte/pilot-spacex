"""Pydantic v2 request/response schemas for workspace role skill endpoints.

Source: Phase 16, WRSKL-01..02
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from pilot_space.application.services.role_skill.types import VALID_ROLE_TYPES


class GenerateWorkspaceSkillRequest(BaseModel):
    """Request body for generating a workspace skill.

    Only ``experience_description`` is required — AI generates a skill name
    and content from it.  ``role_type`` and ``role_name`` are kept for
    backward compatibility but default to ``"custom"`` / ``""`` when omitted.
    """

    role_type: str = Field(
        default="custom",
        description=f"SDLC role type; one of: {sorted(VALID_ROLE_TYPES)}. Defaults to 'custom'.",
    )
    role_name: str = Field(
        default="",
        description="Human-readable display name. AI generates one when empty.",
    )
    experience_description: str = Field(
        description="Natural language description of experience for AI generation"
    )


class WorkspaceRoleSkillResponse(BaseModel):
    """Response schema for a single workspace role skill."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    role_type: str
    role_name: str
    skill_content: str
    experience_description: str | None
    tags: list[str] = []
    usage: str | None = None
    is_active: bool
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime


class WorkspaceRoleSkillListResponse(BaseModel):
    """Response schema for a list of workspace role skills."""

    skills: list[WorkspaceRoleSkillResponse]


__all__ = [
    "GenerateWorkspaceSkillRequest",
    "WorkspaceRoleSkillListResponse",
    "WorkspaceRoleSkillResponse",
]
