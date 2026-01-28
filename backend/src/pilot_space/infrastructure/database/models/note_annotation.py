"""NoteAnnotation SQLAlchemy model.

NoteAnnotation represents AI suggestions and insights displayed in the right margin.
Each annotation is linked to a specific block within a Note.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import WorkspaceScopedModel
from pilot_space.infrastructure.database.types import JSONBCompat

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.note import Note


class AnnotationType(str, Enum):
    """Type of AI annotation.

    Different types affect rendering and user interaction:
    - suggestion: AI suggestion for improvement
    - warning: Potential issue or concern
    - question: Clarification needed
    - insight: Additional context
    - reference: Related content link
    - issue_candidate: Content that could become an Issue
    - info: Informational note from AI
    """

    SUGGESTION = "suggestion"
    WARNING = "warning"
    QUESTION = "question"
    INSIGHT = "insight"
    REFERENCE = "reference"
    ISSUE_CANDIDATE = "issue_candidate"
    INFO = "info"


class AnnotationStatus(str, Enum):
    """Status of annotation processing.

    User can accept, reject, or dismiss annotations:
    - pending: Not yet processed by user
    - accepted: User accepted the suggestion
    - rejected: User rejected the suggestion
    - dismissed: User dismissed without action
    """

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    DISMISSED = "dismissed"


class NoteAnnotation(WorkspaceScopedModel):
    """NoteAnnotation model for AI suggestions in right margin.

    Annotations are AI-generated insights linked to specific blocks in a Note.
    They support the Note-First workflow by identifying patterns and opportunities.

    Attributes:
        note_id: FK to parent Note.
        block_id: TipTap block ID this annotation refers to.
        type: Type of annotation (suggestion/warning/issue_candidate/info).
        content: The annotation text content.
        confidence: AI confidence score (0.0 to 1.0).
        status: Current status (pending/accepted/rejected/dismissed).
        ai_metadata: JSONB for additional AI context (model, reasoning, etc.).
    """

    __tablename__ = "note_annotations"  # type: ignore[assignment]

    # Parent note reference
    note_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notes.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Block reference (TipTap node ID)
    block_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # Annotation type and content
    type: Mapped[AnnotationType] = mapped_column(
        SQLEnum(
            AnnotationType,
            name="annotation_type",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=AnnotationType.SUGGESTION,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # AI confidence (0.0 to 1.0)
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.5,
        server_default=text("0.5"),
    )

    # Status tracking
    status: Mapped[AnnotationStatus] = mapped_column(
        SQLEnum(
            AnnotationStatus,
            name="annotation_status",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=AnnotationStatus.PENDING,
    )

    # AI metadata (model used, reasoning chain, context used, etc.)
    ai_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONBCompat,
        nullable=True,
        default=dict,
    )

    # Relationships
    note: Mapped[Note] = relationship(
        "Note",
        back_populates="annotations",
        lazy="joined",
    )

    # Indexes and constraints
    __table_args__ = (
        Index("ix_note_annotations_note_id", "note_id"),
        Index("ix_note_annotations_block_id", "block_id"),
        Index("ix_note_annotations_type", "type"),
        Index("ix_note_annotations_status", "status"),
        Index("ix_note_annotations_confidence", "confidence"),
        Index("ix_note_annotations_is_deleted", "is_deleted"),
        Index("ix_note_annotations_note_block", "note_id", "block_id"),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<NoteAnnotation(id={self.id}, type={self.type}, "
            f"status={self.status}, confidence={self.confidence:.2f})>"
        )

    @property
    def is_pending(self) -> bool:
        """Check if annotation is pending user action."""
        return self.status == AnnotationStatus.PENDING

    @property
    def is_high_confidence(self) -> bool:
        """Check if annotation has high confidence (>= 0.8)."""
        return self.confidence >= 0.8
