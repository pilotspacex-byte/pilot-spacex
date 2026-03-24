"""ArtifactAnnotation SQLAlchemy model.

Tracks per-slide annotations on PPTX artifacts. Each annotation is scoped to
a specific artifact + slide_index combination.

Feature: v1.2 — PPTX Annotations
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from pilot_space.infrastructure.database.base import WorkspaceScopedModel


class ArtifactAnnotation(WorkspaceScopedModel):
    """Per-slide annotation on a PPTX artifact.

    Inherits id (UUID PK), workspace_id (FK + index), is_deleted, deleted_at,
    created_at, updated_at from WorkspaceScopedModel.

    Attributes:
        artifact_id: Artifact this annotation belongs to.
        slide_index: Zero-based index of the slide being annotated.
        content: Text content of the annotation (max 5000 chars enforced at schema layer).
        user_id: User who created the annotation.
    """

    __tablename__ = "artifact_annotations"  # type: ignore[assignment]
    __table_args__ = (
        Index("ix_artifact_annotations_artifact_slide", "artifact_id", "slide_index"),
    )

    artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artifacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    slide_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<ArtifactAnnotation(id={self.id}, artifact_id={self.artifact_id}, slide_index={self.slide_index})>"


__all__ = ["ArtifactAnnotation"]
