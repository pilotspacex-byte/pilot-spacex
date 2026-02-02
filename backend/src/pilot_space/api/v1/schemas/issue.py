"""Issue API schemas.

T140: Create Issue Pydantic schemas for API layer.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from pilot_space.api.v1.schemas.base import BaseSchema
from pilot_space.infrastructure.database.models import IssuePriority, StateGroup

# ============================================================================
# Base Schemas
# ============================================================================


class UserBriefSchema(BaseSchema):
    """Brief user information for nested responses."""

    id: UUID
    email: str
    display_name: str | None = None


class StateBriefSchema(BaseSchema):
    """Brief state information for nested responses."""

    id: UUID
    name: str
    color: str
    group: StateGroup


class LabelBriefSchema(BaseSchema):
    """Brief label information for nested responses."""

    id: UUID
    name: str
    color: str


class ProjectBriefSchema(BaseSchema):
    """Brief project information for nested responses."""

    id: UUID
    name: str
    identifier: str


# ============================================================================
# Issue Schemas
# ============================================================================


class IssueCreateRequest(BaseSchema):
    """Request to create an issue."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    description_html: str | None = None
    priority: IssuePriority = IssuePriority.NONE
    state_id: UUID | None = None
    project_id: UUID
    assignee_id: UUID | None = None
    cycle_id: UUID | None = None
    module_id: UUID | None = None
    parent_id: UUID | None = None
    estimate_points: int | None = Field(None, ge=0, le=100)
    start_date: date | None = None
    target_date: date | None = None
    label_ids: list[UUID] = Field(default_factory=list)

    # AI enhancement request
    enhance_with_ai: bool = False


class IssueUpdateRequest(BaseSchema):
    """Request to update an issue."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    description_html: str | None = None
    priority: IssuePriority | None = None
    state_id: UUID | None = None
    assignee_id: UUID | None = None
    cycle_id: UUID | None = None
    module_id: UUID | None = None
    parent_id: UUID | None = None
    estimate_points: int | None = Field(None, ge=0, le=100)
    start_date: date | None = None
    target_date: date | None = None
    sort_order: int | None = None
    label_ids: list[UUID] | None = None

    # Explicit null fields (for clearing values)
    clear_assignee: bool = False
    clear_cycle: bool = False
    clear_module: bool = False
    clear_parent: bool = False
    clear_estimate: bool = False
    clear_start_date: bool = False
    clear_target_date: bool = False


class IssueResponse(BaseSchema):
    """Full issue response."""

    id: UUID
    workspace_id: UUID
    sequence_id: int
    identifier: str
    name: str
    description: str | None
    description_html: str | None
    priority: IssuePriority
    estimate_points: int | None
    start_date: date | None
    target_date: date | None
    sort_order: int
    created_at: datetime
    updated_at: datetime

    # Foreign key IDs (needed by frontend for update operations)
    project_id: UUID
    assignee_id: UUID | None
    reporter_id: UUID
    cycle_id: UUID | None
    parent_id: UUID | None

    # Relations
    project: ProjectBriefSchema
    state: StateBriefSchema
    assignee: UserBriefSchema | None
    reporter: UserBriefSchema
    labels: list[LabelBriefSchema]

    # AI metadata
    ai_metadata: dict[str, Any] | None
    has_ai_enhancements: bool

    # Counts
    sub_issue_count: int = 0

    @classmethod
    def from_issue(cls, issue: Any) -> IssueResponse:
        """Create from Issue model."""
        return cls(
            id=issue.id,
            workspace_id=issue.workspace_id,
            sequence_id=issue.sequence_id,
            identifier=issue.identifier,
            name=issue.name,
            description=issue.description,
            description_html=issue.description_html,
            priority=issue.priority,
            estimate_points=issue.estimate_points,
            start_date=issue.start_date,
            target_date=issue.target_date,
            sort_order=issue.sort_order,
            created_at=issue.created_at,
            updated_at=issue.updated_at,
            project_id=issue.project_id,
            assignee_id=issue.assignee_id,
            reporter_id=issue.reporter_id,
            cycle_id=issue.cycle_id,
            parent_id=issue.parent_id,
            project=ProjectBriefSchema.model_validate(issue.project),
            state=StateBriefSchema.model_validate(issue.state),
            assignee=UserBriefSchema.model_validate(issue.assignee) if issue.assignee else None,
            reporter=UserBriefSchema.model_validate(issue.reporter),
            labels=[LabelBriefSchema.model_validate(label) for label in issue.labels],
            ai_metadata=issue.ai_metadata,
            has_ai_enhancements=issue.has_ai_enhancements,
            sub_issue_count=len(issue.sub_issues) if issue.sub_issues else 0,
        )


class IssueListResponse(BaseSchema):
    """Paginated issue list response."""

    items: list[IssueResponse]
    total: int
    next_cursor: str | None
    prev_cursor: str | None
    has_next: bool
    has_prev: bool
    page_size: int


class IssueBriefResponse(BaseSchema):
    """Brief issue response for lists and references."""

    id: UUID
    identifier: str
    name: str
    priority: IssuePriority
    state: StateBriefSchema
    assignee: UserBriefSchema | None


# ============================================================================
# Activity Schemas
# ============================================================================


class ActivityResponse(BaseSchema):
    """Activity response for timeline."""

    id: UUID
    activity_type: str
    field: str | None
    old_value: str | None
    new_value: str | None
    comment: str | None
    metadata: dict[str, Any] | None
    created_at: datetime
    actor: UserBriefSchema | None


class ActivityTimelineResponse(BaseSchema):
    """Activity timeline response."""

    activities: list[ActivityResponse]
    total: int


class CommentCreateRequest(BaseSchema):
    """Request to add a comment."""

    content: str = Field(..., min_length=1, max_length=10000)


# ============================================================================
# Filter Schemas
# ============================================================================


class IssueFilterParams(BaseSchema):
    """Query parameters for issue filtering."""

    project_id: UUID | None = None
    state_ids: list[UUID] | None = None
    state_groups: list[StateGroup] | None = None
    assignee_ids: list[UUID] | None = None
    label_ids: list[UUID] | None = None
    cycle_id: UUID | None = None
    module_id: UUID | None = None
    priorities: list[IssuePriority] | None = None
    start_date_from: date | None = None
    start_date_to: date | None = None
    target_date_from: date | None = None
    target_date_to: date | None = None
    search: str | None = None
    has_ai_enhancements: bool | None = None

    # Pagination
    cursor: str | None = None
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: str = "created_at"
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


__all__ = [
    "ActivityResponse",
    "ActivityTimelineResponse",
    "CommentCreateRequest",
    "IssueBriefResponse",
    "IssueCreateRequest",
    "IssueFilterParams",
    "IssueListResponse",
    "IssueResponse",
    "IssueUpdateRequest",
    "LabelBriefSchema",
    "ProjectBriefSchema",
    "StateBriefSchema",
    "UserBriefSchema",
]
