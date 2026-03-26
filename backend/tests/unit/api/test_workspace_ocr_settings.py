"""Unit tests for workspace OCR settings router.

Tests call endpoint functions directly with mocked dependencies.

Covers:
- GET returns 404 when workspace not found
- GET returns 403 when user is not admin
- GET returns provider_type='none' when no OCR provider is configured
- PUT with provider_type="hunyuan_ocr" calls store_api_key with service_type="ocr"
- POST /test calls validate_connection and returns success/failure response
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from fastapi import HTTPException

from pilot_space.api.v1.routers.workspace_ocr_settings import (
    OcrSettingsUpdateRequest,
    get_ocr_settings as router_get_ocr_settings,
    test_ocr_connection as router_test_ocr_connection,
    update_ocr_settings as router_update_ocr_settings,
)

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Fixed IDs
# ---------------------------------------------------------------------------

TEST_USER_ID = UUID("aaaaaaaa-0000-0000-0000-000000000001")
TEST_WORKSPACE_ID = UUID("bbbbbbbb-0000-0000-0000-000000000002")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_current_user(user_id: UUID = TEST_USER_ID) -> MagicMock:
    """Build a mock CurrentUser."""
    user = MagicMock()
    user.user_id = user_id
    return user


def _make_session() -> MagicMock:
    """Build a mock DbSession."""
    return MagicMock()


def _make_workspace(
    workspace_id: UUID = TEST_WORKSPACE_ID,
    user_id: UUID = TEST_USER_ID,
    is_admin: bool = True,
) -> MagicMock:
    """Build a mock Workspace with one member."""
    workspace = MagicMock()
    workspace.id = workspace_id

    member = MagicMock()
    member.user_id = user_id
    member.is_admin = is_admin
    workspace.members = [member]

    return workspace


def _make_key_storage(key_info: MagicMock | None = None) -> MagicMock:
    """Build a mock KeyStorage (SecureKeyStorage)."""
    ks = MagicMock()
    ks.get_key_info = AsyncMock(return_value=key_info)
    ks.store_api_key = AsyncMock()
    ks.delete_api_key = AsyncMock()
    return ks


def _make_api_key_info(
    provider: str = "hunyuan_ocr",
    base_url: str = "http://localhost:8080/v1",
    model_name: str = "tencent/HunyuanOCR",
) -> MagicMock:
    """Build a mock APIKeyInfo."""
    info = MagicMock()
    info.provider = provider
    info.service_type = "ocr"
    info.is_valid = True
    info.last_validated_at = datetime.now(UTC)
    info.base_url = base_url
    info.model_name = model_name
    return info


# ---------------------------------------------------------------------------
# GET /workspaces/{id}/ocr/settings
# ---------------------------------------------------------------------------

# Patch path for the local import of WorkspaceRepository inside _get_admin_workspace
_WS_REPO_PATCH = (
    "pilot_space.infrastructure.database.repositories.workspace_repository.WorkspaceRepository"
)


async def test_get_ocr_settings_workspace_not_found() -> None:
    """GET returns 404 when workspace not found."""
    workspace_repo = MagicMock()
    workspace_repo.get_with_members = AsyncMock(return_value=None)

    with (
        patch(_WS_REPO_PATCH, return_value=workspace_repo),
        pytest.raises(HTTPException) as exc_info,
    ):
        await router_get_ocr_settings(
            workspace_id=TEST_WORKSPACE_ID,
            current_user=_make_current_user(),
            session=_make_session(),
            key_storage=_make_key_storage(),
        )

    assert exc_info.value.status_code == 404


async def test_get_ocr_settings_not_admin_returns_403() -> None:
    """GET returns 403 when user is not an admin."""
    workspace = _make_workspace(is_admin=False)
    workspace_repo = MagicMock()
    workspace_repo.get_with_members = AsyncMock(return_value=workspace)

    with (
        patch(_WS_REPO_PATCH, return_value=workspace_repo),
        pytest.raises(HTTPException) as exc_info,
    ):
        await router_get_ocr_settings(
            workspace_id=TEST_WORKSPACE_ID,
            current_user=_make_current_user(),
            session=_make_session(),
            key_storage=_make_key_storage(),
        )

    assert exc_info.value.status_code == 403


async def test_get_ocr_settings_no_provider_returns_none() -> None:
    """GET returns provider_type='none' when no OCR provider is configured."""
    workspace = _make_workspace()
    workspace_repo = MagicMock()
    workspace_repo.get_with_members = AsyncMock(return_value=workspace)

    mock_key_storage = _make_key_storage(key_info=None)

    with patch(_WS_REPO_PATCH, return_value=workspace_repo):
        response = await router_get_ocr_settings(
            workspace_id=TEST_WORKSPACE_ID,
            current_user=_make_current_user(),
            session=_make_session(),
            key_storage=mock_key_storage,
        )

    assert response.provider_type == "none"
    assert response.is_configured is False


# ---------------------------------------------------------------------------
# PUT /workspaces/{id}/ocr/settings
# ---------------------------------------------------------------------------


async def test_put_ocr_settings_hunyuan_calls_store_api_key() -> None:
    """PUT with provider_type='hunyuan_ocr' calls store_api_key with service_type='ocr'."""
    workspace = _make_workspace()
    workspace_repo = MagicMock()
    workspace_repo.get_with_members = AsyncMock(return_value=workspace)

    mock_key_storage = _make_key_storage(
        key_info=_make_api_key_info(
            provider="hunyuan_ocr",
            base_url="http://localhost:8080/v1",
            model_name="tencent/HunyuanOCR",
        )
    )

    body = OcrSettingsUpdateRequest(
        provider_type="hunyuan_ocr",
        endpoint_url="http://localhost:8080/v1",
        api_key="test-key",  # pragma: allowlist secret
        model_name="tencent/HunyuanOCR",
    )

    with patch(_WS_REPO_PATCH, return_value=workspace_repo):
        response = await router_update_ocr_settings(
            workspace_id=TEST_WORKSPACE_ID,
            body=body,
            current_user=_make_current_user(),
            session=_make_session(),
            key_storage=mock_key_storage,
        )

    # Confirm store_api_key was called with service_type="ocr"
    mock_key_storage.store_api_key.assert_called_once()
    call_kwargs = mock_key_storage.store_api_key.call_args.kwargs
    assert call_kwargs["service_type"] == "ocr"
    assert call_kwargs["provider"] == "hunyuan_ocr"
    assert call_kwargs["api_key"] == "test-key"  # pragma: allowlist secret

    assert response.provider_type == "hunyuan_ocr"
    assert response.is_configured is True


# ---------------------------------------------------------------------------
# POST /workspaces/{id}/ocr/settings/test
# ---------------------------------------------------------------------------


async def test_post_ocr_test_returns_success() -> None:
    """POST /test calls validate_connection and returns success=True when valid."""
    workspace = _make_workspace()
    workspace_repo = MagicMock()
    workspace_repo.get_with_members = AsyncMock(return_value=workspace)

    mock_ocr_service = MagicMock()
    mock_ocr_service.validate_connection = AsyncMock(return_value=(True, None))

    body = OcrSettingsUpdateRequest(
        provider_type="hunyuan_ocr",
        endpoint_url="http://localhost:8080/v1",
        api_key="test-key",  # pragma: allowlist secret
    )

    mock_request = MagicMock()
    mock_request.app.state.container.encryption_key.return_value = "secret"

    with (
        patch(_WS_REPO_PATCH, return_value=workspace_repo),
        patch(
            "pilot_space.application.services.ai.ocr_service.OcrService",
            return_value=mock_ocr_service,
        ),
    ):
        response = await router_test_ocr_connection(
            workspace_id=TEST_WORKSPACE_ID,
            body=body,
            current_user=_make_current_user(),
            session=_make_session(),
            key_storage=_make_key_storage(),
            request=mock_request,
        )

    assert response.success is True
    assert response.error is None
    mock_ocr_service.validate_connection.assert_called_once()


async def test_post_ocr_test_returns_failure() -> None:
    """POST /test returns success=False with error message when connection fails."""
    workspace = _make_workspace()
    workspace_repo = MagicMock()
    workspace_repo.get_with_members = AsyncMock(return_value=workspace)

    mock_ocr_service = MagicMock()
    mock_ocr_service.validate_connection = AsyncMock(
        return_value=(False, "connection refused: http://localhost:8080")
    )

    body = OcrSettingsUpdateRequest(
        provider_type="hunyuan_ocr",
        endpoint_url="http://localhost:8080/v1",
        api_key="bad-key",  # pragma: allowlist secret
    )

    mock_request = MagicMock()
    mock_request.app.state.container.encryption_key.return_value = "secret"

    with (
        patch(_WS_REPO_PATCH, return_value=workspace_repo),
        patch(
            "pilot_space.application.services.ai.ocr_service.OcrService",
            return_value=mock_ocr_service,
        ),
    ):
        response = await router_test_ocr_connection(
            workspace_id=TEST_WORKSPACE_ID,
            body=body,
            current_user=_make_current_user(),
            session=_make_session(),
            key_storage=_make_key_storage(),
            request=mock_request,
        )

    assert response.success is False
    assert "connection refused" in (response.error or "")
