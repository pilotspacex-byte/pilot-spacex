"""TranscriptCache SQLAlchemy model.

Caches ElevenLabs STT transcription results keyed by SHA-256 audio hash
to avoid reprocessing identical audio (BYOK cost optimization).

Rows expire after 30 days (TTL enforced at query time + periodic cleanup).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from pilot_space.infrastructure.database.base import Base, TimestampMixin, WorkspaceScopedMixin

# Cache entries older than this are considered expired
TRANSCRIPT_CACHE_TTL_DAYS = 30


class TranscriptCache(Base, TimestampMixin, WorkspaceScopedMixin):
    """Cached transcription result for a given audio file.

    Deduplication is performed using a SHA-256 hash of the audio bytes.
    One record per (workspace_id, audio_hash) pair — unique constraint enforced.
    Rows have a 30-day TTL via `expires_at` column.

    Attributes:
        id: Primary key UUID.
        workspace_id: Workspace that owns this transcript (from WorkspaceScopedMixin).
        audio_hash: SHA-256 hex digest of the uploaded audio bytes (64 chars).
        text: Full transcription text returned by ElevenLabs.
        language_code: ISO 639-1 language code detected or requested.
        duration_seconds: Audio duration returned by ElevenLabs.
        provider: AI provider used for transcription (default "elevenlabs").
        metadata_json: Optional extra data (model used, confidence, etc.).
        expires_at: When this cache entry should be evicted.
    """

    __tablename__ = "transcript_cache"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "audio_hash",
            name="uq_transcript_cache_workspace_audio_hash",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    audio_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        doc="SHA-256 hex digest of uploaded audio bytes",
    )

    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Full transcription text",
    )

    language_code: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        doc="ISO 639-1 language code",
    )

    duration_seconds: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        doc="Audio duration in seconds",
    )

    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default="'elevenlabs'",
        doc="AI provider used for transcription",
    )

    metadata_json: Mapped[dict[str, object] | None] = mapped_column(
        JSON,
        nullable=True,
        doc="Extra metadata (model, confidence, etc.)",
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        doc="TTL expiry — rows past this are stale and eligible for cleanup",
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<TranscriptCache(id={self.id}, "
            f"workspace_id={self.workspace_id}, "
            f"audio_hash={self.audio_hash[:8]}...)>"
        )


__all__ = ["TranscriptCache"]
