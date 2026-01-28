"""NoteIssueLink SQLAlchemy model.

NoteIssueLink tracks relationships between Notes and Issues.
Supports the Note-First workflow where issues emerge from notes.
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
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import WorkspaceScopedModel

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.issue import Issue
    from pilot_space.infrastructure.database.models.note import Note


class NoteLinkType(str, Enum):
    """Type of link between Note and Issue.

    Different link types represent different relationships:
    - extracted: Issue was extracted from this Note
    - referenced: Note references this Issue
    - related: General relationship between Note and Issue
    - inline: Issue is visually embedded inline within the note content
    """

    EXTRACTED = "extracted"
    REFERENCED = "referenced"
    RELATED = "related"
    INLINE = "inline"


class NoteIssueLink(WorkspaceScopedModel):
    """NoteIssueLink model for Note-Issue relationships.

    Links track how Notes and Issues are connected, supporting
    traceability in the Note-First workflow.

    Attributes:
        note_id: FK to Note.
        issue_id: FK to Issue.
        link_type: Type of relationship (extracted/referenced/related/inline).
        block_id: Optional TipTap block ID where the link originates.
    """

    __tablename__ = "note_issue_links"  # type: ignore[assignment]

    # Note reference
    note_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notes.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Issue reference
    issue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("issues.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Link type
    link_type: Mapped[NoteLinkType] = mapped_column(
        SQLEnum(
            NoteLinkType,
            name="note_link_type",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=NoteLinkType.RELATED,
    )

    # Block reference (optional - where in the note the link originates)
    block_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # Relationships
    note: Mapped[Note] = relationship(
        "Note",
        back_populates="issue_links",
        lazy="joined",
    )
    issue: Mapped[Issue] = relationship(
        "Issue",
        back_populates="note_links",
        lazy="joined",
    )

    # Indexes and constraints
    __table_args__ = (
        Index("ix_note_issue_links_note_id", "note_id"),
        Index("ix_note_issue_links_issue_id", "issue_id"),
        Index("ix_note_issue_links_link_type", "link_type"),
        Index("ix_note_issue_links_is_deleted", "is_deleted"),
        # Unique constraint: one link type per note-issue pair
        UniqueConstraint(
            "note_id",
            "issue_id",
            "link_type",
            name="uq_note_issue_links_note_issue_type",
        ),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<NoteIssueLink(id={self.id}, note_id={self.note_id}, "
            f"issue_id={self.issue_id}, type={self.link_type})>"
        )
