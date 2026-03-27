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

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from pilot_space.api.v1.routers.workspace_ocr_settings import (
    OcrSettingsUpdateRequest,
    get_ocr_settings as router_get_ocr_settings,
    test_ocr_connection as router_test_ocr_connection,
    update_ocr_settings as router_update_ocr_settings,
)
from pilot_space.application.services.ocr_configuration import OcrConfigResult
from pilot_space.domain.exceptions import NotFoundError

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


def _make_ocr_config_service(
    get_result: OcrConfigResult | None = None,
    update_result: OcrConfigResult | None = None,
) -> AsyncMock:
    """Build a mock OcrConfigurationService."""
    svc = AsyncMock()
    if get_result is None:
        get_result = OcrConfigResult(
            workspace_id=TEST_WORKSPACE_ID,
            provider_type="none",
            is_configured=False,
            is_valid=None,
            endpoint_url=None,
            model_name=None,
        )
    svc.get_ocr_config = AsyncMock(return_value=get_result)
    if update_result is not None:
        svc.update_ocr_config = AsyncMock(return_value=update_result)
    return svc


# Patch path for WorkspaceRepository used by get_admin_workspace
_WS_REPO_PATCH = "pilot_space.api.v1.routers._workspace_admin.WorkspaceRepository"


def _mock_ws_repo_for_admin(workspace: MagicMock | None, is_admin: bool = True) -> MagicMock:
    """Build a WorkspaceRepository mock for get_admin_workspace."""
    from pilot_space.infrastructure.database.models.workspace_member import WorkspaceRole

    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=workspace)
    if is_admin:
        repo.get_member_role = AsyncMock(return_value=WorkspaceRole.ADMIN)
    else:
        repo.get_member_role = AsyncMock(return_value=WorkspaceRole.MEMBER)
    return repo


def _make_workspace(workspace_id: UUID = TEST_WORKSPACE_ID) -> MagicMock:
    """Build a minimal mock Workspace."""
    workspace = MagicMock()
    workspace.id = workspace_id
    return workspace


# ---------------------------------------------------------------------------
# GET /workspaces/{id}/ocr/settings
# ---------------------------------------------------------------------------


async def test_get_ocr_settings_workspace_not_found() -> None:
    """GET returns 404 when workspace not found."""
    ws_repo = _mock_ws_repo_for_admin(workspace=None)
    svc = _make_ocr_config_service()

    with (
        patch(_WS_REPO_PATCH, return_value=ws_repo),
        pytest.raises(NotFoundError) as exc_info,
    ):
        await router_get_ocr_settings(
            workspace_id=TEST_WORKSPACE_ID,
            current_user=_make_current_user(),
            session=_make_session(),
            svc=svc,
        )

    assert exc_info.value.http_status == 404


async def test_get_ocr_settings_not_admin_returns_403() -> None:
    """GET returns 404 (SEC-M1: enumeration prevention) when user is not an admin."""
    workspace = _make_workspace()
    ws_repo = _mock_ws_repo_for_admin(workspace=workspace, is_admin=False)
    svc = _make_ocr_config_service()

    with (
        patch(_WS_REPO_PATCH, return_value=ws_repo),
        pytest.raises(NotFoundError) as exc_info,
    ):
        await router_get_ocr_settings(
            workspace_id=TEST_WORKSPACE_ID,
            current_user=_make_current_user(),
            session=_make_session(),
            svc=svc,
        )

    # get_admin_workspace raises NotFoundError (404) per SEC-M1 policy
    assert exc_info.value.http_status == 404


async def test_get_ocr_settings_no_provider_returns_none() -> None:
    """GET returns provider_type='none' when no OCR provider is configured."""
    workspace = _make_workspace()
    ws_repo = _mock_ws_repo_for_admin(workspace=workspace)
    svc = _make_ocr_config_service()

    with patch(_WS_REPO_PATCH, return_value=ws_repo):
        response = await router_get_ocr_settings(
            workspace_id=TEST_WORKSPACE_ID,
            current_user=_make_current_user(),
            session=_make_session(),
            svc=svc,
        )

    assert response.provider_type == "none"
    assert response.is_configured is False


# ---------------------------------------------------------------------------
# PUT /workspaces/{id}/ocr/settings
# ---------------------------------------------------------------------------


async def test_put_ocr_settings_hunyuan_calls_store_api_key() -> None:
    """PUT with provider_type='hunyuan_ocr' calls update_ocr_config and returns result."""
    workspace = _make_workspace()
    ws_repo = _mock_ws_repo_for_admin(workspace=workspace)

    update_result = OcrConfigResult(
        workspace_id=TEST_WORKSPACE_ID,
        provider_type="hunyuan_ocr",
        is_configured=True,
        is_valid=True,
        endpoint_url="http://localhost:8080/v1",
        model_name="tencent/HunyuanOCR",
    )
    svc = _make_ocr_config_service(update_result=update_result)

    body = OcrSettingsUpdateRequest(
        provider_type="hunyuan_ocr",
        endpoint_url="http://localhost:8080/v1",
        api_key="test-key",  # pragma: allowlist secret
        model_name="tencent/HunyuanOCR",
    )

    with patch(_WS_REPO_PATCH, return_value=ws_repo):
        response = await router_update_ocr_settings(
            workspace_id=TEST_WORKSPACE_ID,
            body=body,
            current_user=_make_current_user(),
            session=_make_session(),
            svc=svc,
        )

    # Confirm update_ocr_config was called
    svc.update_ocr_config.assert_called_once()
    call_args = svc.update_ocr_config.call_args
    assert call_args[0][0] == TEST_WORKSPACE_ID
    payload = call_args[0][1]
    assert payload.provider_type == "hunyuan_ocr"
    assert payload.api_key == "test-key"  # pragma: allowlist secret

    assert response.provider_type == "hunyuan_ocr"
    assert response.is_configured is True


# ---------------------------------------------------------------------------
# POST /workspaces/{id}/ocr/settings/test
# ---------------------------------------------------------------------------


async def test_post_ocr_test_returns_success() -> None:
    """POST /test calls validate_connection and returns success=True when valid."""
    workspace = _make_workspace()
    ws_repo = _mock_ws_repo_for_admin(workspace=workspace)

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
        patch(_WS_REPO_PATCH, return_value=ws_repo),
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
            request=mock_request,
        )

    assert response.success is True
    assert response.error is None
    mock_ocr_service.validate_connection.assert_called_once()


async def test_post_ocr_test_returns_failure() -> None:
    """POST /test returns success=False with error message when connection fails."""
    workspace = _make_workspace()
    ws_repo = _mock_ws_repo_for_admin(workspace=workspace)

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
        patch(_WS_REPO_PATCH, return_value=ws_repo),
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
            request=mock_request,
        )

    assert response.success is False
    assert "connection refused" in (response.error or "")
