"""NoteNoteLink SQLAlchemy model.

NoteNoteLink tracks relationships between Notes (note-to-note linking).
Supports wiki-style [[links]] and /link-note block embeds.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Enum as SQLEnum,
    ForeignKey,
    Index,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import WorkspaceScopedModel

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.note import Note


class NoteNoteLinkType(str, Enum):
    """Type of link between two Notes.

    - inline: Wiki-style [[link]] within text content
    - embed: Block-level embed via /link-note slash command
    """

    INLINE = "inline"
    EMBED = "embed"


class NoteNoteLink(WorkspaceScopedModel):
    """NoteNoteLink model for Note-to-Note relationships.

    Tracks how notes reference each other, supporting wiki-style
    inline links and block embeds.

    Attributes:
        source_note_id: FK to the note containing the link.
        target_note_id: FK to the note being linked to.
        link_type: Type of link (inline/embed).
        block_id: Optional TipTap block ID where the link originates.
    """

    __tablename__ = "note_note_links"  # type: ignore[assignment]

    # Source note (the note containing the link)
    source_note_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notes.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Target note (the note being linked to)
    target_note_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notes.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Link type
    link_type: Mapped[NoteNoteLinkType] = mapped_column(
        SQLEnum(
            NoteNoteLinkType,
            name="note_note_link_type",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=NoteNoteLinkType.INLINE,
    )

    # Block reference (optional - where in the source note the link originates)
    block_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # Relationships
    source_note: Mapped[Note] = relationship(
        "Note",
        foreign_keys=[source_note_id],
        back_populates="outgoing_note_links",
        lazy="joined",
    )
    target_note: Mapped[Note] = relationship(
        "Note",
        foreign_keys=[target_note_id],
        back_populates="incoming_note_links",
        lazy="selectin",
    )

    # Indexes and constraints
    __table_args__ = (
        Index("ix_note_note_links_source_note_id", "source_note_id"),
        Index("ix_note_note_links_target_note_id", "target_note_id"),
        Index("ix_note_note_links_link_type", "link_type"),
        Index("ix_note_note_links_is_deleted", "is_deleted"),
        # R-7: Unique per block, NOT per link_type.
        # Allows multiple [[links]] to the same target from different blocks.
        # block_id=NULL means "unanchored" — at most one unanchored link per pair.
        # Partial index: only enforce uniqueness on non-deleted rows so soft-deleted
        # links do not block re-creation of the same source/target/block combination.
        Index(
            "uq_note_note_links_source_target_block",
            "source_note_id",
            "target_note_id",
            "block_id",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<NoteNoteLink(id={self.id}, source={self.source_note_id}, "
            f"target={self.target_note_id}, type={self.link_type})>"
        )
