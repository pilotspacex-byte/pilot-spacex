"""ThreadedDiscussion SQLAlchemy model.

ThreadedDiscussion enables collaborative discussions on Notes.
Each discussion can be attached to a specific block or the entire note.
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
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import WorkspaceScopedModel

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.discussion_comment import (
        DiscussionComment,
    )
    from pilot_space.infrastructure.database.models.note import Note
    from pilot_space.infrastructure.database.models.user import User


class DiscussionStatus(str, Enum):
    """Status of a threaded discussion.

    Discussions can be open for new comments or resolved.
    """

    OPEN = "open"
    RESOLVED = "resolved"


class ThreadedDiscussion(WorkspaceScopedModel):
    """ThreadedDiscussion model for collaborative discussions on Notes.

    Discussions allow team members to have conversations about specific
    parts of a Note or the entire document.

    Attributes:
        note_id: FK to parent Note.
        block_id: Optional TipTap block ID this discussion refers to.
        title: Optional title for the discussion thread.
        status: Current status (open/resolved).
        resolved_by_id: Optional FK to User who resolved the discussion.
        comments: Child comments in this thread.
    """

    __tablename__ = "threaded_discussions"  # type: ignore[assignment]

    # Parent note reference (nullable for issue/discussion targets)
    note_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notes.id", ondelete="CASCADE"),
        nullable=True,
    )

    # Block reference (optional - can be for entire note)
    block_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # Discussion metadata
    title: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    status: Mapped[DiscussionStatus] = mapped_column(
        SQLEnum(DiscussionStatus, name="discussion_status", create_type=False),
        nullable=False,
        default=DiscussionStatus.OPEN,
    )

    # Generic target reference (AD-001: support issue/note discussions)
    target_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="note",
        server_default="note",
    )
    target_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    # Resolution tracking
    resolved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    note: Mapped[Note | None] = relationship(
        "Note",
        back_populates="discussions",
        lazy="joined",
    )
    resolved_by: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[resolved_by_id],
        lazy="joined",
    )
    comments: Mapped[list[DiscussionComment]] = relationship(
        "DiscussionComment",
        back_populates="discussion",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="DiscussionComment.created_at",
    )

    # Indexes and constraints
    __table_args__ = (
        Index("ix_threaded_discussions_note_id", "note_id"),
        Index("ix_threaded_discussions_block_id", "block_id"),
        Index("ix_threaded_discussions_status", "status"),
        Index("ix_threaded_discussions_resolved_by_id", "resolved_by_id"),
        Index("ix_threaded_discussions_is_deleted", "is_deleted"),
        Index("ix_threaded_discussions_note_block", "note_id", "block_id"),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        title_preview = self.title[:30] if self.title else "Untitled"
        return f"<ThreadedDiscussion(id={self.id}, title={title_preview}..., status={self.status})>"

    @property
    def is_open(self) -> bool:
        """Check if discussion is open for new comments."""
        return self.status == DiscussionStatus.OPEN

    @property
    def is_resolved(self) -> bool:
        """Check if discussion has been resolved."""
        return self.status == DiscussionStatus.RESOLVED

    @property
    def comment_count(self) -> int:
        """Get count of comments in this discussion."""
        return len(self.comments) if self.comments else 0
