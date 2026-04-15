"""BatchRun SQLAlchemy model.

BatchRun represents a sprint batch execution — when a PM approves a sprint cycle
for autonomous AI implementation. Tracks the overall state of a batch job that
dispatches multiple issues to Claude Code via pilot-cli.

Phase 73 Plan 01 — v2.0 Autonomous SDLC foundation.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import WorkspaceScopedModel

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.batch_run_issue import BatchRunIssue
    from pilot_space.infrastructure.database.models.cycle import Cycle
    from pilot_space.infrastructure.database.models.user import User


class BatchRunStatus(StrEnum):
    """Status of a sprint batch run.

    State machine:
        pending → running → completed | failed
        running → paused → running (resume)
        running → failed (error)
    """

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class BatchRun(WorkspaceScopedModel):
    """BatchRun model for sprint batch execution tracking.

    Represents a single execution of AI-autonomous implementation across
    all issues in a sprint cycle. Tracks aggregate progress and connects
    back to the triggering user and target cycle.

    Attributes:
        cycle_id: FK to the sprint cycle being batch-implemented.
        status: Current execution status.
        started_at: When batch execution began (nullable until started).
        completed_at: When batch completed/failed (nullable until done).
        triggered_by_id: FK to user who initiated the batch run.
        total_issues: Total number of issues in this batch.
        completed_issues: Count of successfully implemented issues.
        failed_issues: Count of issues that failed implementation.
    """

    __tablename__ = "batch_runs"  # type: ignore[assignment]

    # Sprint cycle this batch targets
    cycle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cycles.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Execution state
    status: Mapped[BatchRunStatus] = mapped_column(
        SQLEnum(
            BatchRunStatus,
            name="batch_run_status",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=BatchRunStatus.PENDING,
    )

    # Timestamps for execution window
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Who initiated the batch run
    triggered_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Progress counters
    total_issues: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    completed_issues: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    failed_issues: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Relationships
    cycle: Mapped[Cycle] = relationship(
        "Cycle",
        lazy="selectin",
    )
    triggered_by: Mapped[User] = relationship(
        "User",
        foreign_keys=[triggered_by_id],
        lazy="selectin",
    )
    items: Mapped[list[BatchRunIssue]] = relationship(
        "BatchRunIssue",
        back_populates="batch_run",
        lazy="selectin",
    )

    # Indexes
    __table_args__ = (
        Index("ix_batch_runs_workspace_id", "workspace_id"),
        Index("ix_batch_runs_cycle_id", "cycle_id"),
        Index("ix_batch_runs_status", "status"),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<BatchRun(id={self.id}, status={self.status.value})>"

    @property
    def is_active(self) -> bool:
        """Check if batch run is currently executing."""
        return self.status in (BatchRunStatus.RUNNING, BatchRunStatus.PAUSED)

    @property
    def is_complete(self) -> bool:
        """Check if batch run has finished (success or failure)."""
        return self.status in (BatchRunStatus.COMPLETED, BatchRunStatus.FAILED)

    @property
    def progress_percent(self) -> float:
        """Calculate completion percentage (0.0–100.0)."""
        if self.total_issues == 0:
            return 0.0
        return round((self.completed_issues + self.failed_issues) / self.total_issues * 100, 1)
