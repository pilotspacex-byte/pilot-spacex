"""Annotation API schemas.

Request and response schemas for note annotation endpoints.
Includes AI-generated annotations and user actions.

T093: Annotation schemas.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator

from pilot_space.api.v1.schemas.base import BaseSchema, EntitySchema, PaginatedResponse


class AnnotationType(StrEnum):
    """Types of margin annotations.

    Aligns with AI agent output (margin_annotation_agent_sdk.py)
    and database model (note_annotation.py).
    """

    SUGGESTION = "suggestion"  # Improvement suggestion
    WARNING = "warning"  # Potential issue
    QUESTION = "question"  # Clarification needed
    INSIGHT = "insight"  # Additional context (alias: info in DB)
    REFERENCE = "reference"  # Related content link
    ISSUE_CANDIDATE = "issue_candidate"  # Can become a tracked issue
    INFO = "info"  # Informational (DB compatibility)


class AnnotationStatus(StrEnum):
    """Status of an annotation.

    Aligns with database model (note_annotation.py).
    """

    PENDING = "pending"  # Not yet acted upon
    ACCEPTED = "accepted"  # User accepted the suggestion
    REJECTED = "rejected"  # User rejected the suggestion
    DISMISSED = "dismissed"  # User dismissed without action
    CONVERTED = "converted"  # Converted to issue or action


class AnnotationCreate(BaseSchema):
    """Schema for creating an annotation manually.

    Primarily used for user-created annotations.
    AI-generated annotations use the analyze endpoint.
    """

    note_id: UUID = Field(description="Note ID")
    block_id: str = Field(description="Block ID this annotation relates to")
    type: AnnotationType = Field(description="Annotation type")
    content: str = Field(
        min_length=1,
        max_length=1000,
        description="Annotation content",
    )
    highlight_start: int | None = Field(
        default=None,
        ge=0,
        description="Start position of highlight",
    )
    highlight_end: int | None = Field(
        default=None,
        ge=0,
        description="End position of highlight",
    )

    @field_validator("highlight_end")
    @classmethod
    def validate_highlight_positions(
        cls,
        v: int | None,
        info: Any,
    ) -> int | None:
        """Validate highlight end is after start."""
        if v is not None:
            start = info.data.get("highlight_start")
            if start is not None and v < start:
                raise ValueError("highlight_end must be >= highlight_start")
        return v


class AnnotationStatusUpdate(BaseSchema):
    """Schema for updating annotation status."""

    status: AnnotationStatus = Field(description="New status")
    converted_issue_id: UUID | None = Field(
        default=None,
        description="Issue ID if converted to issue",
    )


class AnnotationResponse(EntitySchema):
    """Schema for annotation response."""

    note_id: UUID = Field(description="Note ID")
    block_id: str = Field(description="Block ID")
    type: AnnotationType = Field(description="Annotation type")
    content: str = Field(description="Annotation content")
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="AI confidence score",
    )
    status: AnnotationStatus = Field(
        default=AnnotationStatus.PENDING,
        description="Current status",
    )
    highlight_start: int | None = Field(default=None, description="Highlight start")
    highlight_end: int | None = Field(default=None, description="Highlight end")
    is_ai_generated: bool = Field(
        default=False,
        description="Whether AI generated this annotation",
    )
    created_by_id: UUID | None = Field(
        default=None,
        description="Creator user ID (null for AI)",
    )
    converted_issue_id: UUID | None = Field(
        default=None,
        description="Converted issue ID",
    )


class AnnotationListResponse(PaginatedResponse[AnnotationResponse]):
    """Paginated list of annotations."""


class AnnotationSummary(BaseSchema):
    """Summary of annotations for a note."""

    total: int = Field(description="Total annotations")
    pending: int = Field(description="Pending annotations")
    accepted: int = Field(description="Accepted annotations")
    dismissed: int = Field(description="Dismissed annotations")
    converted: int = Field(description="Converted to issues")
    by_type: dict[str, int] = Field(
        default_factory=dict,
        description="Count by annotation type",
    )


class AnnotationBulkAction(BaseSchema):
    """Schema for bulk annotation actions."""

    annotation_ids: list[UUID] = Field(
        min_length=1,
        max_length=50,
        description="Annotation IDs to update",
    )
    action: AnnotationStatus = Field(description="Action to apply")


class AnnotationBulkResponse(BaseSchema):
    """Response for bulk annotation actions."""

    updated: int = Field(description="Number of annotations updated")
    failed: list[UUID] = Field(  # pyright: ignore[reportUnknownVariableType]
        default_factory=list,
        description="IDs that failed to update",
    )


# AI Analysis Request/Response


class AnalyzeNoteRequest(BaseSchema):
    """Request to analyze a note for annotations."""

    note_id: UUID = Field(description="Note ID to analyze")
    block_ids: list[str] | None = Field(
        default=None,
        description="Specific block IDs to analyze (null for all)",
    )
    min_confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold",
    )


class AnalyzeNoteResponse(BaseSchema):
    """Response from note analysis."""

    note_id: UUID = Field(description="Note ID")
    annotations: list[AnnotationResponse] = Field(description="Generated annotations")
    blocks_analyzed: int = Field(description="Number of blocks analyzed")
    processing_time_ms: float = Field(description="Processing time in milliseconds")


__all__ = [
    "AnalyzeNoteRequest",
    "AnalyzeNoteResponse",
    "AnnotationBulkAction",
    "AnnotationBulkResponse",
    "AnnotationCreate",
    "AnnotationListResponse",
    "AnnotationResponse",
    "AnnotationStatus",
    "AnnotationStatusUpdate",
    "AnnotationSummary",
    "AnnotationType",
]
