"""NoteVersion API schemas.

Request and response schemas for the note versioning endpoints.

Feature 017: Note Versioning — Sprint 1 (T-214)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from pilot_space.api.v1.schemas.base import BaseSchema


class VersionTriggerSchema(str):
    """String type for trigger enum values."""


class NoteVersionResponse(BaseSchema):
    """Response schema for a single note version."""

    id: UUID = Field(description="Version UUID")
    note_id: UUID = Field(description="Parent note UUID")
    workspace_id: UUID = Field(description="Workspace UUID")
    trigger: str = Field(description="Snapshot trigger: auto|manual|ai_before|ai_after")
    label: str | None = Field(default=None, description="Human-readable label")
    pinned: bool = Field(description="Whether version is pinned (exempt from retention)")
    digest: str | None = Field(default=None, description="Cached AI change summary")
    digest_cached_at: datetime | None = Field(default=None, description="When digest was cached")
    created_by: UUID | None = Field(default=None, description="Creator UUID (null for auto)")
    version_number: int = Field(description="Monotonically increasing per-note counter (C-9)")
    created_at: datetime = Field(description="Snapshot creation timestamp")
    # GAP-02: expose ai_before/ai_after pairing for trust UI.
    # Non-null only when trigger == "ai_after", points to the paired ai_before snapshot.
    ai_before_version_id: UUID | None = Field(
        default=None,
        description="Paired ai_before version UUID (populated only when trigger=ai_after)",
    )


class NoteVersionListResponse(BaseSchema):
    """Paginated list of note versions."""

    versions: list[NoteVersionResponse] = Field(description="Version list, newest first")
    total: int = Field(description="Total version count for this note")
    note_id: UUID = Field(description="Parent note UUID")


class CreateVersionRequest(BaseSchema):
    """Request to manually create a version snapshot."""

    label: str | None = Field(
        default=None,
        max_length=100,
        description="Optional label for this snapshot",
    )


class RestoreVersionRequest(BaseSchema):
    """Request to restore a note to a historical version (C-9).

    version_number is the optimistic lock token. It must match the current
    max version_number. If it doesn't, the server returns 409 Conflict.
    """

    version_number: int = Field(
        ge=1,
        description="Optimistic lock token (C-9): must match current max version_number",
    )


class PinVersionRequest(BaseSchema):
    """Request to pin or unpin a version."""

    pinned: bool = Field(description="True to pin, False to unpin")


class BlockDiffResponse(BaseSchema):
    """Diff result for a single TipTap block."""

    block_id: str = Field(description="Block identifier")
    diff_type: str = Field(description="added|removed|modified|unchanged")
    old_content: dict[str, Any] | None = Field(default=None, description="Block before change")
    new_content: dict[str, Any] | None = Field(default=None, description="Block after change")


class DiffResponse(BaseSchema):
    """Block-level diff between two note versions."""

    version1_id: UUID = Field(description="Older version UUID")
    version2_id: UUID = Field(description="Newer version UUID")
    blocks: list[BlockDiffResponse] = Field(description="Per-block diff results")
    added_count: int = Field(description="Number of added blocks")
    removed_count: int = Field(description="Number of removed blocks")
    modified_count: int = Field(description="Number of modified blocks")
    has_changes: bool = Field(description="Whether any blocks changed")


class DigestResponse(BaseSchema):
    """AI change digest for a version."""

    version_id: UUID = Field(description="Version UUID")
    digest: str = Field(description="AI-generated change summary")
    from_cache: bool = Field(description="Whether digest was served from cache")


class EntityReferenceResponse(BaseSchema):
    """A detected entity reference in version content."""

    reference_type: str = Field(description="issue|note|unknown")
    identifier: str = Field(description="Issue identifier (PS-42) or UUID")
    raw_text: str = Field(description="Raw matched text in content")


class ImpactResponse(BaseSchema):
    """Impact analysis result for a version."""

    version_id: UUID = Field(description="Version UUID")
    references: list[EntityReferenceResponse] = Field(description="All detected references")
    issue_count: int = Field(description="Number of issue references")
    note_count: int = Field(description="Number of note references")


class RestoreResponse(BaseSchema):
    """Result of a successful restore operation."""

    new_version: NoteVersionResponse = Field(description="Newly created restore snapshot")
    restored_from_version_id: UUID = Field(description="Source version ID")


class UndoAiRequest(BaseSchema):
    """Request for the Undo AI Changes fast path (GAP-04).

    version_number is the optimistic lock token (C-9). Must match the current
    max version_number. Returns 409 if a concurrent write has occurred.
    """

    version_number: int = Field(
        ge=1,
        description="Optimistic lock token (C-9): current max version_number",
    )


class UndoAiResponse(BaseSchema):
    """Result of the Undo AI Changes fast path."""

    new_version: NoteVersionResponse = Field(description="Newly created restore snapshot")
    restored_from_version_id: UUID = Field(description="The ai_before version that was restored")
