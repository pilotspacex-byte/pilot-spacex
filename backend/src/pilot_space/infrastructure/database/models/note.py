"""Note SQLAlchemy model.

Note is the primary document entity for the Note-First workflow.
Users brainstorm with AI in collaborative documents, and issues emerge naturally.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import WorkspaceScopedModel
from pilot_space.infrastructure.database.types import JSONBCompat

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.note_annotation import (
        NoteAnnotation,
    )
    from pilot_space.infrastructure.database.models.note_issue_link import NoteIssueLink
    from pilot_space.infrastructure.database.models.project import Project
    from pilot_space.infrastructure.database.models.template import Template
    from pilot_space.infrastructure.database.models.threaded_discussion import (
        ThreadedDiscussion,
    )
    from pilot_space.infrastructure.database.models.user import User


class Note(WorkspaceScopedModel):
    """Note model for collaborative documents.

    Notes are the primary entry point for the Note-First workflow.
    They contain TipTap/ProseMirror JSON content and can have AI annotations.

    Attributes:
        title: Display title of the note.
        content: TipTap JSON document structure.
        summary: AI-generated or user-provided summary.
        word_count: Computed word count of document.
        reading_time_mins: Estimated reading time in minutes.
        is_pinned: Whether note is pinned for quick access.
        template_id: Optional FK to Template used as base.
        owner_id: FK to User who created the note.
        project_id: Optional FK to Project (notes can be project-scoped).
        annotations: AI annotations in right margin.
        discussions: Threaded discussions on the note.
    """

    __tablename__ = "notes"  # type: ignore[assignment]

    # Core fields
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    # TipTap JSON content (ProseMirror document structure)
    content: Mapped[dict[str, Any]] = mapped_column(
        JSONBCompat,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    # Metadata
    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    word_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    reading_time_mins: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    is_pinned: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    # T009: Flag to identify onboarding guided notes (FR-011)
    is_guided_template: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    # Template (optional)
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("templates.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Owner (creator of note)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Project scope (optional - notes can exist at workspace level)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
    )

    # Relationships
    template: Mapped[Template | None] = relationship(
        "Template",
        lazy="joined",
    )
    owner: Mapped[User] = relationship(
        "User",
        foreign_keys=[owner_id],
        lazy="joined",
    )
    project: Mapped[Project | None] = relationship(
        "Project",
        lazy="joined",
    )
    annotations: Mapped[list[NoteAnnotation]] = relationship(
        "NoteAnnotation",
        back_populates="note",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    discussions: Mapped[list[ThreadedDiscussion]] = relationship(
        "ThreadedDiscussion",
        back_populates="note",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    issue_links: Mapped[list[NoteIssueLink]] = relationship(
        "NoteIssueLink",
        back_populates="note",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Indexes and constraints
    __table_args__ = (
        Index("ix_notes_project_id", "project_id"),
        Index("ix_notes_workspace_project", "workspace_id", "project_id"),
        Index("ix_notes_owner_id", "owner_id"),
        Index("ix_notes_template_id", "template_id"),
        Index("ix_notes_is_pinned", "is_pinned"),
        Index("ix_notes_is_deleted", "is_deleted"),
        Index("ix_notes_is_guided_template", "is_guided_template"),
        Index("ix_notes_created_at", "created_at"),
        # Full-text search index on title
        Index(
            "ix_notes_title_text",
            text("to_tsvector('english', title)"),
            postgresql_using="gin",
        ),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<Note(id={self.id}, title={self.title[:30] if self.title else 'Untitled'}...)>"

    def calculate_reading_time(self) -> int:
        """Calculate reading time based on word count.

        Assumes average reading speed of 200 words per minute.

        Returns:
            Estimated reading time in minutes (minimum 1).
        """
        if self.word_count <= 0:
            return 0
        return max(1, self.word_count // 200)
