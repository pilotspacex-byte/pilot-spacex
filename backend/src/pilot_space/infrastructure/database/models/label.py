"""Label SQLAlchemy model.

Label is used for categorizing issues with customizable tags.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import WorkspaceScopedModel

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.issue import Issue
    from pilot_space.infrastructure.database.models.project import Project


class Label(WorkspaceScopedModel):
    """Label model for issue categorization.

    Labels can be workspace-wide (project_id=NULL) or project-specific.
    Used for filtering and organizing issues.

    Attributes:
        name: Display name of the label.
        color: Hex color code for UI display.
        description: Optional description of label purpose.
        project_id: Optional FK for project-specific labels.
    """

    __tablename__ = "labels"  # type: ignore[assignment]

    # Core fields
    name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    color: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="#6b7280",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Optional project-specific scope
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
    )

    # Relationships
    project: Mapped[Project | None] = relationship(
        "Project",
        back_populates="labels",
        lazy="joined",
    )
    issues: Mapped[list[Issue]] = relationship(
        "Issue",
        secondary="issue_labels",
        back_populates="labels",
        lazy="raise",
    )

    # Indexes and constraints
    __table_args__ = (
        Index("ix_labels_project_id", "project_id"),
        Index("ix_labels_name", "name"),
        Index("ix_labels_is_deleted", "is_deleted"),
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "name",
            name="uq_labels_workspace_project_name",
        ),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<Label(id={self.id}, name={self.name})>"
