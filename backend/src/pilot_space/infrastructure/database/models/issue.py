"""Issue SQLAlchemy model.

Issue is the core work item entity with AI-enhanced metadata,
state machine support, and integration with notes for Note-First workflow.

T118: Create Issue SQLAlchemy model with ai_metadata JSONB.
"""

from __future__ import annotations

import uuid
from datetime import date
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Date,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import WorkspaceScopedModel
from pilot_space.infrastructure.database.types import JSONBCompat

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.activity import Activity
    from pilot_space.infrastructure.database.models.ai_context import AIContext
    from pilot_space.infrastructure.database.models.cycle import Cycle
    from pilot_space.infrastructure.database.models.label import Label
    from pilot_space.infrastructure.database.models.module import Module
    from pilot_space.infrastructure.database.models.note_issue_link import NoteIssueLink
    from pilot_space.infrastructure.database.models.project import Project
    from pilot_space.infrastructure.database.models.state import State
    from pilot_space.infrastructure.database.models.task import Task
    from pilot_space.infrastructure.database.models.user import User


class IssuePriority(StrEnum):
    """Issue priority levels.

    Per spec.md US-02: Priority options are none, low, medium, high, urgent.
    Default is 'none' (no priority set).
    """

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Issue(WorkspaceScopedModel):
    """Issue model for work item tracking.

    Core entity for the issue management feature (US-02).
    Supports AI-enhanced creation with suggestions for title,
    labels, priority, and duplicate detection.

    Issue identifier format: {PROJECT_IDENTIFIER}-{sequence_number}
    Example: PILOT-123

    State machine: Backlog -> Todo -> In Progress -> In Review -> Done
    (Can also be Cancelled or reopened)

    Attributes:
        sequence_id: Auto-incremented number within project.
        name: Issue title (1-255 chars).
        description: Detailed issue description (markdown).
        description_html: Pre-rendered HTML for display.
        priority: Urgency level (none, low, medium, high, urgent).
        state_id: FK to current workflow state.
        project_id: FK to parent project.
        assignee_id: FK to assigned user (optional).
        reporter_id: FK to user who created the issue.
        cycle_id: FK to sprint/cycle (optional).
        module_id: FK to epic/module (optional).
        parent_id: FK to parent issue (for sub-tasks).
        estimate_points: Story points estimate.
        start_date: Planned start date.
        target_date: Due date.
        sort_order: Manual sort order in views.
        ai_metadata: JSONB for AI suggestions and context.
    """

    __tablename__ = "issues"  # type: ignore[assignment]

    # Sequence ID for identifier (e.g., PILOT-123)
    sequence_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Core fields
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    description_html: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Priority
    priority: Mapped[IssuePriority] = mapped_column(
        SQLEnum(
            IssuePriority,
            name="issue_priority",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=IssuePriority.NONE,
    )

    # State (FK to states table)
    state_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("states.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Project (FK)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Assignment
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reporter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Grouping (optional)
    cycle_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cycles.id", ondelete="SET NULL"),
        nullable=True,
    )
    module_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("modules.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Parent issue (for sub-tasks)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("issues.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Estimation and dates
    estimate_points: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    # T-245: Time estimate in hours (0.5 increments, from migration 045)
    estimate_hours: Mapped[float | None] = mapped_column(
        Numeric(6, 1),
        nullable=True,
    )
    start_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    target_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    # Manual sort order for views
    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # AI metadata (JSONBCompat for flexibility)
    ai_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONBCompat,
        nullable=True,
        default=dict,
    )
    # ai_metadata structure:
    # {
    #   "title_enhanced": true,
    #   "title_original": "original title",
    #   "description_expanded": true,
    #   "labels_suggested": ["bug", "auth"],
    #   "labels_confidence": {"bug": 0.9, "auth": 0.75},
    #   "priority_suggested": "high",
    #   "priority_confidence": 0.85,
    #   "assignee_suggested": "user-uuid",
    #   "assignee_confidence": 0.7,
    #   "duplicate_candidates": [
    #     {"issue_id": "uuid", "similarity": 0.82, "explanation": "..."}
    #   ],
    #   "enhancement_model": "claude-sonnet-4-20250514",
    #   "enhancement_timestamp": "2026-01-24T10:00:00Z"
    # }

    # Task management fields (013-task-management)
    acceptance_criteria: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONBCompat,
        nullable=True,
        default=None,
    )
    technical_requirements: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    project: Mapped[Project] = relationship(
        "Project",
        back_populates="issues",
        lazy="joined",
    )
    state: Mapped[State] = relationship(
        "State",
        lazy="joined",
    )
    assignee: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[assignee_id],
        lazy="joined",
    )
    reporter: Mapped[User] = relationship(
        "User",
        foreign_keys=[reporter_id],
        lazy="joined",
    )
    cycle: Mapped[Cycle | None] = relationship(
        "Cycle",
        back_populates="issues",
        lazy="selectin",
    )
    module: Mapped[Module | None] = relationship(
        "Module",
        back_populates="issues",
        lazy="selectin",
    )
    parent: Mapped[Issue | None] = relationship(
        "Issue",
        remote_side="Issue.id",
        back_populates="sub_issues",
        lazy="selectin",
    )
    sub_issues: Mapped[list[Issue]] = relationship(
        "Issue",
        back_populates="parent",
        lazy="selectin",
    )
    labels: Mapped[list[Label]] = relationship(
        "Label",
        secondary="issue_labels",
        back_populates="issues",
        lazy="selectin",
    )
    activities: Mapped[list[Activity]] = relationship(
        "Activity",
        back_populates="issue",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    note_links: Mapped[list[NoteIssueLink]] = relationship(
        "NoteIssueLink",
        back_populates="issue",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    ai_context: Mapped[AIContext | None] = relationship(
        "AIContext",
        back_populates="issue",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    tasks: Mapped[list[Task]] = relationship(
        "Task",
        back_populates="issue",
        cascade="all, delete-orphan",
        lazy="raise",
    )

    # Indexes and constraints
    __table_args__ = (
        # Unique sequence within project
        UniqueConstraint(
            "project_id",
            "sequence_id",
            name="uq_issues_project_sequence",
        ),
        # Common query indexes
        Index("ix_issues_project_id", "project_id"),
        Index("ix_issues_state_id", "state_id"),
        Index("ix_issues_assignee_id", "assignee_id"),
        Index("ix_issues_reporter_id", "reporter_id"),
        Index("ix_issues_cycle_id", "cycle_id"),
        Index("ix_issues_module_id", "module_id"),
        Index("ix_issues_parent_id", "parent_id"),
        Index("ix_issues_priority", "priority"),
        Index("ix_issues_is_deleted", "is_deleted"),
        Index("ix_issues_created_at", "created_at"),
        Index("ix_issues_target_date", "target_date"),
        # Composite indexes for common filters
        Index("ix_issues_project_state", "project_id", "state_id"),
        Index("ix_issues_project_assignee", "project_id", "assignee_id"),
        Index("ix_issues_workspace_project", "workspace_id", "project_id"),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<Issue(id={self.id}, identifier={self.identifier})>"

    @property
    def identifier(self) -> str:
        """Get the human-readable identifier (e.g., PILOT-123).

        Requires project to be loaded.
        """
        if self.project:
            return f"{self.project.identifier}-{self.sequence_id}"
        return f"???-{self.sequence_id}"

    @property
    def is_completed(self) -> bool:
        """Check if issue is in a completed state."""
        if self.state:
            return self.state.is_terminal
        return False

    @property
    def is_active(self) -> bool:
        """Check if issue is in an active (started) state."""
        if self.state:
            return self.state.is_active
        return False

    @property
    def has_ai_enhancements(self) -> bool:
        """Check if AI has enhanced this issue."""
        if not self.ai_metadata:
            return False
        return any(
            self.ai_metadata.get(key)
            for key in ["title_enhanced", "description_expanded", "labels_suggested"]
        )

    @property
    def duplicate_candidates(self) -> list[dict[str, Any]]:
        """Get list of potential duplicate issues from AI metadata."""
        if not self.ai_metadata:
            return []
        return self.ai_metadata.get("duplicate_candidates", [])
