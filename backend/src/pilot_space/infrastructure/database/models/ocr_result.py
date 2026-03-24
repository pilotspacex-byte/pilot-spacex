"""OcrResult -- persisted OCR extraction output, decoupled from attachment TTL."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from pilot_space.infrastructure.database.base import Base


class OcrResultModel(Base):
    """Persisted OCR extraction output.

    Decoupled from chat_attachments TTL -- attachment rows expire after 24 hours
    but OCR text must persist indefinitely for KG ingestion and search.
    The FK uses ON DELETE SET NULL so OCR results survive attachment cleanup.

    Attributes:
        id: Primary key UUID.
        attachment_id: FK to chat_attachments.id; nullable after attachment expiry.
        extracted_text: Full plain-text OCR output (never null).
        tables_json: JSON array of MarkdownTable dicts; nullable.
        confidence: Provider confidence score 0.0-1.0; nullable.
        language: Detected language code (e.g. "zh", "en"); nullable.
        provider_used: Provider slug used for extraction (e.g. "hunyuan_ocr").
        created_at: Row creation timestamp.
    """

    __tablename__ = "ocr_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    # ON DELETE SET NULL so OCR text persists after 24h attachment TTL cleanup
    attachment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_attachments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False)
    tables_json: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    language: Mapped[str | None] = mapped_column(String(32), nullable=True)
    provider_used: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )


__all__ = ["OcrResultModel"]
