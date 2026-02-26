"""DriveCredential SQLAlchemy model.

Stores per-user, per-workspace Google Drive OAuth tokens (Fernet-encrypted).
Enables persistent Drive access without re-authorization.

Source: Feature 020 — Chat Context Attachments & Google Drive (FR-009, FR-010, FR-012)
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from pilot_space.infrastructure.database.base import Base, TimestampMixin


class DriveCredential(Base, TimestampMixin):
    """Per-user, per-workspace Google Drive OAuth credential.

    Tokens are Fernet-encrypted at the service layer before storage and
    decrypted at the service layer after retrieval. This model stores
    ciphertext only — no plaintext tokens ever persist here.

    Attributes:
        id: Primary key UUID.
        user_id: Owning user; CASCADE delete removes credential on user removal.
        workspace_id: Workspace scope; CASCADE delete removes credential on workspace removal.
        google_email: Connected Google account address shown in UI.
        access_token: Fernet-encrypted OAuth access token (ciphertext).
        refresh_token: Fernet-encrypted OAuth refresh token (ciphertext).
        token_expires_at: UTC expiry of access token; refresh when < NOW().
        scope: Granted OAuth scope string (space-delimited).
        created_at: Row creation timestamp (from TimestampMixin).
        updated_at: Last update timestamp; refreshed on every token rotation (from TimestampMixin).
    """

    __tablename__ = "drive_credentials"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "workspace_id",
            name="uq_drive_credentials_user_workspace",
        ),
        Index("ix_drive_credentials_user_workspace", "user_id", "workspace_id"),
        Index("ix_drive_credentials_expires_at", "token_expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    google_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    access_token: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    refresh_token: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    token_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    scope: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<DriveCredential(id={self.id}, user_id={self.user_id}, "
            f"workspace_id={self.workspace_id}, google_email={self.google_email!r})>"
        )


__all__ = ["DriveCredential"]
