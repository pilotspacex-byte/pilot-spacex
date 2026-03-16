"""NoteVersion SQLAlchemy model for point-in-time note snapshots.

Stores full TipTap JSON content at each snapshot with metadata for
trigger type, pinning, AI digest, and optimistic locking.

Feature 017: Note Versioning + PM Blocks — Sprint 1 (T-201, T-203)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import BaseModel
from pilot_space.infrastructure.database.types import JSONBCompat

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.note import Note
    from pilot_space.infrastructure.database.models.user import User


class VersionTrigger(StrEnum):
    """Trigger source for a note version snapshot."""

    AUTO = "auto"
    MANUAL = "manual"
    AI_BEFORE = "ai_before"
    AI_AFTER = "ai_after"


class NoteVersion(BaseModel):
    """SQLAlchemy model for note version snapshots.

    Each record is a full-content snapshot of a Note at a point in time.
    Content is immutable after creation. Inherits BaseModel for UUID PK
    and repository compatibility (is_deleted/updated_at fields present but
    unused — versions are append-only by design).

    Attributes:
        id: UUID primary key (from BaseModel).
        note_id: FK to notes table (cascade delete).
        workspace_id: FK to workspaces (RLS enforcement).
        trigger: Enum for what initiated this snapshot.
        content: Full TipTap JSON document.
        label: Optional human-readable label (max 100 chars).
        pinned: If true, exempt from retention cleanup.
        digest: Cached AI-generated change summary.
        digest_cached_at: Timestamp when digest was cached.
        created_by: FK to users (nullable — NULL for auto snapshots).
        version_number: Monotonically increasing per note (optimistic lock, C-9).
        created_at: Snapshot creation timestamp (from BaseModel).
    """

    __tablename__ = "note_versions"  # type: ignore[assignment]

    # Note FK (cascade delete when note deleted)
    note_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notes.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Workspace FK (direct RLS enforcement, not via join)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Trigger source
    trigger: Mapped[VersionTrigger] = mapped_column(
        SQLEnum(
            VersionTrigger,
            name="note_version_trigger_enum",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )

    # Immutable full TipTap JSON snapshot
    content: Mapped[dict[str, Any]] = mapped_column(
        JSONBCompat,
        nullable=False,
    )

    # Optional human-readable label
    label: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # Pinned — exempt from retention cleanup
    pinned: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
        default=False,
    )

    # AI digest cache
    digest: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    digest_cached_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Creator (NULL for auto-triggered snapshots)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Optimistic locking token (C-9): monotonically increasing per note
    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )

    # Relationships
    note: Mapped[Note] = relationship(
        "Note",
        lazy="joined",
        foreign_keys=[note_id],
    )
    creator: Mapped[User | None] = relationship(
        "User",
        lazy="joined",
        foreign_keys=[created_by],
    )

    # Indexes matching migration 042
    __table_args__ = (
        Index("ix_note_versions_note_created", "note_id", "created_at"),
        Index("ix_note_versions_workspace_id", "workspace_id"),
        Index("ix_note_versions_trigger", "note_id", "trigger"),
        Index("ix_note_versions_pinned", "note_id", "pinned"),
        Index("ix_note_versions_created_by", "created_by"),
    )

    def __repr__(self) -> str:
        return (
            f"<NoteVersion(id={self.id}, note_id={self.note_id}, "
            f"trigger={self.trigger}, v{self.version_number})>"
        )
