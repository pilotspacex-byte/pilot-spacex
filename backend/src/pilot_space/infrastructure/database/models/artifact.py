"""Artifact SQLAlchemy model.

Tracks metadata for files uploaded to Supabase Storage as note artifacts.
Uses DB-first upload flow: status=pending_upload on create, status=ready after
successful storage upload. Stale pending_upload records are cleaned by a 24h job.

Storage key format: {workspace_id}/{project_id}/{artifact_id}/{filename}
Bucket: note-artifacts (separate from chat-attachments which has 24h TTL expiry)

Feature: v1.1 — Artifacts
"""

from __future__ import annotations

import uuid

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from pilot_space.infrastructure.database.base import WorkspaceScopedModel


class Artifact(WorkspaceScopedModel):
    """Metadata record for a file uploaded to the note-artifacts Supabase Storage bucket.

    Inherits id (UUID PK), workspace_id (FK + index), is_deleted, deleted_at,
    created_at, updated_at from WorkspaceScopedModel.

    Status transitions:
        pending_upload -> ready  (happy path: DB record created, then storage upload succeeds)
        pending_upload remains  (storage upload failed; cleaned up by artifact_cleanup job after 24h)

    Attributes:
        project_id: Project owning this artifact.
        user_id: User who uploaded the file.
        filename: Original filename including extension (max 255 chars).
        mime_type: MIME type, e.g. "image/png" (max 100 chars).
        size_bytes: File size in bytes; must be > 0.
        storage_key: Supabase Storage object path without bucket prefix; globally unique.
            Format: {workspace_id}/{project_id}/{artifact_id}/{filename}
        status: Upload lifecycle state — "pending_upload" or "ready".
    """

    __tablename__ = "artifacts"  # type: ignore[assignment]
    __table_args__ = (
        Index("ix_artifacts_workspace_project", "workspace_id", "project_id"),
        Index("ix_artifacts_status", "status"),
        CheckConstraint(
            "status IN ('pending_upload', 'ready')",
            name="ck_artifacts_status",
        ),
        CheckConstraint("size_bytes > 0", name="ck_artifacts_size"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'pending_upload'"),
    )

    def __repr__(self) -> str:
        return f"<Artifact(id={self.id}, filename={self.filename!r}, status={self.status!r})>"


__all__ = ["Artifact"]
