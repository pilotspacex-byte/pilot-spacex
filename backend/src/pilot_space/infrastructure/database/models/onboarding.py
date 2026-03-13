"""WorkspaceOnboarding SQLAlchemy model.

Persists onboarding state per workspace with JSONB steps column.
RLS policy restricts access to workspace owners and admins.

T008: Create WorkspaceOnboarding SQLAlchemy model.
Source: FR-001, FR-002, FR-003, US1
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import BaseModel
from pilot_space.infrastructure.database.types import JSONBCompat

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.note import Note
    from pilot_space.infrastructure.database.models.workspace import Workspace


class WorkspaceOnboarding(BaseModel):
    """SQLAlchemy model for workspace onboarding state.

    Tracks the 4-step onboarding progress per workspace.
    One-to-one relationship with Workspace.

    Attributes:
        workspace_id: FK to workspaces.id, UNIQUE constraint.
        steps: JSONB column tracking step completion.
        guided_note_id: Optional FK to notes.id for guided note.
        dismissed_at: When checklist was dismissed.
        completed_at: When all steps were completed.

    RLS Policy (T010):
        workspace_id IN (
            SELECT workspace_id FROM workspace_members
            WHERE user_id = auth.uid() AND role IN ('owner', 'admin')
        )
    """

    __tablename__ = "workspace_onboardings"  # type: ignore[assignment]

    # Workspace reference (1:1)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Steps JSONB tracking completion of each onboarding step
    steps: Mapped[dict[str, Any]] = mapped_column(
        JSONBCompat,
        nullable=False,
        default=lambda: {
            "ai_providers": False,
            "invite_members": False,
            "first_note": False,
            "role_setup": False,
        },
    )

    # Reference to guided note (optional)
    guided_note_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notes.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Dismissed timestamp
    dismissed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Completed timestamp (when all steps done)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    workspace: Mapped[Workspace] = relationship(
        "Workspace",
        lazy="joined",
    )
    guided_note: Mapped[Note | None] = relationship(
        "Note",
        lazy="joined",
    )

    # Indexes and constraints
    __table_args__ = (
        UniqueConstraint("workspace_id", name="uq_workspace_onboardings_workspace_id"),
        Index("ix_workspace_onboardings_completed_at", "completed_at"),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        completed = sum(
            [
                self.steps.get("ai_providers", False),
                self.steps.get("invite_members", False),
                self.steps.get("first_note", False),
                self.steps.get("role_setup", False),
            ]
        )
        return f"<WorkspaceOnboarding(workspace_id={self.workspace_id}, {completed}/4)>"

    @property
    def completion_percentage(self) -> int:
        """Calculate completion percentage from steps.

        Returns:
            Percentage (0-100) of completed steps.
        """
        count = sum(
            [
                self.steps.get("ai_providers", False),
                self.steps.get("invite_members", False),
                self.steps.get("first_note", False),
                self.steps.get("role_setup", False),
            ]
        )
        return (count * 100) // 4

    @property
    def is_complete(self) -> bool:
        """Check if all steps are complete.

        Returns:
            True if all 4 steps are completed.
        """
        return (
            self.steps.get("ai_providers", False)
            and self.steps.get("invite_members", False)
            and self.steps.get("first_note", False)
            and self.steps.get("role_setup", False)
        )


__all__ = ["WorkspaceOnboarding"]
