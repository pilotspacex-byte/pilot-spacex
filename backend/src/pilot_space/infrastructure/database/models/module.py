"""Module SQLAlchemy model.

Module represents an epic or feature grouping for issues.
Per FR-006: Module = Epic for organizing related work items.
"""

from __future__ import annotations

import uuid
from datetime import date
from enum import StrEnum
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


class ModuleStatus(StrEnum):
    """Status for module lifecycle.

    Modules progress through: planned → active → completed/cancelled
    """

    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Module(WorkspaceScopedModel):
    """Module model for epic/feature grouping.

    Modules organize related issues into larger units of work.
    Each module belongs to exactly one project.

    Attributes:
        name: Display name of the module.
        description: Optional detailed description.
        status: Current lifecycle status.
        target_date: Optional deadline for module completion.
        sort_order: Display order within project.
        project_id: FK to parent Project (required).
        lead_id: Optional FK to User leading this module.
    """

    __tablename__ = "modules"  # type: ignore[assignment]

    # Core fields
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    status: Mapped[ModuleStatus] = mapped_column(
        SQLEnum(ModuleStatus, name="module_status", create_type=False),
        nullable=False,
        default=ModuleStatus.PLANNED,
    )
    target_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Required project scope
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Optional module lead
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    project: Mapped[Project] = relationship(
        "Project",
        back_populates="modules",
        lazy="joined",
    )
    lead: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[lead_id],
        lazy="joined",
    )
    issues: Mapped[list[Issue]] = relationship(
        "Issue",
        back_populates="module",
        lazy="dynamic",
    )

    # Indexes and constraints
    __table_args__ = (
        Index("ix_modules_project_id", "project_id"),
        Index("ix_modules_status", "status"),
        Index("ix_modules_lead_id", "lead_id"),
        Index("ix_modules_sort_order", "sort_order"),
        Index("ix_modules_is_deleted", "is_deleted"),
        UniqueConstraint(
            "project_id",
            "name",
            name="uq_modules_project_name",
        ),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<Module(id={self.id}, name={self.name}, status={self.status})>"

    @property
    def is_active(self) -> bool:
        """Check if module is actively being worked on."""
        return self.status == ModuleStatus.ACTIVE

    @property
    def is_complete(self) -> bool:
        """Check if module is completed or cancelled."""
        return self.status in (ModuleStatus.COMPLETED, ModuleStatus.CANCELLED)
