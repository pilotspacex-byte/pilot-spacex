"""MemoryEntry, ConstitutionRule, and MemoryDLQ SQLAlchemy models.

Persistent storage for the AI memory engine.
Feature 015: AI Workforce Platform — Memory Engine (Sprint 2 Phase 2a)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from pilot_space.domain.constitution_rule import RuleSeverity
from pilot_space.domain.memory_entry import MemorySourceType
from pilot_space.infrastructure.database.base import BaseModel, WorkspaceScopedModel
from pilot_space.infrastructure.database.types import JSONBCompat


def _make_vector_type() -> Any:
    """Return pgvector Vector(768) or Text fallback for SQLite test environments."""
    try:
        from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]

        return Vector(768)
    except ImportError:
        return Text()


_VECTOR_TYPE: Any = _make_vector_type()


class MemoryEntry(WorkspaceScopedModel):
    """SQLAlchemy model for workspace memory entries.

    Stores content with optional vector embedding and tsvector keywords.
    RLS enforced via workspace_id.
    """

    __tablename__ = "memory_entries"  # type: ignore[assignment]

    # Override workspace_id: composite index covers it
    workspace_id: Mapped[uuid.UUID] = mapped_column(  # type: ignore[assignment]
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=False,
    )

    content: Mapped[str] = mapped_column(Text, nullable=False)

    # embedding: vector(768) at DB level; Text fallback for SQLite tests
    # Stored as list[float] in domain; serialized as text in SQLite
    embedding: Mapped[str | None] = mapped_column(
        _VECTOR_TYPE,
        nullable=True,
    )

    # keywords stored as tsvector at DB level; Text in SQLite
    keywords: Mapped[str | None] = mapped_column(Text, nullable=True)

    source_type: Mapped[MemorySourceType] = mapped_column(
        SQLEnum(
            MemorySourceType,
            name="memory_source_type_enum",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )

    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    pinned: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        Index("ix_memory_entries_source_type", "source_type"),
        Index("ix_memory_entries_pinned", "workspace_id", "pinned"),
        Index("ix_memory_entries_expires_at", "expires_at"),
    )

    def __repr__(self) -> str:
        return f"<MemoryEntry(id={self.id}, source_type={self.source_type}, pinned={self.pinned})>"


class ConstitutionRule(WorkspaceScopedModel):
    """SQLAlchemy model for workspace AI behavior rules.

    Versioned rules following RFC 2119 severity levels.
    RLS enforced via workspace_id.
    """

    __tablename__ = "constitution_rules"  # type: ignore[assignment]

    workspace_id: Mapped[uuid.UUID] = mapped_column(  # type: ignore[assignment]
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=False,
    )

    content: Mapped[str] = mapped_column(Text, nullable=False)

    severity: Mapped[RuleSeverity] = mapped_column(
        SQLEnum(
            RuleSeverity,
            name="constitution_severity_enum",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )

    source_block_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    __table_args__ = (
        Index("ix_constitution_rules_workspace_version", "workspace_id", "version"),
        Index("ix_constitution_rules_workspace_active", "workspace_id", "active"),
    )

    def __repr__(self) -> str:
        return (
            f"<ConstitutionRule(id={self.id}, severity={self.severity}, "
            f"version={self.version}, active={self.active})>"
        )


class MemoryDLQ(BaseModel):
    """SQLAlchemy model for memory dead-letter queue.

    Records failed memory engine payloads for retry.
    No RLS — accessed by service workers only.
    """

    __tablename__ = "memory_dlq"  # type: ignore[assignment]

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONBCompat,
        nullable=False,
    )

    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        Index("ix_memory_dlq_workspace_id", "workspace_id"),
        Index("ix_memory_dlq_next_retry_at", "next_retry_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<MemoryDLQ(id={self.id}, workspace_id={self.workspace_id}, attempts={self.attempts})>"
        )
