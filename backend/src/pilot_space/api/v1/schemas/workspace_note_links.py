"""Pydantic schemas for workspace note-to-note link API.

Supports wiki-style [[links]] and /link-note block embeds.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import Field

from pilot_space.api.v1.schemas.base import BaseSchema


class CreateNoteLinkRequest(BaseSchema):
    """Request body for POST /{wid}/notes/{nid}/links."""

    target_note_id: UUID = Field(description="Target note UUID to link to")
    link_type: Literal["inline", "embed"] = Field(
        default="inline",
        description="Link type: inline (wiki-style) or embed (block)",
    )
    block_id: str | None = Field(
        default=None,
        description="TipTap block ID where the link originates",
    )


class NoteLinkResponse(BaseSchema):
    """Response for a NoteNoteLink record."""

    id: UUID
    source_note_id: UUID
    target_note_id: UUID
    link_type: str
    block_id: str | None = None
    workspace_id: UUID
    target_note_title: str | None = None


class BacklinkResponse(BaseSchema):
    """Response for a backlink (incoming link)."""

    id: UUID
    source_note_id: UUID
    target_note_id: UUID
    link_type: str
    block_id: str | None = None
    workspace_id: UUID
    source_note_title: str | None = None


__all__ = [
    "BacklinkResponse",
    "CreateNoteLinkRequest",
    "NoteLinkResponse",
]
