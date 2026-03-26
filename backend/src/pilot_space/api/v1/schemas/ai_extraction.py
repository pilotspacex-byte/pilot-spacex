"""Pydantic schemas for AI issue extraction endpoints.

Covers ExtractIssuesRequest, ExtractedIssueResponse, ExtractIssuesResponse,
ExtractedIssueInputSchema, CreateExtractedIssuesRequestSchema,
CreatedIssueData, CreateExtractedIssuesResponse.

T058-T059: Issue extraction and approval.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ExtractIssuesRequest(BaseModel):
    """Request for issue extraction."""

    note_title: str = Field(
        max_length=255,
        description="Note title",
    )
    note_content: dict[str, Any] = Field(description="TipTap JSON content")
    project_id: str | None = Field(
        default=None,
        description="Project ID for context",
    )
    project_context: str | None = Field(
        default=None,
        max_length=2000,
        description="Project description for context",
    )
    selected_text: str | None = Field(
        default=None,
        max_length=5000,
        description="User-selected text to focus on",
    )
    available_labels: list[str] | None = Field(
        default=None,
        max_length=50,
        description="Labels available in the project",
    )
    max_issues: int = Field(
        default=10,
        ge=1,
        le=20,
        description="Maximum number of issues to extract",
    )


class ExtractedIssueResponse(BaseModel):
    """Single extracted issue."""

    title: str = Field(description="Issue title")
    description: str = Field(description="Issue description")
    priority: int = Field(description="Suggested priority (0-4)")
    labels: list[str] = Field(description="Suggested labels")
    confidence_score: float = Field(description="Confidence score (0-1)")
    confidence_tag: str = Field(description="Confidence category")
    source_block_ids: list[str] = Field(default_factory=list, description="Source blocks")
    rationale: str = Field(default="", description="Extraction rationale")


class ExtractIssuesResponse(BaseModel):
    """Response for issue extraction."""

    issues: list[ExtractedIssueResponse] = Field(description="Extracted issues")
    recommended_count: int = Field(description="High confidence issues")
    total_count: int = Field(description="Total issues")
    processing_time_ms: float = Field(description="Processing time")


class ExtractedIssueInputSchema(BaseModel):
    """Single issue to create from extraction."""

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    priority: int = Field(default=4, ge=0, le=4)
    source_block_id: str | None = None


class CreateExtractedIssuesRequestSchema(BaseModel):
    """Request to create extracted issues (auto-approve, DD-003 non-destructive)."""

    issues: list[ExtractedIssueInputSchema] = Field(default_factory=list)
    project_id: str | None = Field(default=None, description="Project UUID to assign issues to")
    note_id: str | None = Field(
        default=None, description="Source note ID (for no-note extraction route)"
    )


class CreatedIssueData(BaseModel):
    """Single created issue in the response."""

    id: str
    identifier: str
    title: str


class CreateExtractedIssuesResponse(BaseModel):
    """Response for creating extracted issues."""

    created_issues: list[CreatedIssueData]
    created_count: int
    source_note_id: str | None
    message: str


__all__ = [
    "CreateExtractedIssuesRequestSchema",
    "CreateExtractedIssuesResponse",
    "CreatedIssueData",
    "ExtractIssuesRequest",
    "ExtractIssuesResponse",
    "ExtractedIssueInputSchema",
    "ExtractedIssueResponse",
]
