"""PilotAPIKey SQLAlchemy model.

Stores SHA-256-hashed CLI authentication keys scoped per user and workspace.
Plaintext keys are NEVER stored — only the hex digest of SHA-256 is persisted.

Security properties:
- key_hash is the only stored representation; original key cannot be recovered.
- Unique index on key_hash guarantees O(1) lookup without leaking duplicates.
- RLS policy (pilot_api_keys_workspace_isolation) enforces tenant isolation
  at the database layer using the app.current_workspace_id session variable.
- Soft-delete (is_deleted / deleted_at) from BaseModel keeps audit trails.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import WorkspaceScopedModel

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.user import User
    from pilot_space.infrastructure.database.models.workspace import Workspace


class PilotAPIKey(WorkspaceScopedModel):
    """Hashed CLI API key scoped to a user and workspace.

    Inherits from WorkspaceScopedModel which provides:
    - id (UUID PK, gen_random_uuid())
    - workspace_id (FK → workspaces.id CASCADE)
    - created_at, updated_at (TimestampMixin)
    - is_deleted, deleted_at (SoftDeleteMixin)

    Attributes:
        user_id: Owning user. Cascade-deletes key when user is removed.
        key_hash: SHA-256 hex digest (64 chars) of the raw API key.
        name: Human-readable label shown in the UI (max 100 chars).
        last_used_at: UTC timestamp of most recent successful authentication.
        expires_at: Optional UTC expiry; None means the key never expires.
    """

    __tablename__ = "pilot_api_keys"  # type: ignore[assignment]
    __table_args__ = (
        Index("ix_pilot_api_keys_key_hash", "key_hash", unique=True),
        Index("ix_pilot_api_keys_user_id", "user_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        doc="Owning user; cascade-deletes this key when user is removed.",
    )
    key_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        doc="SHA-256 hex digest of the raw API key. Never store plaintext.",
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Human-readable label for this key shown in workspace settings.",
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="UTC timestamp of the last successful authentication with this key.",
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="UTC expiry timestamp. None means the key never expires.",
    )

    # Relationships
    workspace: Mapped[Workspace] = relationship(
        "Workspace",
        lazy="select",
        foreign_keys="PilotAPIKey.workspace_id",
    )
    user: Mapped[User] = relationship(
        "User",
        lazy="select",
        foreign_keys="PilotAPIKey.user_id",
    )

    @property
    def is_expired(self) -> bool:
        """Return True when the key has passed its expiry time.

        Returns:
            False if expires_at is None (key never expires).
            True if the current UTC time is past expires_at.
        """
        if self.expires_at is None:
            return False
        return datetime.now(UTC) > self.expires_at

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<PilotAPIKey(id={self.id}, user_id={self.user_id}, "
            f"workspace_id={self.workspace_id}, name={self.name!r})>"
        )


__all__ = ["PilotAPIKey"]
