"""TDD tests for DriveOAuthService — Google Drive OAuth token management.

Tests written FIRST (TDD red phase). Service does not exist yet.
All tests FAIL with ImportError until Batch 8 implements it.

Covers:
- get_status: connected=False when no credential, connected=True with email when credential found
- get_auth_url: returns URL string containing OAuth params
- handle_callback: raises on invalid state, succeeds with valid state (mocked HTTP)
- revoke: raises 404 when no credential, calls Google + deletes on success

Feature: 020 — Chat Context Attachments & Google Drive
Task: T037
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import parse_qs, urlparse
from uuid import UUID

import pytest
from fastapi import HTTPException

from pilot_space.application.services.ai.drive_oauth_service import DriveOAuthService

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEST_USER_ID = UUID("aaaaaaaa-0000-0000-0000-000000000001")
TEST_WORKSPACE_ID = UUID("bbbbbbbb-0000-0000-0000-000000000002")

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_session() -> AsyncMock:
    """Mock async SQLAlchemy session."""
    return AsyncMock()


@pytest.fixture
def mock_credential_repo() -> AsyncMock:
    """Mock DriveCredentialRepository with all methods as AsyncMock."""
    repo = AsyncMock()
    repo.get_by_user_workspace = AsyncMock(return_value=None)
    repo.upsert = AsyncMock()
    repo.delete_by_user_workspace = AsyncMock(return_value=True)
    return repo


@pytest.fixture
def mock_settings() -> MagicMock:
    """Mock Settings with Google OAuth fields."""
    settings = MagicMock()
    settings.google_client_id = "test-client-id"
    settings.google_client_secret = MagicMock(get_secret_value=lambda: "secret")
    settings.frontend_url = "http://localhost:3000"
    return settings


@pytest.fixture
def service(
    mock_session: AsyncMock,
    mock_credential_repo: AsyncMock,
    mock_settings: MagicMock,
) -> DriveOAuthService:
    """Create DriveOAuthService with all dependencies mocked."""
    return DriveOAuthService(
        credential_repo=mock_credential_repo,
        settings=mock_settings,
    )


def _make_drive_credential(
    google_email: str = "alice@example.com",
    created_at: datetime | None = None,
) -> MagicMock:
    """Build a mock DriveCredential ORM record."""
    cred = MagicMock()
    cred.google_email = google_email
    cred.created_at = created_at or datetime.now(UTC)
    cred.access_token = "encrypted-access-token"
    cred.refresh_token = "encrypted-refresh-token"
    cred.token_expires_at = datetime.now(UTC)
    cred.scope = "https://www.googleapis.com/auth/drive.readonly"
    return cred


# ===========================================================================
# TestGetStatus
# ===========================================================================


class TestGetStatus:
    """get_status() returns DriveStatusResponse based on credential presence."""

    async def test_get_status_not_connected(
        self,
        service: DriveOAuthService,
        mock_credential_repo: AsyncMock,
        mock_session: AsyncMock,
    ) -> None:
        """When no credential exists, returns connected=False with null fields."""
        mock_credential_repo.get_by_user_workspace.return_value = None

        result = await service.get_status(
            user_id=TEST_USER_ID,
            workspace_id=TEST_WORKSPACE_ID,
            session=mock_session,
        )

        assert result.connected is False
        assert result.google_email is None
        mock_credential_repo.get_by_user_workspace.assert_awaited_once_with(
            TEST_USER_ID, TEST_WORKSPACE_ID
        )

    async def test_get_status_connected(
        self,
        service: DriveOAuthService,
        mock_credential_repo: AsyncMock,
        mock_session: AsyncMock,
    ) -> None:
        """When credential exists, returns connected=True with email and timestamp."""
        cred = _make_drive_credential(google_email="alice@example.com")
        mock_credential_repo.get_by_user_workspace.return_value = cred

        result = await service.get_status(
            user_id=TEST_USER_ID,
            workspace_id=TEST_WORKSPACE_ID,
            session=mock_session,
        )

        assert result.connected is True
        assert result.google_email == "alice@example.com"
        assert result.connected_at is not None


# ===========================================================================
# TestGetAuthUrl
# ===========================================================================


class TestGetAuthUrl:
    """get_auth_url() returns a Google OAuth URL with required query params."""

    async def test_get_auth_url_returns_url_with_oauth_params(
        self,
        service: DriveOAuthService,
    ) -> None:
        """Returned auth_url contains accounts.google.com, scope, code_challenge, and state."""
        result = await service.get_auth_url(
            workspace_id=TEST_WORKSPACE_ID,
            redirect_uri="http://localhost:3000/callback",
        )

        # result may be a dict {"auth_url": "..."} or a string
        auth_url: str = result["auth_url"] if isinstance(result, dict) else result

        assert "accounts.google.com" in auth_url
        assert "scope" in auth_url
        assert "code_challenge" in auth_url
        assert "state" in auth_url


# ===========================================================================
# TestHandleCallback
# ===========================================================================


class TestHandleCallback:
    """handle_callback() validates state and exchanges code for tokens."""

    async def test_handle_callback_invalid_state_raises(
        self,
        service: DriveOAuthService,
        mock_session: AsyncMock,
    ) -> None:
        """A tampered or unknown state value raises HTTPException 400."""
        with pytest.raises(HTTPException) as exc_info:
            await service.handle_callback(
                code="code123",
                state="invalid-state-that-was-never-issued",
                workspace_id=TEST_WORKSPACE_ID,
                user_id=TEST_USER_ID,
                session=mock_session,
            )

        assert exc_info.value.status_code == 400

    async def test_handle_callback_success_upserts_credential(
        self,
        service: DriveOAuthService,
        mock_credential_repo: AsyncMock,
        mock_session: AsyncMock,
    ) -> None:
        """Valid state + auth code exchanges tokens and upserts credential with correct user_id."""
        # Generate a valid state by calling get_auth_url first
        auth_result = await service.get_auth_url(
            workspace_id=TEST_WORKSPACE_ID,
            redirect_uri="http://localhost:3000/callback",
        )
        auth_url: str = auth_result["auth_url"] if isinstance(auth_result, dict) else auth_result
        parsed = urlparse(auth_url)
        qs = parse_qs(parsed.query)
        valid_state = qs["state"][0]

        # Mock token exchange and userinfo HTTP calls
        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {
            "access_token": "tok",
            "refresh_token": "ref",
            "expires_in": 3600,
            "scope": "https://www.googleapis.com/auth/drive.readonly",
        }
        mock_token_response.raise_for_status = MagicMock()

        mock_userinfo_response = MagicMock()
        mock_userinfo_response.json.return_value = {"email": "alice@example.com"}
        mock_userinfo_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(return_value=mock_token_response)
        mock_http_client.get = AsyncMock(return_value=mock_userinfo_response)
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_http_client):
            await service.handle_callback(
                code="auth-code",
                state=valid_state,
                workspace_id=TEST_WORKSPACE_ID,
                user_id=TEST_USER_ID,
                session=mock_session,
            )

        assert mock_credential_repo.upsert.called
        # Verify credential is stored with correct user_id (not workspace_id)
        saved_credential = mock_credential_repo.upsert.call_args[0][0]
        assert saved_credential.user_id == TEST_USER_ID
        assert saved_credential.workspace_id == TEST_WORKSPACE_ID


# ===========================================================================
# TestRevoke
# ===========================================================================


class TestRevoke:
    """revoke() calls Google's revoke endpoint and removes the credential."""

    async def test_revoke_no_credential_raises_not_found(
        self,
        service: DriveOAuthService,
        mock_credential_repo: AsyncMock,
        mock_session: AsyncMock,
    ) -> None:
        """When no credential exists for the user+workspace, raises HTTPException 404."""
        mock_credential_repo.get_by_user_workspace.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await service.revoke(
                user_id=TEST_USER_ID,
                workspace_id=TEST_WORKSPACE_ID,
                session=mock_session,
            )

        assert exc_info.value.status_code == 404
        detail = exc_info.value.detail
        assert isinstance(detail, dict)
        assert detail.get("code") == "DRIVE_NOT_CONNECTED"

    async def test_revoke_success_calls_google_and_deletes(
        self,
        service: DriveOAuthService,
        mock_credential_repo: AsyncMock,
        mock_session: AsyncMock,
    ) -> None:
        """Successful revoke calls Google's revoke endpoint and deletes the credential."""
        cred = _make_drive_credential()
        mock_credential_repo.get_by_user_workspace.return_value = cred

        mock_revoke_response = MagicMock()
        mock_revoke_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(return_value=mock_revoke_response)
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_http_client):
            await service.revoke(
                user_id=TEST_USER_ID,
                workspace_id=TEST_WORKSPACE_ID,
                session=mock_session,
            )

        assert mock_credential_repo.delete_by_user_workspace.called
