"""Pydantic schemas for workspace notes AI API.

Provides request/response models for AI-assisted note operations,
including extracted issue creation from note content.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ExtractedIssueInput(BaseModel):
    """Single extracted issue to create."""

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    priority: str = "medium"
    type: str = "task"
    source_block_id: str | None = None


class CreateExtractedIssuesRequest(BaseModel):
    """Request to create multiple extracted issues from a note."""

    issues: list[ExtractedIssueInput] = Field(..., min_length=1, max_length=50)


class CreateExtractedIssuesResponse(BaseModel):
    """Response with created issue IDs."""

    created_issue_ids: list[str]
    count: int


__all__ = [
    "CreateExtractedIssuesRequest",
    "CreateExtractedIssuesResponse",
    "ExtractedIssueInput",
]
