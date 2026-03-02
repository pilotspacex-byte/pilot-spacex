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

import base64
from typing import TYPE_CHECKING, Any

import httpx

from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.chat_attachment import ChatAttachment
    from pilot_space.infrastructure.storage.client import SupabaseStorageClient

logger = get_logger(__name__)

# Character limit for text/code content injected into the context window
_TEXT_TRUNCATE_LIMIT = 50_000

# MIME types that produce image blocks
_IMAGE_MIME_TYPES = frozenset({"image/jpeg", "image/png", "image/webp", "image/gif"})


def _encode_base64(data: bytes) -> str:
    """Return URL-safe base64 string from raw bytes.

    Args:
        data: Raw bytes to encode.

    Returns:
        Base64-encoded string.
    """
    return base64.b64encode(data).decode()


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

    def __init__(self, storage_client: SupabaseStorageClient) -> None:
        """Initialize service.

        Args:
            storage_client: Supabase Storage client for generating signed URLs.
        """
        self._storage = storage_client

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

        Args:
            attachment: ChatAttachment record.

        Returns:
            Claude API content block dict.
        """
        signed_url = await self._storage.get_signed_url(
            bucket="chat-attachments",
            key=attachment.storage_key,
        )

        async with httpx.AsyncClient() as client:
            response = await client.get(signed_url)
            response.raise_for_status()
            data = response.content

        mime_type = attachment.mime_type
        filename = attachment.filename

        logger.debug(
            "attachment_downloaded",
            filename=filename,
            mime_type=mime_type,
            size_bytes=len(data),
        )

        if mime_type == "application/pdf":
            return _build_document_block(data)

        if mime_type in _IMAGE_MIME_TYPES:
            return _build_image_block(data, mime_type)

        return _build_text_block(data, filename)


__all__ = ["AttachmentContentService"]
