"""Project schemas for API requests/responses.

Pydantic models for project CRUD operations.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import Field

from pilot_space.api.v1.schemas.base import BaseSchema, EntitySchema


class ProjectCreate(BaseSchema):
    """Create project request.

    Attributes:
        name: Project display name.
        identifier: Unique project identifier (e.g., 'PROJ').
        description: Optional project description.
        workspace_id: Parent workspace ID.
    """

    name: str = Field(
        min_length=1,
        max_length=255,
        description="Project display name",
    )
    identifier: str = Field(
        min_length=2,
        max_length=10,
        pattern=r"^[A-Z][A-Z0-9]*$",
        description="Unique identifier (uppercase letters and numbers, starts with letter)",
    )
    description: str | None = Field(
        default=None,
        max_length=2000,
        description="Project description",
    )
    workspace_id: UUID = Field(description="Parent workspace ID")


class ProjectUpdate(BaseSchema):
    """Update project request.

    Attributes:
        name: New project name.
        description: New project description.
        settings: Project-level settings.
    """

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="New project name",
    )
    description: str | None = Field(
        default=None,
        max_length=2000,
        description="New description",
    )
    settings: dict[str, Any] | None = Field(
        default=None,
        description="Project settings (merged with existing)",
    )


class StateResponse(BaseSchema):
    """Workflow state response.

    Attributes:
        id: State identifier.
        name: State display name.
        group: State group (unstarted, started, completed, cancelled).
        color: Display color.
        sequence: Sort order.
    """

    id: UUID = Field(description="State identifier")
    name: str = Field(description="State display name")
    group: str = Field(description="State group")
    color: str = Field(description="Display color")
    sequence: int = Field(description="Sort order")


class LeadBriefResponse(BaseSchema):
    """Brief lead user info for project responses."""

    id: UUID
    email: str
    display_name: str | None = None


class ProjectResponse(EntitySchema):
    """Project response.

    Attributes:
        name: Project display name.
        identifier: Unique project identifier.
        description: Project description.
        workspace_id: Parent workspace ID.
        lead_id: Optional lead user ID.
        lead: Optional lead user brief info.
        icon: Optional icon identifier.
        issue_count: Number of issues.
        open_issue_count: Number of open issues.
    """

    name: str = Field(description="Project display name")
    identifier: str = Field(description="Unique identifier")
    description: str | None = Field(default=None, description="Project description")
    workspace_id: UUID = Field(description="Parent workspace ID")
    lead_id: UUID | None = Field(default=None, description="Lead user ID")
    lead: LeadBriefResponse | None = Field(default=None, description="Lead user info")
    icon: str | None = Field(default=None, description="Icon identifier")
    issue_count: int = Field(default=0, description="Total number of issues")
    open_issue_count: int = Field(default=0, description="Number of open issues")


class ProjectDetailResponse(ProjectResponse):
    """Detailed project response with states.

    Attributes:
        settings: Project-level settings.
        states: Workflow states for this project.
    """

    settings: dict[str, Any] | None = Field(default=None, description="Project settings")
    states: list[StateResponse] = Field(  # pyright: ignore[reportUnknownVariableType]
        default_factory=list, description="Workflow states"
    )


__all__ = [
    "ProjectCreate",
    "ProjectDetailResponse",
    "ProjectResponse",
    "ProjectUpdate",
    "StateResponse",
]
