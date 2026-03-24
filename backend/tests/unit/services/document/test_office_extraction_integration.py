"""Integration-style unit tests for Office extraction wiring.

Tests verify that:
- Office MIME types are in the upload allowlist (OFFICE-04)
- AttachmentContentService calls OfficeExtractionService for Office MIME types
- Cache hit path skips storage download

Feature: Phase 41 — Office Document Extraction
Requirements: OFFICE-04
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pilot_space.application.services.ai.attachment_content_service import (
    AttachmentContentService,
)
from pilot_space.application.services.ai.attachment_upload_service import (
    ATTACHMENT_SIZE_LIMITS,
)
from pilot_space.application.services.document.office_extraction_service import (
    ExtractionResult,
    OfficeExtractionService,
)
from pilot_space.infrastructure.database.models.chat_attachment import ChatAttachment

_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


def make_office_attachment(mime_type: str, extracted_text: str | None = None) -> ChatAttachment:
    """Build an in-memory ChatAttachment for the given Office MIME type."""
    a = ChatAttachment.__new__(ChatAttachment)
    a.id = uuid.uuid4()
    a.workspace_id = uuid.uuid4()
    a.user_id = uuid.uuid4()
    a.session_id = None
    a.filename = "test.docx"
    a.mime_type = mime_type
    a.size_bytes = 1024
    a.storage_key = f"chat-attachments/ws/user/{uuid.uuid4()}/test.docx"
    a.source = "local"
    a.drive_file_id = None
    a.extracted_text = extracted_text
    a.expires_at = datetime(2099, 1, 1, tzinfo=UTC)
    return a


class TestOfficeAllowlist:
    """OFFICE-04: Office MIME types must be in the upload allowlist."""

    def test_docx_in_allowlist(self) -> None:
        assert _DOCX_MIME in ATTACHMENT_SIZE_LIMITS

    def test_xlsx_in_allowlist(self) -> None:
        assert _XLSX_MIME in ATTACHMENT_SIZE_LIMITS

    def test_pptx_in_allowlist(self) -> None:
        assert _PPTX_MIME in ATTACHMENT_SIZE_LIMITS

    def test_office_limit_is_25mb(self) -> None:
        _25_MB = 25 * 1024 * 1024
        assert ATTACHMENT_SIZE_LIMITS[_DOCX_MIME] == _25_MB
        assert ATTACHMENT_SIZE_LIMITS[_XLSX_MIME] == _25_MB
        assert ATTACHMENT_SIZE_LIMITS[_PPTX_MIME] == _25_MB


class TestAttachmentContentServiceOfficeIntegration:
    """AttachmentContentService calls OfficeExtractionService for Office MIME types."""

    @pytest.fixture
    def mock_storage(self) -> MagicMock:
        client = MagicMock()
        client.get_signed_url = AsyncMock(return_value="https://storage.example.com/file")
        return client

    @pytest.fixture
    def mock_office_extraction(self) -> MagicMock:
        svc = MagicMock(spec=OfficeExtractionService)
        svc.extract.return_value = ExtractionResult(
            text="# Extracted Heading\n\nExtracted paragraph.",
            metadata={"word_count": 4},
        )
        return svc

    @pytest.fixture
    def service(
        self,
        mock_storage: MagicMock,
        mock_office_extraction: MagicMock,
    ) -> AttachmentContentService:
        return AttachmentContentService(
            storage_client=mock_storage,
            office_extraction=mock_office_extraction,
        )

    def _patch_httpx(self, content: bytes) -> MagicMock:
        response = MagicMock()
        response.content = content
        response.raise_for_status = MagicMock()
        http_client = MagicMock()
        http_client.get = AsyncMock(return_value=response)
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=http_client)
        cm.__aexit__ = AsyncMock(return_value=False)
        return cm

    async def test_docx_attachment_calls_extraction_service(
        self,
        service: AttachmentContentService,
        mock_office_extraction: MagicMock,
    ) -> None:
        attachment = make_office_attachment(_DOCX_MIME)
        docx_bytes = b"PK fake docx bytes"

        with patch(
            "pilot_space.application.services.ai.attachment_content_service.httpx.AsyncClient",
            return_value=self._patch_httpx(docx_bytes),
        ):
            blocks = await service.build_content_blocks([attachment])

        mock_office_extraction.extract.assert_called_once_with(
            docx_bytes, _DOCX_MIME, attachment.filename
        )
        assert len(blocks) == 1
        assert blocks[0]["type"] == "text"
        assert "Extracted" in blocks[0]["text"]

    async def test_office_cache_hit_skips_storage_download(
        self,
        service: AttachmentContentService,
        mock_office_extraction: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        """When extracted_text is already set, no storage download occurs."""
        cached_text = "# Cached Heading\n\nCached content."
        attachment = make_office_attachment(_DOCX_MIME, extracted_text=cached_text)

        blocks = await service.build_content_blocks([attachment])

        # Storage should NOT be called (cache hit)
        mock_storage.get_signed_url.assert_not_called()
        # Extraction service should NOT be called (cache hit)
        mock_office_extraction.extract.assert_not_called()
        assert len(blocks) == 1
        assert blocks[0]["type"] == "text"
        assert "Cached" in blocks[0]["text"]
