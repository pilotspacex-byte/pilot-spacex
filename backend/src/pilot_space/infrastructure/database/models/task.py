"""Task SQLAlchemy model for issue-scoped task management.

Persistent tasks decomposed from issues, with AI generation support
and Claude Code prompt export.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import WorkspaceScopedModel
from pilot_space.infrastructure.database.types import JSONBCompat

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.issue import Issue


class TaskStatus(str, Enum):
    """Task status values."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class Task(WorkspaceScopedModel):
    """Persistent task entity scoped to an issue.

    Tasks are decomposed from issues either manually or via AI.
    Each task can include acceptance criteria, code references,
    and a ready-to-use Claude Code prompt.
    """

    __tablename__ = "tasks"  # type: ignore[assignment]

    # Parent issue
    issue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("issues.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Core fields
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    acceptance_criteria: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONBCompat,
        nullable=True,
        default=None,
    )

    # Status
    status: Mapped[TaskStatus] = mapped_column(
        SQLEnum(
            TaskStatus,
            name="task_status_enum",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=TaskStatus.TODO,
    )

    # Ordering
    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Estimation
    estimated_hours: Mapped[float | None] = mapped_column(
        Numeric(5, 1),
        nullable=True,
    )

    # Code context
    code_references: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONBCompat,
        nullable=True,
        default=None,
    )

    # AI fields
    ai_prompt: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    ai_generated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    # Dependencies (stored as list of task UUIDs)
    dependency_ids: Mapped[list[str] | None] = mapped_column(
        JSONBCompat,
        nullable=True,
        default=None,
    )

    # Relationships
    issue: Mapped[Issue] = relationship(
        "Issue",
        back_populates="tasks",
        lazy="joined",
    )

    # Indexes and constraints
    __table_args__ = (
        Index("ix_tasks_issue_id", "issue_id"),
        Index("ix_tasks_workspace_id", "workspace_id"),
        Index("ix_tasks_status", "status"),
        Index("ix_tasks_issue_sort", "issue_id", "sort_order"),
        Index("ix_tasks_is_deleted", "is_deleted"),
    )

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, title={self.title!r}, status={self.status})>"
