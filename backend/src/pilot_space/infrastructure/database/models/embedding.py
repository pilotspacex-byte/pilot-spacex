"""Embedding SQLAlchemy model.

Embedding stores vector representations of content for similarity search.
Used by DuplicateDetectorAgent and semantic search features.

T135: Create Embedding model for RAG pipeline.
"""

from __future__ import annotations

import uuid
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from pilot_space.infrastructure.database.base import WorkspaceScopedModel
from pilot_space.infrastructure.database.types import JSONBCompat


class EmbeddingType(StrEnum):
    """Types of content that can be embedded.

    Each type has different preprocessing and retrieval patterns.
    """

    ISSUE = "issue"
    NOTE = "note"
    NOTE_BLOCK = "note_block"
    COMMENT = "comment"
    CODE_SNIPPET = "code_snippet"


class Embedding(WorkspaceScopedModel):
    """Embedding model for vector similarity search.

    Stores vector embeddings of various content types for:
    - Duplicate issue detection
    - Semantic search
    - Related content recommendations
    - RAG context retrieval

    Uses pgvector extension for efficient similarity queries.

    Attributes:
        content_type: Type of content (issue, note, etc).
        content_id: UUID of the source content.
        content_hash: Hash of content for change detection.
        content_preview: First ~200 chars for display.
        embedding: Vector embedding (1536 dims for text-embedding-3-large).
        model: Model used to generate embedding.
        token_count: Number of tokens in source content.
        metadata: Additional context for retrieval.
    """

    __tablename__ = "embeddings"  # type: ignore[assignment]

    # Content identification
    content_type: Mapped[EmbeddingType] = mapped_column(
        SQLEnum(EmbeddingType, name="embedding_type", create_type=False),
        nullable=False,
    )
    content_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    # Change detection
    content_hash: Mapped[str] = mapped_column(
        String(64),  # SHA-256 hex
        nullable=False,
    )

    # Preview for display
    content_preview: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Note: embedding column uses pgvector type, created via migration
    # embedding: Mapped[list[float]] - defined in migration as vector(1536)

    # Model info
    model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="text-embedding-3-large",
    )
    dimensions: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1536,
    )
    token_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Project context for scoped searches
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
    )

    # Additional metadata (renamed to avoid conflict with SQLAlchemy's metadata)
    embedding_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",  # Column name in DB
        JSONBCompat,
        nullable=True,
        default=dict,
    )
    # metadata structure:
    # {
    #   "title": "Issue title for display",
    #   "state": "In Progress",
    #   "priority": "high",
    #   "labels": ["bug", "auth"],
    #   "last_indexed_at": "2026-01-24T10:00:00Z"
    # }

    # Indexes
    __table_args__ = (
        Index("ix_embeddings_content_type", "content_type"),
        Index("ix_embeddings_content_id", "content_id"),
        Index("ix_embeddings_content_hash", "content_hash"),
        Index("ix_embeddings_project_id", "project_id"),
        Index("ix_embeddings_is_deleted", "is_deleted"),
        # Composite for content lookup
        Index(
            "ix_embeddings_type_content",
            "content_type",
            "content_id",
        ),
        # Composite for workspace-scoped search
        Index(
            "ix_embeddings_workspace_type",
            "workspace_id",
            "content_type",
        ),
        # Note: HNSW index for vector similarity is created in migration
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<Embedding(id={self.id}, type={self.content_type.value}, "
            f"content_id={self.content_id})>"
        )

    @property
    def is_stale(self) -> bool:
        """Check if embedding might be stale (simple heuristic).

        More sophisticated staleness detection should compare
        content_hash with current content.
        """
        # Placeholder - actual staleness check happens during indexing
        return False
