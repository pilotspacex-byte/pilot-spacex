"""WorkspaceSession SQLAlchemy model.

Tracks authenticated sessions per workspace member for audit and
force-termination support (AUTH-06).
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import WorkspaceScopedModel

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.user import User
    from pilot_space.infrastructure.database.models.workspace import Workspace


class WorkspaceSession(WorkspaceScopedModel):
    """Authenticated session record for a workspace member.

    Records every authenticated session so admins can audit active sessions,
    throttle `last_seen_at` updates, and force-revoke sessions without
    invalidating the Supabase JWT (which may have a longer TTL).

    Attributes:
        workspace_id: FK to owning workspace (from WorkspaceScopedModel).
        user_id: FK to the authenticated user.
        session_token_hash: SHA-256 hex hash of the session token (64 chars).
        ip_address: IPv4 or IPv6 address (max 45 chars) of the client.
        user_agent: Raw User-Agent header string.
        last_seen_at: Last activity timestamp; throttled to avoid write storms.
        revoked_at: Timestamp when an admin force-terminated this session.
        user: Related User object.
        workspace: Related Workspace object.
    """

    __tablename__ = "workspace_sessions"  # type: ignore[assignment]
    __table_args__ = (
        Index("ix_workspace_sessions_token_hash", "session_token_hash"),
        Index("ix_workspace_sessions_user_id", "user_id"),
        Index("ix_workspace_sessions_workspace_id", "workspace_id"),
    )

    # Session owner
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Token identification (hashed — never store raw token)
    session_token_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        doc="SHA-256 hex digest of the session token",
    )

    # Client metadata
    ip_address: Mapped[str | None] = mapped_column(
        String(45),  # Supports IPv6 (max 45 chars)
        nullable=True,
        doc="Client IP address (IPv4 or IPv6)",
    )
    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Raw User-Agent header string",
    )

    # Temporal tracking
    last_seen_at: Mapped[str] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="Last activity timestamp; throttled updates to avoid write storms",
    )
    revoked_at: Mapped[str | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Set when an admin force-terminates the session",
    )

    # Relationships
    user: Mapped[User] = relationship(
        "User",
        lazy="select",
    )
    workspace: Mapped[Workspace] = relationship(
        "Workspace",
        lazy="select",
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<WorkspaceSession(user_id={self.user_id}, "
            f"workspace_id={self.workspace_id}, "
            f"revoked={self.revoked_at is not None})>"
        )

    @property
    def is_active(self) -> bool:
        """Return True if the session has not been revoked."""
        return self.revoked_at is None
