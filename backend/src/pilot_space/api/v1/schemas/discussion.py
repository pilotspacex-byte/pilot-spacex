"""Discussion API schemas.

Request and response schemas for threaded discussions on notes.
Supports AI-assisted discussion and multi-turn conversations.

T094: Discussion schemas.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import Field

from pilot_space.api.v1.schemas.base import BaseSchema, EntitySchema, PaginatedResponse


class DiscussionStatus(StrEnum):
    """Status of a discussion thread."""

    OPEN = "open"
    RESOLVED = "resolved"
    ARCHIVED = "archived"


class CommentType(StrEnum):
    """Type of comment in a discussion."""

    USER = "user"  # Regular user comment
    AI = "ai"  # AI-generated response
    SYSTEM = "system"  # System message


class CommentCreate(BaseSchema):
    """Schema for creating a comment.

    Attributes:
        content: Comment content.
        mention_user_ids: Users mentioned in the comment.
    """

    content: str = Field(
        min_length=1,
        max_length=5000,
        description="Comment content",
    )
    mention_user_ids: list[UUID] | None = Field(
        default=None,
        description="Mentioned user IDs",
    )


class CommentUpdate(BaseSchema):
    """Schema for updating a comment."""

    content: str = Field(
        min_length=1,
        max_length=5000,
        description="Updated content",
    )


class CommentResponse(EntitySchema):
    """Schema for comment response."""

    discussion_id: UUID = Field(description="Parent discussion ID")
    author_id: UUID | None = Field(
        default=None,
        description="Author user ID (null for AI/system)",
    )
    author_name: str | None = Field(
        default=None,
        description="Author display name",
    )
    author_avatar: str | None = Field(
        default=None,
        description="Author avatar URL",
    )
    content: str = Field(description="Comment content")
    type: CommentType = Field(
        default=CommentType.USER,
        description="Comment type",
    )
    is_edited: bool = Field(
        default=False,
        description="Whether comment was edited",
    )
    mention_user_ids: list[UUID] = Field(  # pyright: ignore[reportUnknownVariableType]
        default_factory=list,
        description="Mentioned user IDs",
    )


class DiscussionCreate(BaseSchema):
    """Schema for creating a discussion thread.

    Attributes:
        note_id: Note this discussion belongs to.
        block_id: Optional block ID for context.
        title: Optional discussion title.
        initial_comment: First comment content.
    """

    note_id: UUID = Field(description="Note ID")
    block_id: str | None = Field(
        default=None,
        description="Block ID for contextual discussion",
    )
    title: str | None = Field(
        default=None,
        max_length=255,
        description="Discussion title",
    )
    initial_comment: str = Field(
        min_length=1,
        max_length=5000,
        description="First comment content",
    )


class DiscussionUpdate(BaseSchema):
    """Schema for updating a discussion."""

    title: str | None = Field(
        default=None,
        max_length=255,
        description="Updated title",
    )
    status: DiscussionStatus | None = Field(
        default=None,
        description="Updated status",
    )


class DiscussionResponse(EntitySchema):
    """Schema for discussion response."""

    note_id: UUID = Field(description="Note ID")
    block_id: str | None = Field(default=None, description="Block ID")
    title: str | None = Field(default=None, description="Discussion title")
    status: DiscussionStatus = Field(
        default=DiscussionStatus.OPEN,
        description="Discussion status",
    )
    started_by_id: UUID = Field(description="User who started discussion")
    started_by_name: str | None = Field(default=None, description="Starter name")
    comment_count: int = Field(default=0, description="Total comments")
    participant_count: int = Field(default=0, description="Unique participants")
    last_activity_at: datetime | None = Field(
        default=None,
        description="Last activity timestamp",
    )


class DiscussionDetailResponse(DiscussionResponse):
    """Schema for detailed discussion with comments."""

    comments: list[CommentResponse] = Field(  # pyright: ignore[reportUnknownVariableType]
        default_factory=list,
        description="Discussion comments",
    )
    participants: list[dict[str, Any]] = Field(  # pyright: ignore[reportUnknownVariableType]
        default_factory=list,
        description="Discussion participants",
    )


class DiscussionListResponse(PaginatedResponse[DiscussionResponse]):
    """Paginated list of discussions."""


class DiscussionSummary(BaseSchema):
    """Summary of discussions for a note."""

    total: int = Field(description="Total discussions")
    open: int = Field(description="Open discussions")
    resolved: int = Field(description="Resolved discussions")
    recent_activity: list[DiscussionResponse] = Field(  # pyright: ignore[reportUnknownVariableType]
        default_factory=list,
        description="Recent active discussions",
    )


# AI-assisted discussion


class AIDiscussionRequest(BaseSchema):
    """Request for AI-assisted discussion response."""

    discussion_id: UUID = Field(description="Discussion ID")
    message: str = Field(
        min_length=1,
        max_length=2000,
        description="User message for AI",
    )
    include_note_context: bool = Field(
        default=True,
        description="Include note content as context",
    )


class AIDiscussionResponse(BaseSchema):
    """Response from AI discussion assistant."""

    discussion_id: UUID = Field(description="Discussion ID")
    ai_response: str = Field(description="AI-generated response")
    suggested_actions: list[str] = Field(
        default_factory=list,
        description="Suggested follow-up actions",
    )
    references: list[dict[str, Any]] = Field(  # pyright: ignore[reportUnknownVariableType]
        default_factory=list,
        description="Relevant references found",
    )


class AIDiscussionStreamChunk(BaseSchema):
    """Streaming chunk for AI discussion response."""

    chunk: str = Field(description="Response chunk")
    done: bool = Field(default=False, description="Whether stream is complete")


__all__ = [
    "AIDiscussionRequest",
    "AIDiscussionResponse",
    "AIDiscussionStreamChunk",
    "CommentCreate",
    "CommentResponse",
    "CommentType",
    "CommentUpdate",
    "DiscussionCreate",
    "DiscussionDetailResponse",
    "DiscussionListResponse",
    "DiscussionResponse",
    "DiscussionStatus",
    "DiscussionSummary",
    "DiscussionUpdate",
]
