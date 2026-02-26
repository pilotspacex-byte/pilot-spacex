"""Unit tests for DriveFileService — Google Drive file listing and import.

Covers:
- list_files: no credential (402), credential found → calls Drive API with params
- list_files: parent_id + search + page_token forwarded in query string
- import_file: no credential (402)
- import_file: Google Workspace MIME type → export path (PDF)
- import_file: non-Workspace MIME type → direct download path
- import_file: session passed → session.add and flush called
- import_file: session=None → no session side-effects

Feature: 020 — Chat Context Attachments & Google Drive
Task: T037
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from fastapi import HTTPException

from pilot_space.api.v1.schemas.attachments import DriveImportRequest
from pilot_space.application.services.ai.drive_file_service import DriveFileService

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEST_USER_ID = UUID("aaaaaaaa-0000-0000-0000-000000000001")
TEST_WORKSPACE_ID = UUID("bbbbbbbb-0000-0000-0000-000000000002")
TEST_SESSION_ID = "sess-001"

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_credential_repo() -> AsyncMock:
    """Mock DriveCredentialRepository."""
    repo = AsyncMock()
    repo.get_by_user_workspace = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def mock_attachment_repo() -> AsyncMock:
    """Mock ChatAttachmentRepository. create() returns the input attachment."""
    repo = AsyncMock()
    repo.create = AsyncMock(side_effect=lambda a: a)
    return repo


@pytest.fixture
def mock_storage_client() -> AsyncMock:
    """Mock SupabaseStorageClient."""
    client = AsyncMock()
    client.upload_object = AsyncMock(return_value=None)
    return client


@pytest.fixture
def mock_settings() -> MagicMock:
    """Mock Settings object."""
    return MagicMock()


@pytest.fixture
def service(
    mock_credential_repo: AsyncMock,
    mock_attachment_repo: AsyncMock,
    mock_storage_client: AsyncMock,
    mock_settings: MagicMock,
) -> DriveFileService:
    """DriveFileService with all dependencies mocked."""
    return DriveFileService(
        credential_repo=mock_credential_repo,
        attachment_repo=mock_attachment_repo,
        storage_client=mock_storage_client,
        settings=mock_settings,
    )


def _make_credential(access_token: str = "plain-token") -> MagicMock:
    """Build a mock DriveCredential ORM record."""
    cred = MagicMock()
    cred.access_token = access_token
    return cred


def _make_drive_api_response(
    files: list[dict] | None = None,
    next_page_token: str | None = None,
) -> MagicMock:
    """Build a mock httpx response for the Drive files API."""
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "files": files or [],
        **({"nextPageToken": next_page_token} if next_page_token else {}),
    }
    return resp


# ===========================================================================
# TestListFiles
# ===========================================================================


class TestListFiles:
    """DriveFileService.list_files()"""

    async def test_list_files_no_credential_raises_402(
        self,
        service: DriveFileService,
        mock_credential_repo: AsyncMock,
    ) -> None:
        """When no credential exists, raises HTTPException 402 DRIVE_NOT_CONNECTED."""
        mock_credential_repo.get_by_user_workspace.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await service.list_files(
                workspace_id=TEST_WORKSPACE_ID,
                user_id=TEST_USER_ID,
            )

        assert exc_info.value.status_code == 402
        detail = exc_info.value.detail
        assert isinstance(detail, dict)
        assert detail.get("code") == "DRIVE_NOT_CONNECTED"

    async def test_list_files_returns_files_from_drive(
        self,
        service: DriveFileService,
        mock_credential_repo: AsyncMock,
    ) -> None:
        """Valid credential → calls Drive API and returns parsed DriveFileListResponse."""
        mock_credential_repo.get_by_user_workspace.return_value = _make_credential()

        drive_file = {
            "id": "file-abc",
            "name": "My Doc",
            "mimeType": "application/vnd.google-apps.document",
            "modifiedTime": "2024-01-01T00:00:00Z",
            "iconLink": "https://drive.google.com/icon.png",
        }
        mock_response = _make_drive_api_response(files=[drive_file])

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_http_client):
            result = await service.list_files(
                workspace_id=TEST_WORKSPACE_ID,
                user_id=TEST_USER_ID,
            )

        assert len(result.files) == 1
        assert result.files[0].id == "file-abc"
        assert result.files[0].name == "My Doc"
        assert result.next_page_token is None

    async def test_list_files_with_size_parsed(
        self,
        service: DriveFileService,
        mock_credential_repo: AsyncMock,
    ) -> None:
        """Files with 'size' field have size_bytes parsed as int."""
        mock_credential_repo.get_by_user_workspace.return_value = _make_credential()

        drive_file = {
            "id": "file-xyz",
            "name": "Image.png",
            "mimeType": "image/png",
            "size": "204800",
            "modifiedTime": "2024-06-01T12:00:00Z",
            "iconLink": None,
        }
        mock_response = _make_drive_api_response(files=[drive_file])

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_http_client):
            result = await service.list_files(
                workspace_id=TEST_WORKSPACE_ID,
                user_id=TEST_USER_ID,
            )

        assert result.files[0].size_bytes == 204800

    async def test_list_files_folder_is_flagged(
        self,
        service: DriveFileService,
        mock_credential_repo: AsyncMock,
    ) -> None:
        """Items with folder MIME type have is_folder=True."""
        mock_credential_repo.get_by_user_workspace.return_value = _make_credential()

        drive_file = {
            "id": "folder-001",
            "name": "Projects",
            "mimeType": "application/vnd.google-apps.folder",
        }
        mock_response = _make_drive_api_response(files=[drive_file])

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_http_client):
            result = await service.list_files(
                workspace_id=TEST_WORKSPACE_ID,
                user_id=TEST_USER_ID,
            )

        assert result.files[0].is_folder is True

    async def test_list_files_next_page_token_forwarded(
        self,
        service: DriveFileService,
        mock_credential_repo: AsyncMock,
    ) -> None:
        """next_page_token from Drive API is included in response."""
        mock_credential_repo.get_by_user_workspace.return_value = _make_credential()

        mock_response = _make_drive_api_response(next_page_token="tok-xyz")

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_http_client):
            result = await service.list_files(
                workspace_id=TEST_WORKSPACE_ID,
                user_id=TEST_USER_ID,
                page_token="prev-tok",
            )

        assert result.next_page_token == "tok-xyz"

    async def test_list_files_with_parent_id_and_search(
        self,
        service: DriveFileService,
        mock_credential_repo: AsyncMock,
    ) -> None:
        """parent_id and search are both appended to the Drive query string."""
        mock_credential_repo.get_by_user_workspace.return_value = _make_credential()

        mock_response = _make_drive_api_response()

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_http_client):
            result = await service.list_files(
                workspace_id=TEST_WORKSPACE_ID,
                user_id=TEST_USER_ID,
                parent_id="folder-root-id",
                search="budget",
            )

        # Call should succeed and return empty file list
        assert isinstance(result.files, list)
        # Verify query params were forwarded (params dict passed to get)
        call_kwargs = mock_http_client.get.call_args[1]
        query_str: str = call_kwargs["params"]["q"]
        assert "folder-root-id" in query_str
        assert "budget" in query_str

    async def test_list_files_encryption_fallback(
        self,
        service: DriveFileService,
        mock_credential_repo: AsyncMock,
    ) -> None:
        """When decrypt_api_key raises EncryptionError, falls back to raw token."""
        from pilot_space.infrastructure.encryption import EncryptionError

        mock_credential_repo.get_by_user_workspace.return_value = _make_credential(
            access_token="raw-token"
        )

        mock_response = _make_drive_api_response()

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=None)

        with (
            patch(
                "pilot_space.application.services.ai.drive_file_service.decrypt_api_key",
                side_effect=EncryptionError("bad key"),
            ),
            patch("httpx.AsyncClient", return_value=mock_http_client),
        ):
            result = await service.list_files(
                workspace_id=TEST_WORKSPACE_ID,
                user_id=TEST_USER_ID,
            )

        # Should not raise; returns empty file list
        assert isinstance(result.files, list)


# ===========================================================================
# TestImportFile
# ===========================================================================


class TestImportFile:
    """DriveFileService.import_file()"""

    async def test_import_file_no_credential_raises_402(
        self,
        service: DriveFileService,
        mock_credential_repo: AsyncMock,
    ) -> None:
        """When no credential exists, raises HTTPException 402."""
        mock_credential_repo.get_by_user_workspace.return_value = None

        request = DriveImportRequest(
            workspace_id=TEST_WORKSPACE_ID,
            file_id="file-123",
            filename="doc.pdf",
            mime_type="application/pdf",
            session_id=None,
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.import_file(request=request, user_id=TEST_USER_ID)

        assert exc_info.value.status_code == 402
        assert exc_info.value.detail["code"] == "DRIVE_NOT_CONNECTED"

    async def test_import_file_workspace_mime_uses_export_endpoint(
        self,
        service: DriveFileService,
        mock_credential_repo: AsyncMock,
        mock_storage_client: AsyncMock,
    ) -> None:
        """Google Workspace MIME type triggers export endpoint with PDF mimeType param."""
        mock_credential_repo.get_by_user_workspace.return_value = _make_credential()

        file_content = b"%PDF-1.4 content"
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.content = file_content

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=None)

        request = DriveImportRequest(
            workspace_id=TEST_WORKSPACE_ID,
            file_id="gdoc-file-id",
            filename="report.gdoc",
            mime_type="application/vnd.google-apps.document",
            session_id=None,
        )

        with patch("httpx.AsyncClient", return_value=mock_http_client):
            result = await service.import_file(request=request, user_id=TEST_USER_ID)

        # Should use export URL with PDF mime type
        call_url: str = mock_http_client.get.call_args[0][0]
        assert "export" in call_url
        assert result.mime_type == "application/pdf"
        assert result.source == "google_drive"
        assert result.size_bytes == len(file_content)
        mock_storage_client.upload_object.assert_awaited_once()

    async def test_import_file_non_workspace_mime_uses_download_endpoint(
        self,
        service: DriveFileService,
        mock_credential_repo: AsyncMock,
        mock_storage_client: AsyncMock,
    ) -> None:
        """Non-Workspace MIME type (e.g. PDF) triggers direct download endpoint."""
        mock_credential_repo.get_by_user_workspace.return_value = _make_credential()

        file_content = b"binary data here"
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.content = file_content

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=None)

        request = DriveImportRequest(
            workspace_id=TEST_WORKSPACE_ID,
            file_id="pdf-file-id",
            filename="report.pdf",
            mime_type="application/pdf",
            session_id=None,
        )

        with patch("httpx.AsyncClient", return_value=mock_http_client):
            result = await service.import_file(request=request, user_id=TEST_USER_ID)

        # Should use download URL (alt=media), not export
        call_url: str = mock_http_client.get.call_args[0][0]
        assert "alt=media" in call_url
        assert result.mime_type == "application/pdf"
        assert result.source == "google_drive"
        mock_storage_client.upload_object.assert_awaited_once()

    async def test_import_file_persists_via_repo(
        self,
        service: DriveFileService,
        mock_credential_repo: AsyncMock,
        mock_attachment_repo: AsyncMock,
        mock_storage_client: AsyncMock,
    ) -> None:
        """import_file always persists the attachment via repo.create, not session."""
        mock_credential_repo.get_by_user_workspace.return_value = _make_credential()

        file_content = b"data"
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.content = file_content

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=None)

        request = DriveImportRequest(
            workspace_id=TEST_WORKSPACE_ID,
            file_id="file-with-repo",
            filename="doc.pdf",
            mime_type="application/pdf",
            session_id=TEST_SESSION_ID,
        )

        with patch("httpx.AsyncClient", return_value=mock_http_client):
            result = await service.import_file(request=request, user_id=TEST_USER_ID)

        mock_attachment_repo.create.assert_awaited_once()
        mock_storage_client.upload_object.assert_awaited_once()
        assert result.source == "google_drive"
        assert result.size_bytes == len(file_content)

    async def test_import_file_encryption_fallback(
        self,
        service: DriveFileService,
        mock_credential_repo: AsyncMock,
        mock_storage_client: AsyncMock,
    ) -> None:
        """When decrypt_api_key raises EncryptionError, falls back to raw access_token."""
        from pilot_space.infrastructure.encryption import EncryptionError

        mock_credential_repo.get_by_user_workspace.return_value = _make_credential(
            access_token="raw-access"
        )

        file_content = b"raw content"
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.content = file_content

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=None)

        request = DriveImportRequest(
            workspace_id=TEST_WORKSPACE_ID,
            file_id="file-enc-fallback",
            filename="doc.pdf",
            mime_type="application/pdf",
            session_id=None,
        )

        with (
            patch(
                "pilot_space.application.services.ai.drive_file_service.decrypt_api_key",
                side_effect=EncryptionError("decrypt failed"),
            ),
            patch("httpx.AsyncClient", return_value=mock_http_client),
        ):
            result = await service.import_file(request=request, user_id=TEST_USER_ID)

        assert result.source == "google_drive"
        mock_storage_client.upload_object.assert_awaited_once()
