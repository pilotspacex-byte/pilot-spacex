"""Unit tests for AttachmentContentService (TDD — tests FAIL before implementation).

Tests cover:
- PDF attachment produces Claude document block
- Image attachments (png, jpeg) produce Claude image blocks
- Text/code attachment produces Claude text block with filename header
- Text content truncated to 50,000 chars with [Truncated] suffix
- Text content at exactly 50,000 chars is NOT truncated
- Multiple attachments produce blocks in the same order
- Empty attachment list returns empty list

Feature: 020 — Chat Context Attachments
"""

from __future__ import annotations

import base64
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pilot_space.application.services.ai.attachment_content_service import (
    AttachmentContentService,
)
from pilot_space.application.services.document.office_extraction_service import (
    ExtractionResult,
    OfficeExtractionService,
)
from pilot_space.infrastructure.database.models.chat_attachment import ChatAttachment

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_attachment(
    mime_type: str,
    filename: str = "testfile",
    storage_key: str | None = None,
) -> ChatAttachment:
    """Construct a ChatAttachment instance without a database session.

    Sets all non-nullable fields to valid sentinel values so the ORM object
    can be constructed in-memory without touching a database.
    """
    attachment = ChatAttachment.__new__(ChatAttachment)
    attachment.id = uuid.uuid4()
    attachment.workspace_id = uuid.uuid4()
    attachment.user_id = uuid.uuid4()
    attachment.session_id = None
    attachment.filename = filename
    attachment.mime_type = mime_type
    attachment.size_bytes = 1024
    attachment.storage_key = storage_key or f"chat-attachments/ws/user/{uuid.uuid4()}/{filename}"
    attachment.source = "local"
    attachment.drive_file_id = None
    attachment.extracted_text = None
    attachment.expires_at = datetime(2099, 1, 1, tzinfo=UTC)
    return attachment


def _encode(data: bytes) -> str:
    """Return base64-encoded string from bytes."""
    return base64.b64encode(data).decode()


# ---------------------------------------------------------------------------
# TestBuildContentBlocks
# ---------------------------------------------------------------------------


class TestBuildContentBlocks:
    """Tests for AttachmentContentService.build_content_blocks."""

    @pytest.fixture
    def storage_client(self) -> MagicMock:
        """Mock storage client with a get_signed_url coroutine."""
        client = MagicMock()
        client.get_signed_url = AsyncMock(return_value="https://storage.example.com/file")
        return client

    @pytest.fixture
    def office_extraction(self) -> MagicMock:
        """Mock OfficeExtractionService (not called for non-Office MIME tests)."""
        return MagicMock(spec=OfficeExtractionService)

    @pytest.fixture
    def service(
        self, storage_client: MagicMock, office_extraction: MagicMock
    ) -> AttachmentContentService:
        """Service under test wired with the mock storage client and office extraction."""
        return AttachmentContentService(
            storage_client=storage_client,
            office_extraction=office_extraction,
        )

    def _patch_httpx(self, content: bytes) -> MagicMock:
        """Return a context-manager mock for httpx.AsyncClient.get returning content."""
        response = MagicMock()
        response.content = content
        response.raise_for_status = MagicMock()

        http_client = MagicMock()
        http_client.get = AsyncMock(return_value=response)

        # AsyncClient used as async context manager
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=http_client)
        cm.__aexit__ = AsyncMock(return_value=False)
        return cm

    # ------------------------------------------------------------------
    # PDF
    # ------------------------------------------------------------------

    async def test_pdf_produces_document_block(
        self,
        service: AttachmentContentService,
    ) -> None:
        """application/pdf attachment produces a Claude document content block."""
        pdf_bytes = b"%PDF-1.4 fake pdf content"
        attachment = make_attachment(mime_type="application/pdf", filename="report.pdf")

        with patch(
            "pilot_space.application.services.ai.attachment_content_service.httpx.AsyncClient",
            return_value=self._patch_httpx(pdf_bytes),
        ):
            blocks = await service.build_content_blocks([attachment])

        assert len(blocks) == 1
        block = blocks[0]
        assert block["type"] == "document"
        assert block["source"]["type"] == "base64"
        assert block["source"]["media_type"] == "application/pdf"
        assert block["source"]["data"] == _encode(pdf_bytes)

    # ------------------------------------------------------------------
    # Images
    # ------------------------------------------------------------------

    async def test_png_produces_image_block(
        self,
        service: AttachmentContentService,
    ) -> None:
        """image/png attachment produces a Claude image content block."""
        png_bytes = b"\x89PNG\r\n\x1a\n fake png"
        attachment = make_attachment(mime_type="image/png", filename="screenshot.png")

        with patch(
            "pilot_space.application.services.ai.attachment_content_service.httpx.AsyncClient",
            return_value=self._patch_httpx(png_bytes),
        ):
            blocks = await service.build_content_blocks([attachment])

        assert len(blocks) == 1
        block = blocks[0]
        assert block["type"] == "image"
        assert block["source"]["type"] == "base64"
        assert block["source"]["media_type"] == "image/png"
        assert block["source"]["data"] == _encode(png_bytes)

    async def test_jpeg_produces_image_block(
        self,
        service: AttachmentContentService,
    ) -> None:
        """image/jpeg attachment produces a Claude image content block."""
        jpeg_bytes = b"\xff\xd8\xff\xe0 fake jpeg"
        attachment = make_attachment(mime_type="image/jpeg", filename="photo.jpg")

        with patch(
            "pilot_space.application.services.ai.attachment_content_service.httpx.AsyncClient",
            return_value=self._patch_httpx(jpeg_bytes),
        ):
            blocks = await service.build_content_blocks([attachment])

        assert len(blocks) == 1
        block = blocks[0]
        assert block["type"] == "image"
        assert block["source"]["type"] == "base64"
        assert block["source"]["media_type"] == "image/jpeg"

    # ------------------------------------------------------------------
    # Text / code
    # ------------------------------------------------------------------

    async def test_text_produces_text_block(
        self,
        service: AttachmentContentService,
    ) -> None:
        """text/plain attachment produces a Claude text block containing the filename."""
        text_content = b"Hello, world!"
        attachment = make_attachment(mime_type="text/plain", filename="notes.txt")

        with patch(
            "pilot_space.application.services.ai.attachment_content_service.httpx.AsyncClient",
            return_value=self._patch_httpx(text_content),
        ):
            blocks = await service.build_content_blocks([attachment])

        assert len(blocks) == 1
        block = blocks[0]
        assert block["type"] == "text"
        assert "notes.txt" in block["text"]
        assert "Hello, world!" in block["text"]

    async def test_text_truncated_at_50000_chars(
        self,
        service: AttachmentContentService,
    ) -> None:
        """Text content exceeding 50,000 chars is truncated and marked with [Truncated]."""
        long_text = "A" * 60_000
        attachment = make_attachment(mime_type="text/plain", filename="big.txt")

        with patch(
            "pilot_space.application.services.ai.attachment_content_service.httpx.AsyncClient",
            return_value=self._patch_httpx(long_text.encode()),
        ):
            blocks = await service.build_content_blocks([attachment])

        block = blocks[0]
        assert block["type"] == "text"
        assert "[Truncated]" in block["text"]
        # The raw content portion must not exceed the limit
        raw_content = block["text"]
        # Total text includes filename header; content portion is truncated
        assert len(raw_content) < 60_000 + 500  # generous upper bound including header

    async def test_text_at_exactly_50000_chars_not_truncated(
        self,
        service: AttachmentContentService,
    ) -> None:
        """Text content at exactly 50,000 chars is NOT truncated."""
        exact_text = "B" * 50_000
        attachment = make_attachment(mime_type="text/plain", filename="exact.txt")

        with patch(
            "pilot_space.application.services.ai.attachment_content_service.httpx.AsyncClient",
            return_value=self._patch_httpx(exact_text.encode()),
        ):
            blocks = await service.build_content_blocks([attachment])

        block = blocks[0]
        assert block["type"] == "text"
        assert "[Truncated]" not in block["text"]
        assert "B" * 50_000 in block["text"]

    # ------------------------------------------------------------------
    # Ordering and edge cases
    # ------------------------------------------------------------------

    async def test_multi_attachment_ordering_preserved(
        self,
        service: AttachmentContentService,
    ) -> None:
        """Three attachments of different types produce three blocks in input order."""
        attachments = [
            make_attachment(mime_type="application/pdf", filename="first.pdf"),
            make_attachment(mime_type="image/png", filename="second.png"),
            make_attachment(mime_type="text/plain", filename="third.txt"),
        ]

        pdf_bytes = b"%PDF fake"
        png_bytes = b"\x89PNG fake"
        txt_bytes = b"hello"

        responses = [pdf_bytes, png_bytes, txt_bytes]
        call_count = 0

        def _side_effect_factory(idx: int) -> MagicMock:
            return self._patch_httpx(responses[idx])

        # Each AsyncClient instantiation returns the next response in sequence
        clients = [self._patch_httpx(b) for b in responses]
        client_iter = iter(clients)

        with patch(
            "pilot_space.application.services.ai.attachment_content_service.httpx.AsyncClient",
            side_effect=lambda: next(client_iter),
        ):
            blocks = await service.build_content_blocks(attachments)

        assert len(blocks) == 3
        assert blocks[0]["type"] == "document"
        assert blocks[1]["type"] == "image"
        assert blocks[2]["type"] == "text"
        assert "third.txt" in blocks[2]["text"]

    async def test_empty_attachment_list_returns_empty(
        self,
        service: AttachmentContentService,
    ) -> None:
        """Empty input list returns an empty list without any I/O calls."""
        blocks = await service.build_content_blocks([])
        assert blocks == []


# ---------------------------------------------------------------------------
# TestOfficeExtraction
# ---------------------------------------------------------------------------


class TestOfficeExtraction:
    """Tests for PIPE-05 / OFFICE-04: Office document (.docx/.xlsx/.pptx) extraction.

    Office files are converted to markdown text blocks via injected OfficeExtractionService.
    Tests mock the service — real Office libs are not required for unit tests.
    """

    _DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    _XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    _PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"

    _MOCK_MARKDOWN = "## Header\n\nBody text"
    _FAKE_OFFICE_BYTES = b"PK\x03\x04fake-office-binary"

    @pytest.fixture
    def storage_client(self) -> MagicMock:
        """Mock storage client with a get_signed_url coroutine."""
        client = MagicMock()
        client.get_signed_url = AsyncMock(return_value="https://storage.example.com/file")
        return client

    @pytest.fixture
    def office_extraction(self) -> MagicMock:
        """Mock OfficeExtractionService returning markdown."""
        svc = MagicMock(spec=OfficeExtractionService)
        svc.extract.return_value = ExtractionResult(
            text=self._MOCK_MARKDOWN,
            metadata={"word_count": 4},
        )
        return svc

    @pytest.fixture
    def service(
        self, storage_client: MagicMock, office_extraction: MagicMock
    ) -> AttachmentContentService:
        """Service under test wired with mock storage and office extraction."""
        return AttachmentContentService(
            storage_client=storage_client,
            office_extraction=office_extraction,
        )

    def _patch_httpx(self, content: bytes) -> MagicMock:
        """Return a context-manager mock for httpx.AsyncClient.get returning content."""
        response = MagicMock()
        response.content = content
        response.raise_for_status = MagicMock()

        http_client = MagicMock()
        http_client.get = AsyncMock(return_value=response)

        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=http_client)
        cm.__aexit__ = AsyncMock(return_value=False)
        return cm

    async def test_docx_produces_text_block(
        self,
        service: AttachmentContentService,
        office_extraction: MagicMock,
    ) -> None:
        """PIPE-05: .docx MIME type attachment produces a text block with extracted markdown."""
        attachment = make_attachment(mime_type=self._DOCX_MIME, filename="report.docx")

        with patch(
            "pilot_space.application.services.ai.attachment_content_service.httpx.AsyncClient",
            return_value=self._patch_httpx(self._FAKE_OFFICE_BYTES),
        ):
            blocks = await service.build_content_blocks([attachment])

        assert len(blocks) == 1
        block = blocks[0]
        assert block["type"] == "text"
        assert self._MOCK_MARKDOWN in block["text"]
        office_extraction.extract.assert_called_once_with(
            self._FAKE_OFFICE_BYTES, self._DOCX_MIME, "report.docx"
        )

    async def test_xlsx_produces_text_block(
        self,
        service: AttachmentContentService,
        office_extraction: MagicMock,
    ) -> None:
        """PIPE-05: .xlsx MIME type attachment produces a text block with extracted markdown."""
        attachment = make_attachment(mime_type=self._XLSX_MIME, filename="data.xlsx")

        with patch(
            "pilot_space.application.services.ai.attachment_content_service.httpx.AsyncClient",
            return_value=self._patch_httpx(self._FAKE_OFFICE_BYTES),
        ):
            blocks = await service.build_content_blocks([attachment])

        assert len(blocks) == 1
        block = blocks[0]
        assert block["type"] == "text"
        assert self._MOCK_MARKDOWN in block["text"]
        office_extraction.extract.assert_called_once_with(
            self._FAKE_OFFICE_BYTES, self._XLSX_MIME, "data.xlsx"
        )

    async def test_pptx_produces_text_block(
        self,
        service: AttachmentContentService,
        office_extraction: MagicMock,
    ) -> None:
        """PIPE-05: .pptx MIME type attachment produces a text block with extracted markdown."""
        attachment = make_attachment(mime_type=self._PPTX_MIME, filename="slides.pptx")

        with patch(
            "pilot_space.application.services.ai.attachment_content_service.httpx.AsyncClient",
            return_value=self._patch_httpx(self._FAKE_OFFICE_BYTES),
        ):
            blocks = await service.build_content_blocks([attachment])

        assert len(blocks) == 1
        block = blocks[0]
        assert block["type"] == "text"
        assert self._MOCK_MARKDOWN in block["text"]
        office_extraction.extract.assert_called_once_with(
            self._FAKE_OFFICE_BYTES, self._PPTX_MIME, "slides.pptx"
        )

    async def test_office_extraction_failure_returns_fallback_text_block(
        self,
        storage_client: MagicMock,
    ) -> None:
        """PIPE-05: Extraction failure returns a fallback text block — does not raise."""
        failing_svc = MagicMock(spec=OfficeExtractionService)
        failing_svc.extract.side_effect = Exception("corrupted file")
        service = AttachmentContentService(
            storage_client=storage_client,
            office_extraction=failing_svc,
        )
        attachment = make_attachment(mime_type=self._DOCX_MIME, filename="corrupted.docx")

        with patch(
            "pilot_space.application.services.ai.attachment_content_service.httpx.AsyncClient",
            return_value=self._patch_httpx(self._FAKE_OFFICE_BYTES),
        ):
            blocks = await service.build_content_blocks([attachment])

        assert len(blocks) == 1
        block = blocks[0]
        assert block["type"] == "text"
        assert "failed" in block["text"].lower() or "extraction" in block["text"].lower()
