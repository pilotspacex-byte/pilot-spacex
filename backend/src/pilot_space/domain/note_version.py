"""NoteVersion domain entity.

Represents a point-in-time snapshot of a Note's TipTap content.
Snapshots are immutable after creation — content is never modified.

Feature 017: Note Versioning + PM Blocks — Sprint 1 (T-203)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID


class VersionTrigger(StrEnum):
    """What initiated this version snapshot."""

    AUTO = "auto"
    MANUAL = "manual"
    AI_BEFORE = "ai_before"
    AI_AFTER = "ai_after"


_LABEL_MAX_LEN = 100


@dataclass
class NoteVersion:
    """Domain entity representing a note version snapshot.

    Snapshots are immutable — content must not be modified after creation.
    The digest field is a cached AI summary and may be lazily populated.

    Attributes:
        note_id: Note this version belongs to.
        workspace_id: Workspace for RLS enforcement.
        trigger: What initiated this snapshot.
        content: Full TipTap JSON document at snapshot time.
        id: UUID (None for unsaved entities).
        label: Human-readable label (max 100 chars).
        pinned: Pinned versions are exempt from retention cleanup.
        digest: Cached AI-generated change summary.
        digest_cached_at: When the digest was last cached.
        created_by: User who created this version (None for auto).
        version_number: Monotonically increasing per-note counter (optimistic lock token).
        created_at: Snapshot timestamp.
    """

    note_id: UUID
    workspace_id: UUID
    trigger: VersionTrigger
    content: dict[str, Any]
    id: UUID | None = None
    label: str | None = None
    pinned: bool = False
    digest: str | None = None
    digest_cached_at: datetime | None = None
    created_by: UUID | None = None
    version_number: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))

    def __post_init__(self) -> None:
        """Validate initial state."""
        self._validate_label(self.label)
        self._validate_content(self.content)
        self._validate_version_number(self.version_number)

    def pin(self) -> None:
        """Pin this version — exempt from retention cleanup."""
        self.pinned = True

    def unpin(self) -> None:
        """Unpin this version — eligible for retention cleanup."""
        self.pinned = False

    def cache_digest(self, digest: str) -> None:
        """Store an AI-generated digest for this version.

        Args:
            digest: Human-readable summary of changes in this version.
        """
        self.digest = digest
        self.digest_cached_at = datetime.now(tz=UTC)

    def invalidate_digest(self) -> None:
        """Invalidate cached digest (called when linked entities change, FR-042)."""
        self.digest = None
        self.digest_cached_at = None

    @property
    def has_digest(self) -> bool:
        """Whether a cached digest is available."""
        return self.digest is not None

    @property
    def is_ai_triggered(self) -> bool:
        """Whether this version was created by an AI operation."""
        return self.trigger in (VersionTrigger.AI_BEFORE, VersionTrigger.AI_AFTER)

    @staticmethod
    def _validate_label(label: str | None) -> None:
        """Validate label length.

        Args:
            label: Label text.

        Raises:
            ValueError: If label exceeds max length.
        """
        if label is not None and len(label) > _LABEL_MAX_LEN:
            msg = f"Version label must not exceed {_LABEL_MAX_LEN} characters, got {len(label)}"
            raise ValueError(msg)

    @staticmethod
    def _validate_content(content: dict[str, Any]) -> None:
        """Validate TipTap content is a non-empty dict.

        Args:
            content: TipTap JSON document.

        Raises:
            ValueError: If content is not a dict.
        """
        if not isinstance(content, dict):  # type: ignore[misc]
            msg = "Version content must be a dict (TipTap JSON document)"
            raise TypeError(msg)

    @staticmethod
    def _validate_version_number(version_number: int) -> None:
        """Validate version_number is positive.

        Args:
            version_number: Optimistic lock counter.

        Raises:
            ValueError: If version_number is not positive.
        """
        if version_number < 1:
            msg = f"version_number must be >= 1, got {version_number}"
            raise ValueError(msg)


__all__ = ["NoteVersion", "VersionTrigger"]
