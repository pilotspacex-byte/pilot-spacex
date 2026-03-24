"""ArtifactAnnotation SQLAlchemy model.

User-authored slide annotations on project artifacts (e.g. presentation slides).
Each annotation is scoped to a workspace, project artifact, and optional slide index.

Hard delete — no soft-delete lifecycle needed here (design decision:
annotation data is ephemeral, deletion is permanent).
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from pilot_space.infrastructure.database.base import WorkspaceScopedModel


class ArtifactAnnotation(WorkspaceScopedModel):
    """User annotation attached to a project artifact.

    Inherits id (UUID PK), workspace_id (FK + index), is_deleted, deleted_at,
    created_at, updated_at from WorkspaceScopedModel.

    Note: is_deleted / deleted_at columns are inherited but unused — this
    model uses hard delete. The BaseRepository.delete(hard=True) call in the
    repository ensures permanent removal.

    Attributes:
        artifact_id: Artifact this annotation belongs to.
        user_id: User who created the annotation.
        slide_index: Zero-based slide/page index within the artifact.
            Null means the annotation is not tied to a specific slide.
        content: Free-text annotation body (max 4000 chars enforced at schema layer).
    """

    __tablename__ = "artifact_annotations"  # type: ignore[assignment]
    __table_args__ = (
        Index("ix_artifact_annotations_artifact_id", "artifact_id"),
        Index("ix_artifact_annotations_workspace_artifact", "workspace_id", "artifact_id"),
    )

    artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artifacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    slide_index: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<ArtifactAnnotation(id={self.id}, "
            f"artifact_id={self.artifact_id}, "
            f"slide_index={self.slide_index!r})>"
        )


__all__ = ["ArtifactAnnotation"]
