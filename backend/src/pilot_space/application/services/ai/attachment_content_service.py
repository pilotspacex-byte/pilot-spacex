"""Attachment content service for converting stored files to Claude content blocks.

Downloads attachment bytes from Supabase Storage via signed URLs and
converts them into the appropriate Claude API content block format:
- PDF → document block (base64)
- Image → image block (base64)
- Text/code → text block (UTF-8, truncated to 50,000 chars)

Feature: 020 — Chat Context Attachments
Source: FR-007, US-1
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
from typing import TYPE_CHECKING, Any

import httpx

from pilot_space.application.services.document.office_extraction_service import (
    OfficeExtractionService,
)
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.application.services.ai.ocr_service import OcrService
    from pilot_space.infrastructure.database.models.chat_attachment import ChatAttachment
    from pilot_space.infrastructure.storage.client import SupabaseStorageClient

logger = get_logger(__name__)

# Character limit for text/code content injected into the context window
_TEXT_TRUNCATE_LIMIT = 50_000

# MIME types that produce image blocks
_IMAGE_MIME_TYPES = frozenset({"image/jpeg", "image/png", "image/webp", "image/gif"})

# MIME types for Office documents — converted to markdown via _extract_office_to_markdown
_OFFICE_MIME_TYPES = frozenset(
    {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # .pptx
    }
)


def _encode_base64(data: bytes) -> str:
    """Return URL-safe base64 string from raw bytes.

    Args:
        data: Raw bytes to encode.

    Returns:
        Base64-encoded string.
    """
    return base64.b64encode(data).decode()


def _extract_pdf_text(data: bytes) -> str:
    """Extract embedded text from a PDF using pypdf.

    Returns extracted text, or empty string if extraction fails or yields
    no meaningful content. Used to make PDF content available to non-Claude
    providers (Ollama, OpenAI-compat) that don't support document blocks.
    """
    try:
        import io

        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        pages: list[str] = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if text.strip():
                pages.append(f"--- Page {i + 1} ---\n{text}")
        return "\n\n".join(pages)
    except Exception:
        return ""


def _build_document_block(data: bytes) -> dict[str, Any]:
    """Build a Claude document content block from PDF bytes.

    Args:
        data: PDF file bytes.

    Returns:
        Claude API document block dict.
    """
    return {
        "type": "document",
        "source": {
            "type": "base64",
            "media_type": "application/pdf",
            "data": _encode_base64(data),
        },
    }


def _build_image_block(data: bytes, mime_type: str) -> dict[str, Any]:
    """Build a Claude image content block from image bytes.

    Args:
        data: Image file bytes.
        mime_type: MIME type of the image (e.g. "image/png").

    Returns:
        Claude API image block dict.
    """
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": mime_type,
            "data": _encode_base64(data),
        },
    }


def _build_text_block(data: bytes, filename: str) -> dict[str, Any]:
    """Build a Claude text content block from text/code bytes.

    Content is decoded as UTF-8 and truncated to 50,000 characters.
    A ``[Truncated]`` suffix is appended when truncation occurs.

    Args:
        data: Text/code file bytes.
        filename: Original filename used as a header in the block.

    Returns:
        Claude API text block dict.
    """
    content = data.decode("utf-8", errors="replace")
    if len(content) > _TEXT_TRUNCATE_LIMIT:
        content = content[:_TEXT_TRUNCATE_LIMIT] + "[Truncated]"
    text = f"{filename}\n\n{content}"
    return {"type": "text", "text": text}


class AttachmentContentService:
    """Service for converting chat attachments into Claude API content blocks.

    Fetches each attachment from Supabase Storage via a short-lived signed URL,
    downloads the bytes over HTTPS, and converts to the appropriate Claude
    content block format based on MIME type.

    Example:
        service = AttachmentContentService(storage_client=storage_client)
        blocks = await service.build_content_blocks(attachments)
        # Inject blocks into the user message content array
    """

    def __init__(
        self,
        storage_client: SupabaseStorageClient,
        office_extraction: OfficeExtractionService,
        ocr_service: OcrService | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        """Initialize service.

        Args:
            storage_client: Supabase Storage client for generating signed URLs.
            office_extraction: OfficeExtractionService for DOCX/XLSX/PPTX conversion.
            ocr_service: Optional OcrService for scanned PDF / image OCR extraction.
            session: Optional AsyncSession required when ocr_service is provided.
        """
        self._storage = storage_client
        self._office_extraction = office_extraction
        self._ocr_service = ocr_service
        self._session = session

    async def build_content_blocks(
        self,
        attachments: list[ChatAttachment],
    ) -> list[dict[str, Any]]:
        """Convert a list of attachments to Claude API content blocks.

        For each attachment:
        1. Generates a signed URL via the storage client.
        2. Downloads the bytes via httpx.AsyncClient.
        3. Converts to the appropriate Claude content block format.

        Returns blocks in the same order as the input list.

        Args:
            attachments: List of ChatAttachment records to convert.

        Returns:
            List of Claude API content block dicts in input order.
        """
        if not attachments:
            return []

        blocks: list[dict[str, Any]] = []

        for attachment in attachments:
            block = await self._convert_attachment(attachment)
            blocks.append(block)

        return blocks

    async def _convert_attachment(
        self,
        attachment: ChatAttachment,
    ) -> dict[str, Any]:
        """Download a single attachment and convert to a content block.

        For Office MIME types, checks extracted_text cache before downloading
        from storage. Cache hit skips the storage download entirely.

        Args:
            attachment: ChatAttachment record.

        Returns:
            Claude API content block dict.
        """
        mime_type = attachment.mime_type
        filename = attachment.filename

        # OFFICE-04: Cache hit — use previously extracted text without re-downloading
        if mime_type in _OFFICE_MIME_TYPES and attachment.extracted_text:
            logger.debug("office_extraction_cache_hit", filename=filename)
            return _build_text_block(attachment.extracted_text.encode(), filename)

        signed_url = await self._storage.get_signed_url(
            bucket="chat-attachments",
            key=attachment.storage_key,
        )

        async with httpx.AsyncClient() as client:
            response = await client.get(signed_url)
            response.raise_for_status()
            data = response.content

        logger.debug(
            "attachment_downloaded",
            filename=filename,
            mime_type=mime_type,
            size_bytes=len(data),
        )

        # PIPE-05 / OFFICE-04: Office extraction via injected OfficeExtractionService
        if mime_type in _OFFICE_MIME_TYPES:
            try:
                result = await asyncio.to_thread(
                    self._office_extraction.extract, data, mime_type, filename
                )
                # Cache for future calls (best-effort — don't fail if attachment is detached)
                with contextlib.suppress(Exception):
                    attachment.extracted_text = result.text
            except Exception:
                logger.warning(
                    "office_extraction_failed",
                    filename=filename,
                    mime_type=mime_type,
                )
                return _build_text_block(f"[{filename}: extraction failed]".encode(), filename)
            return _build_text_block(result.text.encode(), filename)

        if mime_type == "application/pdf":
            return await self._convert_pdf(data, filename, attachment)

        if mime_type in _IMAGE_MIME_TYPES:
            return await self._convert_image(data, mime_type, filename, attachment)

        return _build_text_block(data, filename)

    async def _convert_pdf(
        self,
        data: bytes,
        filename: str,
        attachment: ChatAttachment,
    ) -> dict[str, Any]:
        """Convert PDF bytes to a content block.

        OCR-01: Runs OCR on scanned PDFs (< 100 chars of embedded text).
        For non-scanned PDFs, extracts text via pypdf so the content works
        with any LLM provider (Ollama, OpenAI-compat) — not just Claude.
        """
        if self._ocr_service and self._session:
            from pilot_space.application.services.ai.ocr_service import is_scanned_pdf

            if await is_scanned_pdf(data):
                ocr_result = await self._ocr_service.extract_with_fallback(
                    data,
                    "application/pdf",
                    attachment.workspace_id,
                    attachment.id,
                    self._session,
                )
                if ocr_result.text:
                    return _build_text_block(ocr_result.text.encode(), filename)

        # Extract text from PDF so it works with any LLM provider
        extracted = _extract_pdf_text(data)
        if extracted:
            return _build_text_block(extracted.encode(), filename)

        # Last resort: raw document block (Claude-only, may fail on other providers)
        return _build_document_block(data)

    async def _convert_image(
        self,
        data: bytes,
        mime_type: str,
        filename: str,
        attachment: ChatAttachment,
    ) -> dict[str, Any]:
        """Convert image bytes to a content block.

        Attempts OCR text extraction first (when configured) so that
        text-only LLM providers (Ollama, open-source models) can still
        process image uploads. Falls back to a native image block for
        vision-capable models (Claude, GPT-4o).
        """
        if self._ocr_service and self._session:
            try:
                ocr_result = await self._ocr_service.extract_with_fallback(
                    data,
                    mime_type,
                    attachment.workspace_id,
                    attachment.id,
                    self._session,
                )
                if ocr_result.text:
                    return _build_text_block(ocr_result.text.encode(), filename)
            except Exception:
                logger.debug("image_ocr_fallback_failed", filename=filename, exc_info=True)

        # Native image block — works with vision-capable models
        return _build_image_block(data, mime_type)


__all__ = ["AttachmentContentService"]
