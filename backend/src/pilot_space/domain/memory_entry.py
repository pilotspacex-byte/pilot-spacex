"""MemoryEntry domain entity.

Represents a piece of AI memory stored for a workspace.
Supports vector embedding for semantic search and tsvector for full-text search.

Feature 015: AI Workforce Platform — Memory Engine
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID


class MemorySourceType(StrEnum):
    """Source of a memory entry."""

    INTENT = "intent"
    SKILL_OUTCOME = "skill_outcome"
    USER_FEEDBACK = "user_feedback"
    CONSTITUTION = "constitution"


@dataclass
class MemoryEntry:
    """Domain entity for a workspace memory entry.

    Stores content with optional vector embedding for semantic search
    and keyword list for full-text search.

    Attributes:
        workspace_id: Owning workspace.
        content: Raw text content of the memory.
        source_type: What generated this memory.
        id: Unique identifier (None for unsaved entities).
        embedding: Optional 768-dim vector (filled async by worker).
        keywords: Optional keyword list extracted from content.
        source_id: Optional reference to originating entity.
        pinned: Pinned memories survive TTL expiry.
        created_at: Creation timestamp.
        expires_at: Optional expiry timestamp (None = never expires).
    """

    workspace_id: UUID
    content: str
    source_type: MemorySourceType
    id: UUID | None = None
    embedding: list[float] | None = None
    keywords: list[str] | None = None
    source_id: UUID | None = None
    pinned: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    expires_at: datetime | None = None

    def __post_init__(self) -> None:
        """Extract keywords from content if not provided."""
        if self.keywords is None:
            self.keywords = self._extract_keywords(self.content)

    def pin(self) -> None:
        """Pin this memory so it survives TTL expiry."""
        self.pinned = True

    def unpin(self) -> None:
        """Unpin this memory, allowing normal TTL expiry."""
        self.pinned = False

    @property
    def is_expired(self) -> bool:
        """Check if this memory has passed its expiry time.

        Pinned memories never expire regardless of expires_at.

        Returns:
            True if expired and not pinned.
        """
        if self.pinned:
            return False
        if self.expires_at is None:
            return False
        return datetime.now(tz=UTC) > self.expires_at

    @staticmethod
    def _extract_keywords(content: str) -> list[str]:
        """Extract unique lowercase keywords from content.

        Simple extraction: split on whitespace, lowercase, dedupe.

        Args:
            content: Raw text content.

        Returns:
            Sorted list of unique lowercase words.
        """
        words = content.lower().split()
        return sorted(set(words))


__all__ = ["MemoryEntry", "MemorySourceType"]
