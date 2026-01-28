"""Project SQLAlchemy model.

Project is a workspace-scoped container for issues, notes, cycles, and modules.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import WorkspaceScopedModel
from pilot_space.infrastructure.database.types import JSONBCompat

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.cycle import Cycle
    from pilot_space.infrastructure.database.models.issue import Issue
    from pilot_space.infrastructure.database.models.label import Label
    from pilot_space.infrastructure.database.models.module import Module
    from pilot_space.infrastructure.database.models.state import State
    from pilot_space.infrastructure.database.models.user import User
    from pilot_space.infrastructure.database.models.workspace import Workspace


class Project(WorkspaceScopedModel):
    """Project model for organizing issues and notes.

    Each project belongs to a workspace and contains:
    - Issues (work items)
    - Notes (collaborative documents)
    - Cycles (sprints)
    - Modules (epics/features)
    - States (workflow)
    - Labels (categorization)

    Attributes:
        name: Display name of the project.
        identifier: Short code (e.g., "PILOT", max 5 chars).
        description: Optional project description.
        icon: Emoji or icon identifier.
        settings: JSONB for project-level configuration.
        lead_id: Optional FK to User who leads the project.
    """

    __tablename__ = "projects"  # type: ignore[assignment]

    # Core fields
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    identifier: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    icon: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # Settings (JSONBCompat for flexibility)
    settings: Mapped[dict[str, Any] | None] = mapped_column(
        JSONBCompat,
        nullable=True,
        default=dict,
    )

    # Project lead (optional)
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    workspace: Mapped[Workspace] = relationship(
        "Workspace",
        back_populates="projects",
        lazy="joined",
    )
    lead: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[lead_id],
        lazy="joined",
    )
    states: Mapped[list[State]] = relationship(
        "State",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    labels: Mapped[list[Label]] = relationship(
        "Label",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    modules: Mapped[list[Module]] = relationship(
        "Module",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    cycles: Mapped[list[Cycle]] = relationship(
        "Cycle",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    issues: Mapped[list[Issue]] = relationship(
        "Issue",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    # Indexes and constraints
    __table_args__ = (
        Index("ix_projects_identifier", "identifier"),
        Index("ix_projects_lead_id", "lead_id"),
        Index("ix_projects_is_deleted", "is_deleted"),
        UniqueConstraint(
            "workspace_id",
            "identifier",
            name="uq_projects_workspace_identifier",
        ),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<Project(id={self.id}, identifier={self.identifier})>"
