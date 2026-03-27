"""Domain schemas for AttachmentManagementService return types.

These schemas are used by AttachmentManagementService and re-exported from
``api/v1/schemas/attachments`` for use in router response models.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class _CamelSchema(BaseModel):
    """Base schema with camelCase alias generation for API compatibility."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
    )


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


class ExtractionMetadata(_CamelSchema):
    """Document extraction metadata."""

    page_count: int | None = None
    language: str | None = None
    extraction_source: str = "none"
    confidence: float | None = None
    word_count: int | None = None
    provider_name: str | None = None


class ExtractionChunk(_CamelSchema):
    """A single chunk of a pre-chunked document."""

    chunk_index: int
    heading: str
    content: str
    char_count: int
    token_count: int
    heading_hierarchy: list[str] = Field(default_factory=list)


class ExtractionResultResponse(_CamelSchema):
    """Full extraction result returned by get_extraction_result."""

    attachment_id: UUID
    extracted_text: str | None = None
    metadata: ExtractionMetadata
    chunks: list[ExtractionChunk] = Field(default_factory=list)
    tables: list[str] = Field(default_factory=list)


__all__ = [
    "ExtractionChunk",
    "ExtractionMetadata",
    "ExtractionResultResponse",
    "IngestResult",
    "SignedUrlResult",
]
