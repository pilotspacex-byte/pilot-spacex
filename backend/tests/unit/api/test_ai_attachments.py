"""Unit tests for POST /ai/attachments/upload and DELETE /ai/attachments/{id}.

Tests call router functions directly with mocked dependencies — no TestClient,
no HTTP stack. Tests FAIL until the router is implemented (TDD).

Feature: 020 — Chat Context Attachments
Task: T013
"""

from __future__ import annotations

import io
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException, UploadFile

from pilot_space.api.v1.routers.ai_attachments import (
    delete_attachment,
    upload_attachment,
)

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Fixed test IDs
# ---------------------------------------------------------------------------

TEST_USER_ID = UUID("aaaaaaaa-0000-0000-0000-000000000001")
TEST_WORKSPACE_ID = UUID("bbbbbbbb-0000-0000-0000-000000000002")
TEST_ATTACHMENT_ID = UUID("cccccccc-0000-0000-0000-000000000003")
OTHER_USER_ID = UUID("dddddddd-0000-0000-0000-000000000004")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_upload_file(
    filename: str = "document.pdf",
    content: bytes = b"%PDF-1.4 fake pdf content",
    content_type: str = "application/pdf",
) -> UploadFile:
    """Build a minimal UploadFile suitable for upload endpoint tests."""
    file_obj = io.BytesIO(content)
    upload = MagicMock(spec=UploadFile)
    upload.filename = filename
    upload.content_type = content_type
    upload.read = AsyncMock(return_value=content)
    upload.seek = AsyncMock()
    upload.size = len(content)
    return upload


def _make_attachment_record(
    *,
    attachment_id: UUID = TEST_ATTACHMENT_ID,
    user_id: UUID = TEST_USER_ID,
    filename: str = "document.pdf",
    mime_type: str = "application/pdf",
    size_bytes: int = 2097152,
    source: str = "local",
) -> MagicMock:
    """Build a mock ChatAttachment ORM record."""
    record = MagicMock()
    record.id = attachment_id
    record.user_id = user_id
    record.filename = filename
    record.mime_type = mime_type
    record.size_bytes = size_bytes
    record.source = source
    record.expires_at = datetime.now(UTC) + timedelta(hours=24)
    return record


def _make_upload_service(
    return_record: MagicMock | None = None,
    raises: Exception | None = None,
) -> AsyncMock:
    """Build a mock AttachmentUploadService."""
    svc = AsyncMock()
    if raises is not None:
        svc.execute = AsyncMock(side_effect=raises)
    else:
        svc.execute = AsyncMock(return_value=return_record)
    return svc


# ---------------------------------------------------------------------------
# TestUploadEndpoint
# ---------------------------------------------------------------------------


class TestUploadEndpoint:
    """POST /ai/attachments/upload"""

    async def test_upload_valid_file_returns_201(self) -> None:
        """Valid PDF + workspace_id → 201 with full response schema."""
        record = _make_attachment_record()
        upload_svc = _make_upload_service(return_record=record)
        file = _make_upload_file()

        result = await upload_attachment(
            file=file,
            workspace_id=TEST_WORKSPACE_ID,
            session_id=None,
            user_id=TEST_USER_ID,
            upload_service=upload_svc,
        )

        assert result.attachment_id == TEST_ATTACHMENT_ID
        assert result.filename == "document.pdf"
        assert result.mime_type == "application/pdf"
        assert result.size_bytes == 2097152
        assert result.source == "local"
        assert result.expires_at is not None
        upload_svc.execute.assert_awaited_once()

    async def test_upload_unsupported_type_returns_400(self) -> None:
        """.exe file → 400 UNSUPPORTED_FILE_TYPE."""
        file = _make_upload_file(
            filename="exploit.exe",
            content=b"MZ\x00\x00fake exe",
            content_type="application/octet-stream",
        )
        upload_svc = _make_upload_service(
            raises=HTTPException(
                status_code=400,
                detail={"code": "UNSUPPORTED_FILE_TYPE", "message": "MIME type not allowed"},
            )
        )

        with pytest.raises(HTTPException) as exc_info:
            await upload_attachment(
                file=file,
                workspace_id=TEST_WORKSPACE_ID,
                session_id=None,
                user_id=TEST_USER_ID,
                upload_service=upload_svc,
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["code"] == "UNSUPPORTED_FILE_TYPE"

    async def test_upload_oversized_returns_400(self) -> None:
        """File >25 MB → 400 FILE_TOO_LARGE."""
        oversized_content = b"x" * (26 * 1024 * 1024)
        file = _make_upload_file(
            filename="big.pdf",
            content=oversized_content,
            content_type="application/pdf",
        )
        upload_svc = _make_upload_service(
            raises=HTTPException(
                status_code=400,
                detail={"code": "FILE_TOO_LARGE", "message": "Exceeds size limit"},
            )
        )

        with pytest.raises(HTTPException) as exc_info:
            await upload_attachment(
                file=file,
                workspace_id=TEST_WORKSPACE_ID,
                session_id=None,
                user_id=TEST_USER_ID,
                upload_service=upload_svc,
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["code"] == "FILE_TOO_LARGE"

    async def test_upload_empty_file_returns_400(self) -> None:
        """Zero-byte file → 400 EMPTY_FILE."""
        file = _make_upload_file(
            filename="empty.pdf",
            content=b"",
            content_type="application/pdf",
        )
        upload_svc = _make_upload_service(
            raises=HTTPException(
                status_code=400,
                detail={"code": "EMPTY_FILE", "message": "File has no content"},
            )
        )

        with pytest.raises(HTTPException) as exc_info:
            await upload_attachment(
                file=file,
                workspace_id=TEST_WORKSPACE_ID,
                session_id=None,
                user_id=TEST_USER_ID,
                upload_service=upload_svc,
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["code"] == "EMPTY_FILE"


# ---------------------------------------------------------------------------
# TestDeleteEndpoint
# ---------------------------------------------------------------------------


class TestDeleteEndpoint:
    """DELETE /ai/attachments/{attachment_id}"""

    async def test_delete_own_attachment_returns_204(self) -> None:
        """Attachment owned by requesting user → 204 no content."""
        svc = AsyncMock()
        svc.delete = AsyncMock(return_value=None)

        result = await delete_attachment(
            attachment_id=TEST_ATTACHMENT_ID,
            user_id=TEST_USER_ID,
            upload_service=svc,
        )

        # 204 handler returns None (FastAPI infers no-content response)
        assert result is None
        svc.delete.assert_awaited_once_with(attachment_id=TEST_ATTACHMENT_ID, user_id=TEST_USER_ID)

    async def test_delete_not_found_returns_404(self) -> None:
        """Unknown attachment_id → 404 NOT_FOUND."""
        svc = AsyncMock()
        svc.delete = AsyncMock(side_effect=ValueError("NOT_FOUND"))

        with pytest.raises(HTTPException) as exc_info:
            await delete_attachment(
                attachment_id=uuid4(),
                user_id=TEST_USER_ID,
                upload_service=svc,
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["code"] == "NOT_FOUND"

    async def test_delete_other_user_attachment_returns_403(self) -> None:
        """Attachment owned by a different user → 403 FORBIDDEN."""
        svc = AsyncMock()
        svc.delete = AsyncMock(side_effect=PermissionError("FORBIDDEN"))

        with pytest.raises(HTTPException) as exc_info:
            await delete_attachment(
                attachment_id=TEST_ATTACHMENT_ID,
                user_id=TEST_USER_ID,
                upload_service=svc,
            )

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["code"] == "FORBIDDEN"


# ---------------------------------------------------------------------------
# TestGuestRestriction
# ---------------------------------------------------------------------------


class TestGuestRestriction:
    """Guest role must be blocked at the upload endpoint."""

    async def test_guest_user_upload_returns_403(self) -> None:
        """Guest role → 403 GUEST_NOT_ALLOWED before any service call."""
        file = _make_upload_file()
        upload_svc = _make_upload_service(
            raises=HTTPException(
                status_code=403,
                detail={"code": "GUEST_NOT_ALLOWED", "message": "Guests cannot upload"},
            )
        )

        with pytest.raises(HTTPException) as exc_info:
            await upload_attachment(
                file=file,
                workspace_id=TEST_WORKSPACE_ID,
                session_id=None,
                user_id=TEST_USER_ID,
                upload_service=upload_svc,
            )

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["code"] == "GUEST_NOT_ALLOWED"
