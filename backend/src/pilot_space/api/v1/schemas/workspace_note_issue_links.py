"""Pydantic schemas for workspace note-issue link API.

Provides request/response models for NoteIssueLink endpoints.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import Field

from pilot_space.api.v1.schemas.base import BaseSchema


class LinkIssueRequest(BaseSchema):
    """Request body for POST /{wid}/notes/{nid}/issues."""

    issue_id: UUID = Field(description="Issue UUID to link")
    link_type: str | None = Field(
        default=None,
        description="Link type: EXTRACTED, REFERENCED, RELATED, INLINE",
    )
    block_id: str | None = Field(
        default=None,
        description="TipTap block ID where the link originates",
    )


class NoteIssueLinkResponse(BaseSchema):
    """Response for a NoteIssueLink record."""

    id: UUID
    note_id: UUID
    issue_id: UUID
    link_type: str
    block_id: str | None = None
    workspace_id: UUID


__all__ = [
    "LinkIssueRequest",
    "NoteIssueLinkResponse",
]
