"""Domain schemas for AttachmentManagementService return types.

ExtractionResultResponse is already defined in ``api/v1/schemas/attachments``
and is returned directly from ``get_extraction_result``.  This module adds the
simpler dict-returning methods: signed URL lookup and document ingest.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SignedUrlResult(BaseModel):
    """Signed download URL with expiry metadata."""

    model_config = ConfigDict(frozen=True)

    url: str
    expires_in: int


class IngestResult(BaseModel):
    """Document ingest confirmation after enqueue."""

    model_config = ConfigDict(frozen=True)

    status: str
    attachment_id: UUID


__all__ = [
    "IngestResult",
    "SignedUrlResult",
]
