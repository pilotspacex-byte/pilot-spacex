"""TDD tests for AttachmentUploadService — local file upload and delete.

Tests written FIRST (TDD red phase). The service at
``pilot_space.application.services.ai.attachment_upload_service``
does NOT exist yet; every test is expected to FAIL until Batch 5 implements it.

Covers:
- Upload validation: MIME whitelist, per-type size limits, empty file guard.
- Upload happy path: correct ``AttachmentUploadResponse`` fields returned.
- Delete: repository + storage both called on success.
- Delete error paths: NOT_FOUND when record absent, FORBIDDEN when wrong owner.

Feature: 020 — Chat Context Attachments
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from pilot_space.api.v1.schemas.attachments import AttachmentUploadResponse
from pilot_space.application.services.ai.attachment_upload_service import (
    AttachmentUploadService,
)

# ---------------------------------------------------------------------------
# Constants mirroring the API contract (rest-api.md §1)
# ---------------------------------------------------------------------------

_PDF_MIME = "application/pdf"
_PNG_MIME = "image/png"
_UNSUPPORTED_MIME = "application/x-executable"

_25_MB = 25 * 1024 * 1024
_10_MB = 10 * 1024 * 1024

_SMALL_PDF = b"%PDF-1.4 fake pdf content"  # well under 25 MB
_SMALL_PNG = b"\x89PNG\r\n\x1a\n fake png content"  # well under 10 MB


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_session() -> AsyncMock:
    """Mock async SQLAlchemy session."""
    return AsyncMock()


@pytest.fixture
def mock_storage_client() -> AsyncMock:
    """Mock Supabase Storage / S3-compatible async storage client."""
    client = AsyncMock()
    client.upload_object.return_value = "storage/path/file.pdf"
    return client


@pytest.fixture
def mock_attachment_repo() -> AsyncMock:
    """Mock attachment repository."""
    return AsyncMock()


@pytest.fixture
def service(
    mock_session: AsyncMock,
    mock_storage_client: AsyncMock,
    mock_attachment_repo: AsyncMock,
) -> AttachmentUploadService:
    """Create AttachmentUploadService with all dependencies mocked."""
    return AttachmentUploadService(
        session=mock_session,
        storage_client=mock_storage_client,
        attachment_repo=mock_attachment_repo,
    )


def _make_upload_response(**overrides: Any) -> AttachmentUploadResponse:
    """Build a valid AttachmentUploadResponse for use in mock return values."""
    defaults: dict[str, Any] = {
        "attachment_id": uuid.uuid4(),
        "filename": "file.pdf",
        "mime_type": _PDF_MIME,
        "size_bytes": len(_SMALL_PDF),
        "source": "local",
        "expires_at": datetime(2099, 1, 1, tzinfo=UTC),
    }
    defaults.update(overrides)
    return AttachmentUploadResponse(**defaults)


def _make_attachment_record(
    attachment_id: uuid.UUID,
    owner_id: uuid.UUID,
    storage_path: str = "attachments/file.pdf",
) -> MagicMock:
    """Create a fake ORM attachment record returned by the repository."""
    record = MagicMock()
    record.id = attachment_id
    record.owner_id = owner_id
    record.storage_path = storage_path
    return record


# ===========================================================================
# TestAttachmentUploadValidation
# ===========================================================================


class TestAttachmentUploadValidation:
    """Validate MIME type whitelist and per-type size limits on upload()."""

    @pytest.mark.asyncio
    async def test_upload_valid_pdf_returns_response(
        self,
        service: AttachmentUploadService,
        mock_attachment_repo: AsyncMock,
    ) -> None:
        """Valid PDF bytes under 25 MB return a well-formed AttachmentUploadResponse."""
        workspace_id = uuid.uuid4()
        user_id = uuid.uuid4()
        expected = _make_upload_response(
            filename="spec.pdf",
            mime_type=_PDF_MIME,
            size_bytes=len(_SMALL_PDF),
        )
        mock_attachment_repo.create.return_value = expected

        result = await service.upload(
            file_data=_SMALL_PDF,
            filename="spec.pdf",
            content_type=_PDF_MIME,
            workspace_id=workspace_id,
            user_id=user_id,
        )

        assert isinstance(result, AttachmentUploadResponse)
        assert result.mime_type == _PDF_MIME
        assert result.size_bytes == len(_SMALL_PDF)
        assert result.source == "local"
        assert result.filename == "spec.pdf"
        assert result.attachment_id is not None
        assert result.expires_at is not None

    @pytest.mark.asyncio
    async def test_upload_valid_png_returns_response(
        self,
        service: AttachmentUploadService,
        mock_attachment_repo: AsyncMock,
    ) -> None:
        """Valid PNG bytes under 10 MB return a well-formed AttachmentUploadResponse."""
        workspace_id = uuid.uuid4()
        user_id = uuid.uuid4()
        expected = _make_upload_response(
            filename="screenshot.png",
            mime_type=_PNG_MIME,
            size_bytes=len(_SMALL_PNG),
        )
        mock_attachment_repo.create.return_value = expected

        result = await service.upload(
            file_data=_SMALL_PNG,
            filename="screenshot.png",
            content_type=_PNG_MIME,
            workspace_id=workspace_id,
            user_id=user_id,
        )

        assert isinstance(result, AttachmentUploadResponse)
        assert result.mime_type == _PNG_MIME
        assert result.size_bytes == len(_SMALL_PNG)
        assert result.source == "local"

    @pytest.mark.asyncio
    async def test_upload_rejects_unsupported_mime_type(
        self,
        service: AttachmentUploadService,
    ) -> None:
        """MIME type not in whitelist raises ValueError with UNSUPPORTED_FILE_TYPE."""
        with pytest.raises((ValueError, Exception), match="UNSUPPORTED_FILE_TYPE"):
            await service.upload(
                file_data=b"\x7fELF binary content",
                filename="malware.exe",
                content_type=_UNSUPPORTED_MIME,
                workspace_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
            )

    @pytest.mark.asyncio
    async def test_upload_rejects_pdf_exceeding_25mb(
        self,
        service: AttachmentUploadService,
    ) -> None:
        """PDF exceeding 25 MB raises ValueError with FILE_TOO_LARGE."""
        oversized_pdf = b"x" * (_25_MB + 1)

        with pytest.raises((ValueError, Exception), match="FILE_TOO_LARGE"):
            await service.upload(
                file_data=oversized_pdf,
                filename="huge.pdf",
                content_type=_PDF_MIME,
                workspace_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
            )

    @pytest.mark.asyncio
    async def test_upload_rejects_image_exceeding_10mb(
        self,
        service: AttachmentUploadService,
    ) -> None:
        """Image exceeding 10 MB raises ValueError with FILE_TOO_LARGE."""
        oversized_png = b"x" * (_10_MB + 1)

        with pytest.raises((ValueError, Exception), match="FILE_TOO_LARGE"):
            await service.upload(
                file_data=oversized_png,
                filename="huge.png",
                content_type=_PNG_MIME,
                workspace_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
            )

    @pytest.mark.asyncio
    async def test_upload_rejects_empty_file(
        self,
        service: AttachmentUploadService,
    ) -> None:
        """Zero-byte file raises ValueError with EMPTY_FILE."""
        with pytest.raises((ValueError, Exception), match="EMPTY_FILE"):
            await service.upload(
                file_data=b"",
                filename="empty.pdf",
                content_type=_PDF_MIME,
                workspace_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
            )


# ===========================================================================
# TestAttachmentDelete
# ===========================================================================


class TestAttachmentDelete:
    """Validate delete() orchestration: repo + storage calls and error paths."""

    @pytest.mark.asyncio
    async def test_delete_attachment_calls_repo_and_storage(
        self,
        service: AttachmentUploadService,
        mock_attachment_repo: AsyncMock,
        mock_storage_client: AsyncMock,
    ) -> None:
        """Successful delete must call both attachment_repo.delete() and storage_client.delete_object()."""
        attachment_id = uuid.uuid4()
        user_id = uuid.uuid4()
        record = _make_attachment_record(
            attachment_id=attachment_id,
            owner_id=user_id,
            storage_path="attachments/spec.pdf",
        )
        mock_attachment_repo.get_by_id.return_value = record
        mock_attachment_repo.delete.return_value = None
        mock_storage_client.delete_object.return_value = None

        await service.delete(attachment_id=attachment_id, user_id=user_id)

        mock_attachment_repo.delete.assert_called_once()
        mock_storage_client.delete_object.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_attachment_not_found_raises(
        self,
        service: AttachmentUploadService,
        mock_attachment_repo: AsyncMock,
    ) -> None:
        """When repo returns None the service raises with NOT_FOUND."""
        mock_attachment_repo.get_by_id.return_value = None

        with pytest.raises((ValueError, Exception), match="NOT_FOUND"):
            await service.delete(
                attachment_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
            )

    @pytest.mark.asyncio
    async def test_delete_attachment_wrong_owner_raises(
        self,
        service: AttachmentUploadService,
        mock_attachment_repo: AsyncMock,
    ) -> None:
        """When authenticated user differs from attachment owner, raises PermissionError with FORBIDDEN."""
        attachment_id = uuid.uuid4()
        owner_id = uuid.uuid4()
        different_user_id = uuid.uuid4()

        record = _make_attachment_record(
            attachment_id=attachment_id,
            owner_id=owner_id,
        )
        mock_attachment_repo.get_by_id.return_value = record

        with pytest.raises((PermissionError, Exception), match="FORBIDDEN"):
            await service.delete(
                attachment_id=attachment_id,
                user_id=different_user_id,
            )
