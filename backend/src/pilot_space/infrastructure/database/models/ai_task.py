"""AITask SQLAlchemy model.

Tracks units of work within the AI task system. Tasks can depend on
other tasks and show progress updates via TaskPanel UI.

References:
- T010: Create ai_tasks table
- specs/005-conversational-agent-arch/data-model.md
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import Base
from pilot_space.infrastructure.database.types import JSONBCompat

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.ai_session import AISession


class TaskStatus(StrEnum):
    """Status of a task in the AI task system."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class AITask(Base):
    """Tracked task in the AI task system.

    Represents a decomposed unit of work with dependencies and progress tracking.
    Tasks are displayed in the TaskPanel UI and can be reassigned or unblocked.

    Attributes:
        session_id: Reference to parent session.
        subject: Brief task title (imperative form).
        description: Optional detailed description.
        status: Task lifecycle state (pending, in_progress, completed, failed, blocked).
        owner: Agent name or "user" handling the task.
        progress: Completion percentage (0-100).
        task_metadata: Additional task-specific data.
        blocked_by_id: Reference to blocking task (dependency chain).
        created_at: When the task was created.
        updated_at: When the task was last updated.
    """

    __tablename__ = "ai_tasks"
    __table_args__ = (
        Index("ix_ai_tasks_session_id", "session_id"),
        Index("ix_ai_tasks_session_status", "session_id", "status"),
        {"schema": None},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default="gen_random_uuid()",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Session reference
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Task details
    subject: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Brief task title (imperative form)",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Optional detailed description",
    )

    # Status and ownership
    status: Mapped[TaskStatus] = mapped_column(
        String(20),
        default=TaskStatus.PENDING,
        nullable=False,
        doc="Task lifecycle state",
    )

    owner: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="Agent name or 'user' handling the task",
    )

    progress: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Completion percentage (0-100)",
    )

    # Additional data
    task_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",  # Column name in DB
        JSONBCompat,
        nullable=True,
        doc="Additional task-specific data",
    )

    # Dependencies (self-referential)
    blocked_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_tasks.id", ondelete="SET NULL"),
        nullable=True,
        doc="Reference to blocking task (dependency chain)",
    )

    # Relationships
    session: Mapped[AISession] = relationship(
        "AISession",
        back_populates="tasks",
        lazy="selectin",
    )

    blocked_by: Mapped[AITask | None] = relationship(
        "AITask",
        remote_side="AITask.id",
        backref="blocking",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<AITask(id={self.id}, subject='{self.subject}', "
            f"status={self.status}, progress={self.progress}%)>"
        )
