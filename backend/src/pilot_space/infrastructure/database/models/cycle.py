"""Cycle SQLAlchemy model.

Cycle represents a sprint/iteration for grouping issues.
Used by US-04 Sprint Planning feature.
"""

from __future__ import annotations

import uuid
from datetime import date
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Date,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import WorkspaceScopedModel

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.issue import Issue
    from pilot_space.infrastructure.database.models.project import Project
    from pilot_space.infrastructure.database.models.user import User


class CycleStatus(str, Enum):
    """Cycle status values.

    Per US-04 spec: Cycles progress through planned -> active -> completed.
    """

    DRAFT = "draft"
    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Cycle(WorkspaceScopedModel):
    """Cycle model for sprint/iteration tracking.

    Groups issues into time-boxed iterations with:
    - Start and end dates
    - Velocity tracking
    - Burndown metrics

    Attributes:
        name: Cycle name (e.g., "Sprint 1").
        description: Optional description.
        project_id: FK to parent project.
        status: Current cycle status.
        start_date: Cycle start date.
        end_date: Cycle end date.
        sequence: Order within project.
        owned_by_id: FK to user who manages this cycle.
    """

    __tablename__ = "cycles"  # type: ignore[assignment]

    # Core fields
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Project relationship
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Status and dates
    status: Mapped[CycleStatus] = mapped_column(
        SQLEnum(
            CycleStatus,
            name="cycle_status",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=CycleStatus.DRAFT,
    )
    start_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    end_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    # Ordering
    sequence: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Ownership
    owned_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    project: Mapped[Project] = relationship(
        "Project",
        back_populates="cycles",
        lazy="joined",
    )
    owned_by: Mapped[User | None] = relationship(
        "User",
        lazy="joined",
    )
    issues: Mapped[list[Issue]] = relationship(
        "Issue",
        back_populates="cycle",
        lazy="selectin",
    )

    # Indexes and constraints
    __table_args__ = (
        Index("ix_cycles_project_id", "project_id"),
        Index("ix_cycles_status", "status"),
        Index("ix_cycles_start_date", "start_date"),
        Index("ix_cycles_end_date", "end_date"),
        Index("ix_cycles_is_deleted", "is_deleted"),
        UniqueConstraint(
            "project_id",
            "name",
            name="uq_cycles_project_name",
        ),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<Cycle(id={self.id}, name={self.name}, status={self.status.value})>"

    @property
    def is_active(self) -> bool:
        """Check if cycle is currently active."""
        return self.status == CycleStatus.ACTIVE

    @property
    def is_completed(self) -> bool:
        """Check if cycle is completed."""
        return self.status == CycleStatus.COMPLETED
