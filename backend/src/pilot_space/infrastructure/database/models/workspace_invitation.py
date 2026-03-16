"""WorkspaceInvitation SQLAlchemy model.

Tracks pending invitations for users who may not yet have an account.
Source: FR-016, US3, plan.md Data Model.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import BaseModel
from pilot_space.infrastructure.database.models.workspace_member import WorkspaceRole

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.user import User
    from pilot_space.infrastructure.database.models.workspace import Workspace


class InvitationStatus(StrEnum):
    """Status of a workspace invitation."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


def _default_expires_at() -> datetime:
    """Default expiry: 7 days from now."""
    return datetime.now(tz=UTC) + timedelta(days=7)


class WorkspaceInvitation(BaseModel):
    """Invitation to join a workspace.

    Tracks pending invitations for users who may not yet have an account.
    When an invited user signs up, pending invitations are auto-accepted
    via ensure_user_synced.

    Attributes:
        workspace_id: FK to Workspace.
        email: Invited email address.
        role: Intended role upon acceptance.
        invited_by: FK to User who sent the invite.
        status: Invitation lifecycle state.
        expires_at: When the invitation expires.
        accepted_at: When the invitation was accepted.
    """

    __tablename__ = "workspace_invitations"  # type: ignore[assignment]

    # Foreign keys
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    role: Mapped[WorkspaceRole] = mapped_column(
        SQLEnum(WorkspaceRole, name="workspace_role", create_type=False),
        nullable=False,
        default=WorkspaceRole.MEMBER,
    )
    invited_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[InvitationStatus] = mapped_column(
        SQLEnum(InvitationStatus, name="invitation_status"),
        nullable=False,
        default=InvitationStatus.PENDING,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_default_expires_at,
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Owner's role hint for invitee (FR-012)
    suggested_sdlc_role: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # Relationships
    workspace: Mapped[Workspace] = relationship(
        "Workspace",
        lazy="joined",
    )
    inviter: Mapped[User] = relationship(
        "User",
        lazy="joined",
    )

    # Indexes and constraints
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "email",
            name="uq_workspace_invitations_pending",
        ),
        Index("ix_workspace_invitations_email_status", "email", "status"),
        Index("ix_workspace_invitations_workspace_status", "workspace_id", "status"),
        Index("ix_workspace_invitations_expires_at", "expires_at"),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<WorkspaceInvitation(email={self.email}, "
            f"workspace_id={self.workspace_id}, status={self.status})>"
        )

    @property
    def is_pending(self) -> bool:
        """Check if invitation is still pending."""
        return self.status == InvitationStatus.PENDING

    @property
    def is_expired(self) -> bool:
        """Check if invitation has expired."""
        if self.status == InvitationStatus.EXPIRED:
            return True
        if self.status == InvitationStatus.PENDING:
            return datetime.now(tz=UTC) > self.expires_at
        return False
