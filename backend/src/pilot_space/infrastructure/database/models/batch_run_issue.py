"""BatchRunIssue SQLAlchemy model.

BatchRunIssue is the per-issue tracking record within a BatchRun.
Each row represents a single issue's journey through AI autonomous
implementation: from queued → running → completed/failed.

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
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import WorkspaceScopedModel

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.batch_run import BatchRun
    from pilot_space.infrastructure.database.models.issue import Issue


class BatchRunIssueStatus(StrEnum):
    """Status of a single issue within a batch run.

    State machine:
        pending → queued → running → completed | failed | cancelled
    """

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BatchRunIssue(WorkspaceScopedModel):
    """BatchRunIssue tracks a single issue's execution within a batch run.

    Created when a BatchRun is dispatched. Stores execution metadata including
    the worktree path used by Claude Code, the resulting PR URL, timing,
    error messages on failure, and AI cost in cents.

    Attributes:
        batch_run_id: FK to parent batch run.
        issue_id: FK to the issue being implemented.
        status: Current execution status for this issue.
        execution_order: Priority order within the batch (lower = earlier).
        worktree_path: Local filesystem path for Claude Code's git worktree.
        pr_url: GitHub/GitLab PR URL created by Claude Code (nullable until done).
        started_at: When Claude Code began work on this issue.
        completed_at: When implementation completed/failed.
        error_message: Failure details if status is 'failed'.
        cost_cents: AI API cost incurred for this issue (in US cents * 100).
    """

    __tablename__ = "batch_run_issues"  # type: ignore[assignment]

    # Parent batch run
    batch_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("batch_runs.id", ondelete="CASCADE"),
        nullable=False,
    )

    # The issue being implemented
    issue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("issues.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Execution state
    status: Mapped[BatchRunIssueStatus] = mapped_column(
        SQLEnum(
            BatchRunIssueStatus,
            name="batch_run_issue_status",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=BatchRunIssueStatus.PENDING,
    )

    # Dispatch ordering (dependency-topological sort order)
    execution_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Claude Code execution details
    worktree_path: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    pr_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Timing
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Error details on failure
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Fine-grained execution stage for SSE (cloning/implementing/creating_pr)
    # Persisted so late-joining SSE clients see current sub-stage.
    current_stage: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # AI cost tracking (cents × 100 to avoid floating point — e.g., 125 = $0.0125)
    cost_cents: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Relationships
    batch_run: Mapped[BatchRun] = relationship(
        "BatchRun",
        back_populates="items",
        lazy="selectin",
    )
    issue: Mapped[Issue] = relationship(
        "Issue",
        lazy="selectin",
    )

    # Indexes and constraints
    __table_args__ = (
        UniqueConstraint(
            "batch_run_id",
            "issue_id",
            name="uq_batch_run_issues_run_issue",
        ),
        Index("ix_batch_run_issues_batch_run_id", "batch_run_id"),
        Index("ix_batch_run_issues_issue_id", "issue_id"),
        Index("ix_batch_run_issues_status", "status"),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<BatchRunIssue(id={self.id}, "
            f"issue_id={self.issue_id}, "
            f"status={self.status.value})>"
        )

    @property
    def is_terminal(self) -> bool:
        """Check if this issue has reached a terminal state."""
        return self.status in (
            BatchRunIssueStatus.COMPLETED,
            BatchRunIssueStatus.FAILED,
            BatchRunIssueStatus.CANCELLED,
        )
