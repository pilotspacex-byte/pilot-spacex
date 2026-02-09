"""Pydantic schemas for Homepage Hub API endpoints.

Defines request/response models for:
- Activity feed (recent notes + issues grouped by day)
- AI Digest (suggestions, refresh, dismiss)
- Chat-to-note creation

References:
- specs/012-homepage-note/spec.md API Endpoints section
- US-19: Homepage Hub feature
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from pilot_space.api.v1.schemas.base import BaseSchema

# ── Shared nested schemas ──────────────────────────────────────────────


class ProjectBrief(BaseSchema):
    """Minimal project info embedded in activity cards."""

    id: UUID
    name: str
    identifier: str


class AnnotationPreview(BaseSchema):
    """Latest AI annotation preview for note activity cards."""

    type: str = Field(description="Annotation type (suggestion, question, etc.)")
    content: str = Field(description="Annotation text content")
    confidence: float = Field(ge=0.0, le=1.0, description="AI confidence score")


class StateBrief(BaseSchema):
    """Issue state info for activity cards."""

    name: str
    color: str
    group: str = Field(description="State group: unstarted, started, completed, cancelled")


class AssigneeBrief(BaseSchema):
    """Assignee info for issue activity cards."""

    id: UUID
    name: str
    avatar_url: str | None = None


# ── Activity Feed schemas ──────────────────────────────────────────────


class ActivityCardNote(BaseSchema):
    """Activity card for a recent note."""

    type: Literal["note"] = "note"
    id: UUID
    title: str
    project: ProjectBrief | None = None
    topics: list[str] = Field(default_factory=list, description="Note topic tags")
    word_count: int = Field(ge=0)
    latest_annotation: AnnotationPreview | None = None
    updated_at: datetime
    is_pinned: bool = False


class ActivityCardIssue(BaseSchema):
    """Activity card for a recent issue."""

    type: Literal["issue"] = "issue"
    id: UUID
    identifier: str = Field(description="Human-readable issue ID (e.g. PS-42)")
    title: str
    project: ProjectBrief | None = None
    state: StateBrief | None = None
    priority: str = Field(description="Issue priority: none, low, medium, high, urgent")
    assignee: AssigneeBrief | None = None
    last_activity: str | None = Field(default=None, description="Most recent activity summary")
    updated_at: datetime


# Union type for activity cards
ActivityCard = ActivityCardNote | ActivityCardIssue


class ActivityGroupedData(BaseSchema):
    """Activity items grouped by time period."""

    today: list[ActivityCard] = Field(default_factory=list)
    yesterday: list[ActivityCard] = Field(default_factory=list)
    this_week: list[ActivityCard] = Field(default_factory=list)


class ActivityMeta(BaseSchema):
    """Pagination metadata for activity feed."""

    total: int = Field(ge=0)
    cursor: str | None = None
    has_more: bool = False


class HomepageActivityResponse(BaseSchema):
    """Response for GET /homepage/activity."""

    data: ActivityGroupedData
    meta: ActivityMeta


# ── Digest schemas ─────────────────────────────────────────────────────


class DigestSuggestion(BaseSchema):
    """Single AI digest suggestion."""

    id: UUID = Field(description="Unique suggestion identifier")
    category: str = Field(
        description="Suggestion category (stale_issues, unlinked_notes, review_needed, etc.)"
    )
    title: str = Field(description="Short actionable title")
    description: str = Field(description="Detailed explanation")
    entity_id: UUID | None = Field(
        default=None, description="Related entity ID (issue, note, etc.)"
    )
    entity_type: str | None = Field(
        default=None, description="Entity type: issue, note, cycle, etc."
    )
    entity_identifier: str | None = Field(
        default=None, description="Human-readable entity identifier (e.g. PS-42)"
    )
    project_id: UUID | None = Field(default=None, description="Related project ID")
    project_name: str | None = Field(default=None, description="Related project name")
    action_type: str | None = Field(
        default=None, description="Action type: navigate or quick_action"
    )
    action_label: str | None = Field(
        default=None, description="Button label for the action (default: View)"
    )
    action_url: str | None = Field(default=None, description="Frontend route for quick action")
    relevance_score: float = Field(
        ge=0.0, le=1.0, default=0.5, description="Relevance to current user"
    )


class DigestData(BaseSchema):
    """Digest data payload."""

    generated_at: datetime
    generated_by: str = Field(description="Origin: scheduled or manual")
    suggestions: list[DigestSuggestion] = Field(default_factory=list)
    suggestion_count: int = Field(ge=0)


class DigestResponse(BaseSchema):
    """Response for GET /homepage/digest."""

    data: DigestData


class DigestRefreshData(BaseSchema):
    """Digest refresh status payload."""

    status: str = Field(description="Generation status: generating, completed, error")
    estimated_seconds: int = Field(ge=0, default=15)


class DigestRefreshResponse(BaseSchema):
    """Response for POST /homepage/digest/refresh."""

    data: DigestRefreshData


class DigestDismissPayload(BaseSchema):
    """Request body for POST /homepage/digest/dismiss."""

    suggestion_id: UUID = Field(description="ID of the suggestion being dismissed")
    entity_id: UUID | None = Field(
        default=None, description="ID of the related entity (null for workspace-wide suggestions)"
    )
    entity_type: str | None = Field(default=None, description="Type of entity: issue, note, etc.")
    category: str = Field(description="Suggestion category being dismissed")


# ── Chat-to-Note schemas ──────────────────────────────────────────────


class CreateNoteFromChatPayload(BaseSchema):
    """Request body for POST /notes/from-chat."""

    chat_session_id: UUID = Field(description="Source AI chat session ID")
    title: str = Field(min_length=1, max_length=500, description="Note title")
    project_id: UUID | None = Field(
        default=None, description="Optional project to associate the note with"
    )


class CreateNoteFromChatData(BaseSchema):
    """Response data for chat-to-note creation."""

    note_id: UUID
    title: str
    source_chat_session_id: UUID


class CreateNoteFromChatResponse(BaseSchema):
    """Response for POST /notes/from-chat."""

    data: CreateNoteFromChatData


__all__ = [
    "ActivityCard",
    "ActivityCardIssue",
    "ActivityCardNote",
    "ActivityGroupedData",
    "ActivityMeta",
    "AnnotationPreview",
    "AssigneeBrief",
    "CreateNoteFromChatData",
    "CreateNoteFromChatPayload",
    "CreateNoteFromChatResponse",
    "DigestData",
    "DigestDismissPayload",
    "DigestRefreshData",
    "DigestRefreshResponse",
    "DigestResponse",
    "DigestSuggestion",
    "HomepageActivityResponse",
    "ProjectBrief",
    "StateBrief",
]
