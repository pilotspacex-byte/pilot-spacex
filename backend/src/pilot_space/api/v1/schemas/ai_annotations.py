"""Pydantic schemas for AI annotation endpoints.

Covers AnnotateBlocksRequest and AnnotationResponse.

T069: Margin annotations.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class AnnotateBlocksRequest(BaseModel):
    """Request for block annotation."""

    block_ids: list[str] = Field(..., min_length=1, max_length=20)
    context_blocks: int = Field(default=3, ge=1, le=10)


class AnnotationResponse(BaseModel):
    """Single annotation in response."""

    block_id: str
    type: str
    title: str
    content: str
    confidence: float
    action_label: str | None = None


__all__ = ["AnnotateBlocksRequest", "AnnotationResponse"]
