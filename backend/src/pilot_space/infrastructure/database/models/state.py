"""State SQLAlchemy model.

State represents workflow states for issues (e.g., Backlog, In Progress, Done).
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import WorkspaceScopedModel

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.project import Project


class StateGroup(str, Enum):
    """Groups for workflow states.

    Per FR-003: States are grouped for filtering and reporting.
    - unstarted: Work not yet begun (Backlog, Todo)
    - started: Work in progress (In Progress, In Review)
    - completed: Work finished (Done)
    - cancelled: Work abandoned (Cancelled)
    """

    UNSTARTED = "unstarted"
    STARTED = "started"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# Default states with colors and groups
DEFAULT_STATES: list[dict[str, str | StateGroup | int]] = [
    {"name": "Backlog", "color": "#94a3b8", "group": StateGroup.UNSTARTED, "sequence": 0},
    {"name": "Todo", "color": "#60a5fa", "group": StateGroup.UNSTARTED, "sequence": 1},
    {"name": "In Progress", "color": "#fbbf24", "group": StateGroup.STARTED, "sequence": 2},
    {"name": "In Review", "color": "#a78bfa", "group": StateGroup.STARTED, "sequence": 3},
    {"name": "Done", "color": "#22c55e", "group": StateGroup.COMPLETED, "sequence": 4},
    {"name": "Cancelled", "color": "#ef4444", "group": StateGroup.CANCELLED, "sequence": 5},
]


class State(WorkspaceScopedModel):
    """State model for issue workflow.

    States can be workspace-wide (project_id=NULL) or project-specific.
    Default states are created when a workspace/project is created.

    Attributes:
        name: Display name of the state.
        color: Hex color code for UI display.
        group: StateGroup for categorization.
        sequence: Order for display (lower = earlier in workflow).
        project_id: Optional FK for project-specific states.
    """

    __tablename__ = "states"  # type: ignore[assignment]

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
    group: Mapped[StateGroup] = mapped_column(
        SQLEnum(
            StateGroup,
            name="state_group",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=StateGroup.UNSTARTED,
    )
    sequence: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
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
        back_populates="states",
        lazy="joined",
    )

    # Indexes and constraints
    __table_args__ = (
        Index("ix_states_project_id", "project_id"),
        Index("ix_states_group", "group"),
        Index("ix_states_sequence", "sequence"),
        Index("ix_states_is_deleted", "is_deleted"),
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "name",
            name="uq_states_workspace_project_name",
        ),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<State(id={self.id}, name={self.name}, group={self.group})>"

    @property
    def is_terminal(self) -> bool:
        """Check if this is a terminal state (completed or cancelled)."""
        return self.group in (StateGroup.COMPLETED, StateGroup.CANCELLED)

    @property
    def is_active(self) -> bool:
        """Check if this is an active state (started)."""
        return self.group == StateGroup.STARTED
