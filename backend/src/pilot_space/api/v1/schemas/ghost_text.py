"""Pydantic schemas for ghost text endpoints.

Covers GhostTextRequest (from both notes_ai.py and ghost_text.py) and
GhostTextResponse. The notes_ai GhostTextRequest is a simpler streaming
variant; the ghost_text GhostTextRequest is the full completion variant
with rate limiting.

Reference: T082-T083 (GhostText Endpoint + Rate Limiting), T113 (SSE endpoint)
Design Decisions: DD-011 (Haiku for latency)
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class GhostTextStreamRequest(BaseModel):
    """Request schema for SSE ghost text streaming (notes_ai endpoint).

    Attributes:
        context: Text content before cursor.
        cursor_position: Cursor position in document.
    """

    context: str = Field(
        ...,
        description="Text content before cursor for context",
        min_length=1,
        max_length=10000,
    )
    cursor_position: int = Field(
        ...,
        description="Cursor position in document",
        ge=0,
    )


class GhostTextRequest(BaseModel):
    """GhostText completion request (rate-limited endpoint).

    Attributes:
        context: Context text (previous paragraphs, max 500 chars).
        prefix: Prefix to complete (current line, max 200 chars).
        workspace_id: Workspace UUID for context and caching.
        block_type: TipTap block type for prompt routing (paragraph, codeBlock,
            heading, bulletList). Defaults to paragraph behavior when omitted.
        note_title: Title of the note being edited (optional context).
        linked_issues: Linked issue identifiers for context (optional).
    """

    context: str = Field(..., max_length=500, description="Context text")
    prefix: str = Field(..., max_length=200, description="Prefix to complete")
    workspace_id: UUID = Field(..., description="Workspace ID")
    block_type: Literal["paragraph", "codeBlock", "heading", "bulletList"] | None = Field(
        None, description="TipTap block type for prompt routing"
    )
    note_title: str | None = Field(None, max_length=200, description="Note title for context")
    linked_issues: list[str] | None = Field(
        None, max_length=20, description="Linked issue identifiers"
    )


class GhostTextResponse(BaseModel):
    """GhostText completion response.

    Attributes:
        suggestion: Completion suggestion text.
        confidence: Confidence score (0.0-1.0).
        cached: Whether result was cached.
    """

    suggestion: str = Field(..., description="Completion suggestion")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    cached: bool = Field(False, description="Whether cached")


__all__ = ["GhostTextRequest", "GhostTextResponse", "GhostTextStreamRequest"]
