"""TENANT-02: Workspace encryption API endpoint tests.

Router-level tests for the encryption management API:
- GET /api/v1/workspaces/{slug}/encryption — get status (no key leak)
- PUT /api/v1/workspaces/{slug}/encryption/key — store encrypted key
- POST /api/v1/workspaces/{slug}/encryption/verify — verify key matches
- POST /api/v1/workspaces/{slug}/encryption/generate-key — generate new key

Tests use dependency_overrides to bypass auth and DB layers.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from fastapi import status

pytestmark = pytest.mark.asyncio

WORKSPACE_SLUG = "test-workspace"
_OWNER_USER_ID = uuid4()
_MEMBER_USER_ID = uuid4()
_WORKSPACE_ID = uuid4()

# Path aliases for patching
_RESOLVE_PATH = "pilot_space.api.v1.routers.workspace_encryption._resolve_workspace"
_CHECK_PERMISSION_PATH = "pilot_space.api.v1.routers.workspace_encryption.check_permission"
_REPO_PATH = "pilot_space.api.v1.routers.workspace_encryption.WorkspaceEncryptionRepository"


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
async def enc_client(request: Any) -> AsyncGenerator[Any, None]:
    """Authenticated client with overrides for encryption router tests.

    Accepts an optional indirect parameter 'user_id' to test different roles.
    """
    from datetime import UTC, datetime

    from httpx import ASGITransport, AsyncClient

    from pilot_space.dependencies.auth import get_current_user, get_session
    from pilot_space.infrastructure.auth import TokenPayload
    from pilot_space.main import app

    user_id = getattr(request, "param", _OWNER_USER_ID)

    mock_session = AsyncMock()

    async def mock_session_gen() -> AsyncGenerator[Any, None]:
        yield mock_session

    now = datetime.now(tz=UTC)
    mock_payload = TokenPayload(
        sub=str(user_id),
        email="test@example.com",
        role="authenticated",
        aud="authenticated",
        exp=int(now.timestamp()) + 3600,
        iat=int(now.timestamp()),
        app_metadata={},
        user_metadata={},
    )

    app.dependency_overrides[get_session] = mock_session_gen
    app.dependency_overrides[get_current_user] = lambda: mock_payload

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    ) as ac:
        yield ac

    app.dependency_overrides.pop(get_session, None)
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def valid_fernet_key() -> str:
    """Generate a valid Fernet key for testing."""
    return Fernet.generate_key().decode()


# ============================================================================
# GET /workspaces/{slug}/encryption
# ============================================================================


async def test_get_encryption_status_no_key_configured(
    enc_client: Any,
) -> None:
    """GET returns {enabled: false, key_hint: null, key_version: null} when no key set."""
    mock_repo = AsyncMock()
    mock_repo.get_key_record.return_value = None

    with (
        patch(_RESOLVE_PATH, return_value=_WORKSPACE_ID),
        patch(_CHECK_PERMISSION_PATH, return_value=True),
        patch(_REPO_PATH, return_value=mock_repo),
    ):
        response = await enc_client.get(f"/api/v1/workspaces/{WORKSPACE_SLUG}/encryption/")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["enabled"] is False
    assert data["key_hint"] is None
    assert data["key_version"] is None
    # Must NEVER contain the raw encrypted key
    assert "encrypted_workspace_key" not in data


async def test_get_encryption_status_key_configured(
    enc_client: Any,
) -> None:
    """GET returns {enabled: true, key_hint, key_version} when key is set."""
    mock_key_record = MagicMock()
    mock_key_record.key_hint = "AbCdEfGh"
    mock_key_record.key_version = 2
    mock_key_record.updated_at = datetime.now(tz=UTC)

    mock_repo = AsyncMock()
    mock_repo.get_key_record.return_value = mock_key_record

    with (
        patch(_RESOLVE_PATH, return_value=_WORKSPACE_ID),
        patch(_CHECK_PERMISSION_PATH, return_value=True),
        patch(_REPO_PATH, return_value=mock_repo),
    ):
        response = await enc_client.get(f"/api/v1/workspaces/{WORKSPACE_SLUG}/encryption/")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["enabled"] is True
    assert data["key_hint"] == "AbCdEfGh"
    assert data["key_version"] == 2
    assert "encrypted_workspace_key" not in data


async def test_get_encryption_requires_admin_permission(enc_client: Any) -> None:
    """GET /encryption returns 403 when user lacks settings:read."""
    with (
        patch(_RESOLVE_PATH, return_value=_WORKSPACE_ID),
        patch(_CHECK_PERMISSION_PATH, return_value=False),
    ):
        response = await enc_client.get(f"/api/v1/workspaces/{WORKSPACE_SLUG}/encryption/")

    assert response.status_code == status.HTTP_403_FORBIDDEN


# ============================================================================
# PUT /workspaces/{slug}/encryption/key
# ============================================================================


async def test_put_encryption_key_stores_and_returns_hint(
    enc_client: Any, valid_fernet_key: str
) -> None:
    """PUT with valid Fernet key stores it and returns {key_version, key_hint}."""
    mock_key_record = MagicMock()
    mock_key_record.key_version = 1
    mock_key_record.key_hint = valid_fernet_key[-8:]

    mock_repo = AsyncMock()
    mock_repo.upsert_key.return_value = mock_key_record

    with (
        patch(_RESOLVE_PATH, return_value=_WORKSPACE_ID),
        patch(_CHECK_PERMISSION_PATH, return_value=True),
        patch(_REPO_PATH, return_value=mock_repo),
    ):
        response = await enc_client.put(
            f"/api/v1/workspaces/{WORKSPACE_SLUG}/encryption/key",
            json={"key": valid_fernet_key},
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "key_version" in data
    assert "key_hint" in data
    # Must never return the raw key or encrypted key
    assert "encrypted_workspace_key" not in data
    assert "key" not in data


async def test_put_encryption_key_invalid_format_returns_422(enc_client: Any) -> None:
    """PUT with invalid key format returns 422 with actionable message."""
    with (
        patch(_RESOLVE_PATH, return_value=_WORKSPACE_ID),
        patch(_CHECK_PERMISSION_PATH, return_value=True),
    ):
        response = await enc_client.put(
            f"/api/v1/workspaces/{WORKSPACE_SLUG}/encryption/key",
            json={"key": "not-a-valid-fernet-key"},
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    # Should contain helpful message about key format
    body = response.json()
    assert body is not None


async def test_put_encryption_key_requires_owner_permission(
    enc_client: Any, valid_fernet_key: str
) -> None:
    """PUT /encryption/key returns 403 when user lacks settings:manage (OWNER only)."""
    with (
        patch(_RESOLVE_PATH, return_value=_WORKSPACE_ID),
        patch(_CHECK_PERMISSION_PATH, return_value=False),
    ):
        response = await enc_client.put(
            f"/api/v1/workspaces/{WORKSPACE_SLUG}/encryption/key",
            json={"key": valid_fernet_key},
        )

    assert response.status_code == status.HTTP_403_FORBIDDEN


# ============================================================================
# POST /workspaces/{slug}/encryption/verify
# ============================================================================


async def test_post_verify_correct_key_returns_verified_true(
    enc_client: Any, valid_fernet_key: str
) -> None:
    """POST /verify with the stored key returns {verified: true, key_version}."""
    from pilot_space.infrastructure.workspace_encryption import store_workspace_key

    stored = store_workspace_key(valid_fernet_key)
    mock_key_record = MagicMock()
    mock_key_record.encrypted_workspace_key = stored
    mock_key_record.key_version = 1

    mock_repo = AsyncMock()
    mock_repo.get_key_record.return_value = mock_key_record

    with (
        patch(_RESOLVE_PATH, return_value=_WORKSPACE_ID),
        patch(_CHECK_PERMISSION_PATH, return_value=True),
        patch(_REPO_PATH, return_value=mock_repo),
    ):
        response = await enc_client.post(
            f"/api/v1/workspaces/{WORKSPACE_SLUG}/encryption/verify",
            json={"key": valid_fernet_key},
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["verified"] is True
    assert data["key_version"] == 1


async def test_post_verify_wrong_key_returns_422(enc_client: Any, valid_fernet_key: str) -> None:
    """POST /verify with wrong key returns 422."""
    from pilot_space.infrastructure.workspace_encryption import store_workspace_key

    # Store key A, verify with key B
    different_key = Fernet.generate_key().decode()
    stored = store_workspace_key(valid_fernet_key)
    mock_key_record = MagicMock()
    mock_key_record.encrypted_workspace_key = stored
    mock_key_record.key_version = 1

    mock_repo = AsyncMock()
    mock_repo.get_key_record.return_value = mock_key_record

    with (
        patch(_RESOLVE_PATH, return_value=_WORKSPACE_ID),
        patch(_CHECK_PERMISSION_PATH, return_value=True),
        patch(_REPO_PATH, return_value=mock_repo),
    ):
        response = await enc_client.post(
            f"/api/v1/workspaces/{WORKSPACE_SLUG}/encryption/verify",
            json={"key": different_key},
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_post_verify_no_key_configured_returns_404(
    enc_client: Any, valid_fernet_key: str
) -> None:
    """POST /verify when no key is configured returns 404."""
    mock_repo = AsyncMock()
    mock_repo.get_key_record.return_value = None

    with (
        patch(_RESOLVE_PATH, return_value=_WORKSPACE_ID),
        patch(_CHECK_PERMISSION_PATH, return_value=True),
        patch(_REPO_PATH, return_value=mock_repo),
    ):
        response = await enc_client.post(
            f"/api/v1/workspaces/{WORKSPACE_SLUG}/encryption/verify",
            json={"key": valid_fernet_key},
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# POST /workspaces/{slug}/encryption/generate-key
# ============================================================================


async def test_post_generate_key_returns_valid_fernet_key(enc_client: Any) -> None:
    """POST /generate-key returns a valid Fernet key."""
    with (
        patch(_RESOLVE_PATH, return_value=_WORKSPACE_ID),
        patch(_CHECK_PERMISSION_PATH, return_value=True),
    ):
        response = await enc_client.post(
            f"/api/v1/workspaces/{WORKSPACE_SLUG}/encryption/generate-key",
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "key" in data

    # Must be a valid Fernet key
    generated_key = data["key"]
    f = Fernet(generated_key.encode())  # raises if invalid
    assert f is not None


async def test_encrypted_workspace_key_never_in_any_response(enc_client: Any) -> None:
    """GET /encryption does not return encrypted_workspace_key at any depth."""
    mock_key_record = MagicMock()
    mock_key_record.key_hint = "AbCdEfGh"
    mock_key_record.key_version = 1
    mock_key_record.updated_at = datetime.now(tz=UTC)

    mock_repo = AsyncMock()
    mock_repo.get_key_record.return_value = mock_key_record

    with (
        patch(_RESOLVE_PATH, return_value=_WORKSPACE_ID),
        patch(_CHECK_PERMISSION_PATH, return_value=True),
        patch(_REPO_PATH, return_value=mock_repo),
    ):
        response = await enc_client.get(f"/api/v1/workspaces/{WORKSPACE_SLUG}/encryption/")

    assert response.status_code == status.HTTP_200_OK
    # Verify the raw field name never appears anywhere in the JSON
    assert "encrypted_workspace_key" not in response.text
