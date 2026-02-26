"""TDD tests for Drive endpoints — GET /ai/drive/status, auth-url, files, import, DELETE credentials.

Tests written FIRST (TDD red phase). Router does not exist yet.
All tests FAIL with ImportError until Batch 8 implements it.

Feature: 020 — Chat Context Attachments & Google Drive
Task: T038
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from fastapi import HTTPException

from pilot_space.api.v1.routers.ai_drive import (
    get_drive_auth_url,
    get_drive_status,
    import_drive_file,
    list_drive_files,
    revoke_drive_credentials,
)
from pilot_space.api.v1.schemas.attachments import (
    AttachmentUploadResponse,
    DriveFileItem,
    DriveFileListResponse,
    DriveImportRequest,
    DriveStatusResponse,
)

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Fixed test IDs
# ---------------------------------------------------------------------------

TEST_USER_ID = UUID("aaaaaaaa-0000-0000-0000-000000000001")
TEST_WORKSPACE_ID = UUID("bbbbbbbb-0000-0000-0000-000000000002")
TEST_ATTACHMENT_ID = UUID("cccccccc-0000-0000-0000-000000000003")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_drive_service() -> AsyncMock:
    """Build a mock DriveOAuthService with all relevant methods as AsyncMock."""
    svc = AsyncMock()
    svc.get_status = AsyncMock()
    svc.get_auth_url = AsyncMock()
    svc.list_files = AsyncMock()
    svc.import_file = AsyncMock()
    svc.revoke = AsyncMock(return_value=None)
    return svc


def _make_file_item(
    file_id: str = "file1",
    name: str = "Doc",
    mime_type: str = "application/vnd.google-apps.document",
    size_bytes: int | None = 1000,
    is_folder: bool = False,
) -> DriveFileItem:
    """Build a DriveFileItem for use in mock return values."""
    return DriveFileItem(
        id=file_id,
        name=name,
        mime_type=mime_type,
        size_bytes=size_bytes,
        modified_at=datetime.now(UTC),
        is_folder=is_folder,
        icon_url=None,
    )


# ===========================================================================
# TestGetDriveStatus
# ===========================================================================


class TestGetDriveStatus:
    """GET /ai/drive/status"""

    async def test_get_drive_status_not_connected(self) -> None:
        """No credential for workspace → DriveStatusResponse(connected=False)."""
        mock_service = _make_drive_service()
        mock_service.get_status.return_value = DriveStatusResponse(
            connected=False,
            google_email=None,
            connected_at=None,
        )

        result = await get_drive_status(
            workspace_id=TEST_WORKSPACE_ID,
            user_id=TEST_USER_ID,
            drive_service=mock_service,
        )

        assert isinstance(result, DriveStatusResponse)
        assert result.connected is False
        assert result.google_email is None
        mock_service.get_status.assert_awaited_once()

    async def test_get_drive_status_connected(self) -> None:
        """Active credential → DriveStatusResponse with connected=True and email."""
        mock_service = _make_drive_service()
        mock_service.get_status.return_value = DriveStatusResponse(
            connected=True,
            google_email="alice@example.com",
            connected_at=datetime.now(UTC),
        )

        result = await get_drive_status(
            workspace_id=TEST_WORKSPACE_ID,
            user_id=TEST_USER_ID,
            drive_service=mock_service,
        )

        assert result.connected is True
        assert result.google_email == "alice@example.com"
        assert result.connected_at is not None


# ===========================================================================
# TestGetDriveAuthUrl
# ===========================================================================


class TestGetDriveAuthUrl:
    """GET /ai/drive/auth-url"""

    async def test_get_auth_url_success(self) -> None:
        """Authenticated member receives an OAuth redirect URL."""
        mock_service = _make_drive_service()
        mock_service.get_auth_url.return_value = {
            "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=test&scope=drive"
        }

        result = await get_drive_auth_url(
            workspace_id=TEST_WORKSPACE_ID,
            redirect_uri="http://localhost:3000/callback",
            user_id=TEST_USER_ID,
            drive_service=mock_service,
            user_role="member",
        )

        assert result["auth_url"].startswith("https://accounts.google.com")
        mock_service.get_auth_url.assert_awaited_once()

    async def test_get_auth_url_guest_forbidden(self) -> None:
        """Guest role is denied the auth URL — 403 before any service call."""
        mock_service = _make_drive_service()

        with pytest.raises(HTTPException) as exc_info:
            await get_drive_auth_url(
                workspace_id=TEST_WORKSPACE_ID,
                redirect_uri="http://localhost:3000/callback",
                user_id=TEST_USER_ID,
                drive_service=mock_service,
                user_role="guest",
            )

        assert exc_info.value.status_code == 403
        mock_service.get_auth_url.assert_not_awaited()


# ===========================================================================
# TestListDriveFiles
# ===========================================================================


class TestListDriveFiles:
    """GET /ai/drive/files"""

    async def test_list_drive_files_not_connected(self) -> None:
        """Service raises 402 DRIVE_NOT_CONNECTED → exception propagates."""
        mock_service = _make_drive_service()
        mock_service.list_files.side_effect = HTTPException(
            status_code=402,
            detail={"code": "DRIVE_NOT_CONNECTED", "message": "No Drive credential"},
        )

        with pytest.raises(HTTPException) as exc_info:
            await list_drive_files(
                workspace_id=TEST_WORKSPACE_ID,
                user_id=TEST_USER_ID,
                drive_service=mock_service,
                parent_id=None,
                search=None,
                page_token=None,
            )

        assert exc_info.value.status_code == 402

    async def test_list_drive_files_success(self) -> None:
        """Service returns file list → endpoint passes it through unchanged."""
        mock_service = _make_drive_service()
        mock_service.list_files.return_value = DriveFileListResponse(
            files=[_make_file_item(file_id="file1", name="Doc")],
            next_page_token=None,
        )

        result = await list_drive_files(
            workspace_id=TEST_WORKSPACE_ID,
            user_id=TEST_USER_ID,
            drive_service=mock_service,
            parent_id=None,
            search=None,
            page_token=None,
        )

        assert isinstance(result, DriveFileListResponse)
        assert len(result.files) == 1
        assert result.files[0].name == "Doc"
        mock_service.list_files.assert_awaited_once()


# ===========================================================================
# TestImportDriveFile
# ===========================================================================


class TestImportDriveFile:
    """POST /ai/drive/import"""

    async def test_import_drive_file_success(self) -> None:
        """Valid import request returns AttachmentUploadResponse with 201 semantics."""
        mock_service = _make_drive_service()
        mock_service.import_file.return_value = AttachmentUploadResponse(
            attachment_id=TEST_ATTACHMENT_ID,
            filename="Doc.gdoc",
            mime_type="application/pdf",
            size_bytes=50000,
            source="google_drive",
            expires_at=datetime.now(UTC),
        )

        import_request = DriveImportRequest(
            workspace_id=TEST_WORKSPACE_ID,
            file_id="drive-file-id-123",
            filename="Doc.gdoc",
            mime_type="application/vnd.google-apps.document",
            session_id=None,
        )

        result = await import_drive_file(
            request=import_request,
            user_id=TEST_USER_ID,
            drive_service=mock_service,
        )

        assert isinstance(result, AttachmentUploadResponse)
        assert result.attachment_id == TEST_ATTACHMENT_ID
        assert result.source == "google_drive"
        mock_service.import_file.assert_awaited_once()


# ===========================================================================
# TestRevokeDriveCredentials
# ===========================================================================


class TestRevokeDriveCredentials:
    """DELETE /ai/drive/credentials"""

    async def test_revoke_drive_credentials_success(self) -> None:
        """Successful revoke returns None (204 no-content semantics)."""
        mock_service = _make_drive_service()
        mock_service.revoke.return_value = None

        result = await revoke_drive_credentials(
            workspace_id=TEST_WORKSPACE_ID,
            user_id=TEST_USER_ID,
            drive_service=mock_service,
        )

        assert result is None
        mock_service.revoke.assert_awaited_once()
