"""Note API schemas.

Request and response schemas for note endpoints.
Includes TipTap JSON content validation.

T092: Note schemas.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator

from pilot_space.api.v1.schemas.base import BaseSchema, EntitySchema, PaginatedResponse
from pilot_space.api.v1.schemas.issue import IssueBriefResponse


class NoteBlockSchema(BaseSchema):
    """Schema for a note content block.

    Represents a block in TipTap document structure.
    """

    id: str = Field(description="Block identifier")
    type: str = Field(description="Block type (paragraph, heading, etc.)")
    content: str = Field(default="", description="Text content of the block")
    attrs: dict[str, Any] | None = Field(default=None, description="Block attributes")


class TipTapContentSchema(BaseSchema):
    """Schema for TipTap JSON document structure.

    Validates the structure of TipTap/ProseMirror content.
    """

    type: str = Field(default="doc", description="Root node type")
    content: list[dict[str, Any]] = Field(  # pyright: ignore[reportUnknownVariableType]
        default_factory=list,
        description="Document content blocks",
    )

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate root type is 'doc'."""
        if v != "doc":
            raise ValueError("Root type must be 'doc'")
        return v


class NoteCreate(BaseSchema):
    """Schema for creating a new note.

    Attributes:
        project_id: Project to create note in.
        title: Note title.
        content: TipTap JSON content.
        is_pinned: Whether note is pinned.
    """

    project_id: UUID | None = Field(default=None, description="Project ID for the note (optional)")
    title: str = Field(
        min_length=1,
        max_length=255,
        description="Note title",
    )
    content: TipTapContentSchema | None = Field(
        default=None,
        description="TipTap JSON content",
    )
    is_pinned: bool = Field(
        default=False,
        description="Whether the note is pinned",
    )


class NoteUpdate(BaseSchema):
    """Schema for updating a note.

    All fields are optional for partial updates.
    """

    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Note title",
    )
    content: TipTapContentSchema | None = Field(
        default=None,
        description="TipTap JSON content",
    )
    is_pinned: bool | None = Field(
        default=None,
        description="Whether the note is pinned",
    )


class NotePinUpdate(BaseSchema):
    """Schema for pinning/unpinning a note."""

    is_pinned: bool = Field(description="Pin status")


class NoteResponse(EntitySchema):
    """Schema for note response.

    Includes basic note information without full content.
    """

    workspace_id: UUID = Field(description="Workspace ID the note belongs to")
    project_id: UUID | None = Field(default=None, description="Project ID (optional)")
    title: str = Field(description="Note title")
    is_pinned: bool = Field(description="Pin status")
    word_count: int = Field(default=0, description="Approximate word count")
    last_edited_by_id: UUID | None = Field(
        default=None,
        description="Last editor user ID",
    )


class NoteDetailResponse(NoteResponse):
    """Schema for detailed note response.

    Includes full content and metadata.
    """

    content: TipTapContentSchema | None = Field(
        default=None,
        description="Full TipTap JSON content",
    )
    annotation_count: int = Field(
        default=0,
        description="Number of pending annotations",
    )
    discussion_count: int = Field(
        default=0,
        description="Number of discussions",
    )
    linked_issues: list[IssueBriefResponse] = Field(
        default_factory=list,
        description="Issues linked to this note",
    )


class NoteListResponse(PaginatedResponse[NoteResponse]):
    """Paginated list of notes."""


class NoteSummary(BaseSchema):
    """Lightweight note summary for lists and references."""

    id: UUID = Field(description="Note ID")
    title: str = Field(description="Note title")
    is_pinned: bool = Field(description="Pin status")
    updated_at: datetime = Field(description="Last update timestamp")


class NoteSearchResult(BaseSchema):
    """Search result for notes."""

    note: NoteSummary = Field(description="Note summary")
    highlight: str | None = Field(
        default=None,
        description="Highlighted matching text",
    )
    score: float = Field(
        default=0.0,
        description="Search relevance score",
    )


class NoteSearchResponse(BaseSchema):
    """Search results for notes."""

    results: list[NoteSearchResult] = Field(description="Search results")
    total: int = Field(description="Total matching results")
    query: str = Field(description="Search query")


# Export for TipTap content extraction
def extract_blocks_from_tiptap(
    content: TipTapContentSchema | dict[str, Any] | None,
) -> list[dict[str, str]]:
    """Extract text blocks from TipTap content.

    Args:
        content: TipTap JSON content.

    Returns:
        List of blocks with 'id' and 'content' keys.
    """
    if not content:
        return []

    if isinstance(content, TipTapContentSchema):
        raw_content = content.content
    else:
        raw_content = content.get("content", [])

    blocks: list[dict[str, str]] = []

    def extract_text(node: dict[str, Any]) -> str:
        """Recursively extract text from node."""
        if node.get("type") == "text":
            return node.get("text", "")

        return "".join(extract_text(child) for child in node.get("content", []))

    for i, node in enumerate(raw_content):
        # Generate block ID if not present
        block_id = node.get("attrs", {}).get("id", f"block-{i}")
        text = extract_text(node)

        if text.strip():  # Only include non-empty blocks
            blocks.append(
                {
                    "id": block_id,
                    "content": text,
                }
            )

    return blocks


def extract_text_from_tiptap(
    content: TipTapContentSchema | dict[str, Any] | None,
) -> str:
    """Extract plain text from TipTap content.

    Args:
        content: TipTap JSON content.

    Returns:
        Plain text representation.
    """
    blocks = extract_blocks_from_tiptap(content)
    return "\n\n".join(block["content"] for block in blocks)


# ============================================================
# AI Update Schemas
# ============================================================


class AIUpdateRequest(BaseSchema):
    """Schema for AI-initiated note content update.

    Separate endpoint from user autosave for audit trails and conflict detection.
    """

    operation: str = Field(
        description="Update operation type: replace_block, append_blocks, or insert_inline_issue"
    )
    block_id: str | None = Field(
        default=None,
        description="Target block ID (required for replace_block and insert_inline_issue)",
    )
    content: dict[str, Any] | None = Field(  # pyright: ignore[reportUnknownVariableType]
        default=None,
        description="New content for the block or blocks",
    )
    after_block_id: str | None = Field(
        default=None,
        description="Insert position for append_blocks operation",
    )
    issue_data: dict[str, Any] | None = Field(  # pyright: ignore[reportUnknownVariableType]
        default=None,
        description="Issue node data for insert_inline_issue operation",
    )
    agent_session_id: str | None = Field(
        default=None,
        description="Agent session ID for audit trail",
    )
    source_tool: str | None = Field(
        default=None,
        description="MCP tool that triggered this update",
    )


class AIUpdateResponse(BaseSchema):
    """Schema for AI update response."""

    success: bool = Field(description="Whether the update succeeded")
    note_id: str = Field(description="The updated note ID")
    affected_block_ids: list[str] = Field(description="List of block IDs that were modified")
    conflict: bool = Field(
        default=False,
        description="Whether a conflict was detected",
    )


__all__ = [
    "AIUpdateRequest",
    "AIUpdateResponse",
    "NoteBlockSchema",
    "NoteCreate",
    "NoteDetailResponse",
    "NoteListResponse",
    "NotePinUpdate",
    "NoteResponse",
    "NoteSearchResponse",
    "NoteSearchResult",
    "NoteSummary",
    "NoteUpdate",
    "TipTapContentSchema",
    "extract_blocks_from_tiptap",
    "extract_text_from_tiptap",
]
