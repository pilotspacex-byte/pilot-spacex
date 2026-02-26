"""ChatAttachment SQLAlchemy model.

Tracks metadata for files uploaded to temporary Supabase Storage for use as
AI chat context. File bytes live in Storage; this table holds metadata and
the storage key for retrieval and TTL-based cleanup.

Feature: 020 — Chat Context Attachments
Source: FR-001, FR-004, FR-008, US-1, US-2
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from pilot_space.infrastructure.database.base import Base, TimestampMixin


class ChatAttachment(Base, TimestampMixin):
    """Metadata record for a file attached to an AI chat session.

    Stores the Supabase Storage key and file metadata needed to inject
    file contents into the AI context window. Rows expire after 24 hours
    and are cleaned up by a pg_cron job.

    Storage key format:
        chat-attachments/{workspace_id}/{user_id}/{attachment_id}/{filename}

    Attributes:
        id: Primary key UUID.
        workspace_id: Workspace owning this attachment (RLS filter).
        user_id: User who uploaded the file (ownership).
        session_id: Chat session active at upload time; nullable.
        filename: Original filename including extension (max 255 chars).
        mime_type: MIME type, e.g. ``application/pdf`` (max 100 chars).
        size_bytes: File size in bytes; must be > 0.
        storage_key: Supabase Storage object path; globally unique.
        source: Upload origin — ``local`` or ``google_drive``.
        drive_file_id: Google Drive file ID; non-null iff source is
            ``google_drive``.
        expires_at: TTL timestamp; defaults to NOW() + 24 hours.
        created_at: Row creation timestamp (from TimestampMixin).
        updated_at: Last modification timestamp (from TimestampMixin).
    """

    __tablename__ = "chat_attachments"
    __table_args__ = (
        Index("ix_chat_attachments_workspace_user", "workspace_id", "user_id"),
        Index("ix_chat_attachments_session", "session_id"),
        Index("ix_chat_attachments_expires_at", "expires_at"),
        CheckConstraint(
            "source IN ('local', 'google_drive')",
            name="ck_chat_attachments_source",
        ),
        CheckConstraint("size_bytes > 0", name="ck_chat_attachments_size"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    session_id: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    storage_key: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        unique=True,
    )
    source: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    drive_file_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW() + INTERVAL '24 hours'"),
    )

    def __new__(cls, **kw: object) -> ChatAttachment:  # noqa: ARG004
        """Create instance and ensure SQLAlchemy instrumentation is initialized.

        SQLAlchemy's instrumented attributes require ``_sa_instance_state`` to be
        present on the instance.  When code (e.g., unit tests) creates an instance
        via ``ChatAttachment.__new__(ChatAttachment)`` without immediately calling
        ``__init__``, the ORM state is absent and attribute access raises
        ``AttributeError``.  Overriding ``__new__`` here to call ``__init__``
        ensures the state is always set up, regardless of how the instance is
        constructed.
        """
        instance = super().__new__(cls)
        # Initialize SQLAlchemy instrumentation so attributes work without a session.
        cls.__init__(instance)
        return instance

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<ChatAttachment(id={self.id}, filename={self.filename!r}, source={self.source!r})>"


__all__ = ["ChatAttachment"]
