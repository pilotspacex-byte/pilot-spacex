"""TENANT-04: Super-admin operator dashboard API tests.

Router-level tests for the internal admin API:
- GET /api/v1/admin/workspaces — list all workspaces with metrics
- Authentication via super-admin token (not workspace JWT)
- Token must not appear in structured logs

Tests use dependency_overrides to bypass DB layer and mock Redis.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.asyncio

_VALID_TOKEN = "test-super-admin-token-12345"
_WORKSPACE_ID = uuid4()
_WORKSPACE_ID_2 = uuid4()

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def admin_client(monkeypatch: pytest.MonkeyPatch) -> AsyncGenerator[AsyncClient, None]:
    """HTTP client with PILOT_SPACE_SUPER_ADMIN_TOKEN set in settings."""
    from pilot_space.config import get_settings
    from pilot_space.main import app

    # Clear settings cache so the token value is picked up
    get_settings.cache_clear()
    monkeypatch.setenv("PILOT_SPACE_SUPER_ADMIN_TOKEN", _VALID_TOKEN)
    # Re-clear after env is set to ensure fresh settings with new token
    get_settings.cache_clear()

    async with AsyncClient(
        transport=ASGITransport(app=app),  # type: ignore[arg-type]
        base_url="http://test",
    ) as client:
        yield client

    # Cleanup: restore cache clear so other tests get fresh settings
    get_settings.cache_clear()


@pytest.fixture
def mock_workspace_rows() -> list[dict[str, Any]]:
    """Mock DB rows returned by the admin workspace list query."""
    return [
        {
            "id": str(_WORKSPACE_ID),
            "name": "Acme Corp",
            "slug": "acme",
            "created_at": datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
            "member_count": 5,
            "owner_email": "owner@acme.com",
            "last_active": datetime(2024, 6, 1, 8, 30, 0, tzinfo=UTC),
            "storage_used_bytes": 1024 * 1024 * 50,  # 50 MB
            "ai_action_count": 120,
        },
        {
            "id": str(_WORKSPACE_ID_2),
            "name": "Beta Corp",
            "slug": "beta",
            "created_at": datetime(2024, 2, 20, 9, 0, 0, tzinfo=UTC),
            "member_count": 2,
            "owner_email": None,
            "last_active": None,
            "storage_used_bytes": 0,
            "ai_action_count": 0,
        },
    ]


# ---------------------------------------------------------------------------
# Task 1: get_super_admin dependency + SecretStr token in settings
# ---------------------------------------------------------------------------


async def test_admin_workspaces_requires_super_admin_token(
    admin_client: AsyncClient,
) -> None:
    """GET /api/v1/admin/workspaces without Authorization header returns 401."""
    # Auth check in get_super_admin happens before service is invoked — no DB patching needed
    response = await admin_client.get("/api/v1/admin/workspaces")

    assert response.status_code == 401


async def test_invalid_super_admin_token_returns_401(
    admin_client: AsyncClient,
) -> None:
    """GET /api/v1/admin/workspaces with wrong token returns 401."""
    # Auth check in get_super_admin happens before service is invoked — no DB patching needed
    response = await admin_client.get(
        "/api/v1/admin/workspaces",
        headers={"Authorization": "Bearer wrong-token-value"},
    )

    assert response.status_code == 401


async def test_super_admin_token_is_secret_str() -> None:
    """PILOT_SPACE_SUPER_ADMIN_TOKEN is SecretStr — repr() does not expose value."""
    from pydantic import SecretStr

    from pilot_space.config import Settings

    settings = Settings(pilot_space_super_admin_token=_VALID_TOKEN)  # type: ignore[arg-type]
    token = settings.pilot_space_super_admin_token

    assert isinstance(token, SecretStr)
    assert _VALID_TOKEN not in repr(token)
    assert _VALID_TOKEN not in str(token)
    # But get_secret_value() works
    assert token.get_secret_value() == _VALID_TOKEN


async def test_super_admin_none_token_returns_401(admin_client: AsyncClient) -> None:
    """Settings with PILOT_SPACE_SUPER_ADMIN_TOKEN=None disables super-admin access."""
    from pilot_space.config import get_settings

    get_settings.cache_clear()

    with patch("pilot_space.dependencies.admin.get_settings") as mock_get_settings:
        mock_settings = MagicMock()
        mock_settings.pilot_space_super_admin_token = None
        mock_get_settings.return_value = mock_settings

        response = await admin_client.get(
            "/api/v1/admin/workspaces",
            headers={"Authorization": f"Bearer {_VALID_TOKEN}"},
        )

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Task 2: Super-admin router — workspace list and detail
# ---------------------------------------------------------------------------


async def test_valid_super_admin_token_returns_workspace_list(
    admin_client: AsyncClient,
    mock_workspace_rows: list[dict[str, Any]],
) -> None:
    """GET /api/v1/admin/workspaces with valid token returns list with metrics."""
    from pilot_space.api.v1.dependencies import _get_admin_dashboard_service
    from pilot_space.main import app
    from pilot_space.schemas.admin_dashboard import WorkspaceOverview

    # Build expected WorkspaceOverview list from mock rows
    expected = [
        WorkspaceOverview(
            id=row["id"],
            name=row["name"],
            slug=row["slug"],
            created_at=row["created_at"],
            member_count=row["member_count"],
            owner_email=row.get("owner_email"),
            last_active=row.get("last_active"),
            storage_used_bytes=row["storage_used_bytes"],
            ai_action_count=row["ai_action_count"],
            rate_limit_violation_count=0,
        )
        for row in mock_workspace_rows
    ]

    mock_svc = AsyncMock()
    mock_svc.list_workspaces = AsyncMock(return_value=expected)

    app.dependency_overrides[_get_admin_dashboard_service] = lambda: mock_svc
    try:
        response = await admin_client.get(
            "/api/v1/admin/workspaces",
            headers={"Authorization": f"Bearer {_VALID_TOKEN}"},
        )
    finally:
        app.dependency_overrides.pop(_get_admin_dashboard_service, None)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Each workspace must have required fields
    required_fields = {
        "id",
        "name",
        "slug",
        "created_at",
        "member_count",
        "storage_used_bytes",
        "ai_action_count",
        "rate_limit_violation_count",
    }
    for ws in data:
        assert required_fields.issubset(ws.keys()), f"Missing fields: {required_fields - ws.keys()}"


async def test_workspace_detail_returns_expanded_data(
    admin_client: AsyncClient,
) -> None:
    """GET /api/v1/admin/workspaces/{slug} returns workspace detail."""
    from pilot_space.api.v1.dependencies import _get_admin_dashboard_service
    from pilot_space.main import app
    from pilot_space.schemas.admin_dashboard import QuotaConfig, WorkspaceDetail

    slug = "acme"
    expected_detail = WorkspaceDetail(
        id=_WORKSPACE_ID,
        name="Acme Corp",
        slug=slug,
        created_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
        member_count=5,
        owner_email="owner@acme.com",
        last_active=datetime(2024, 6, 1, 8, 30, 0, tzinfo=UTC),
        storage_used_bytes=1024 * 1024 * 50,
        ai_action_count=120,
        rate_limit_violation_count=0,
        quota=QuotaConfig(
            rate_limit_standard_rpm=None,
            rate_limit_ai_rpm=None,
            storage_quota_mb=None,
        ),
        top_members=[],
        recent_ai_actions=[],
    )

    mock_svc = AsyncMock()
    mock_svc.get_workspace_detail = AsyncMock(return_value=expected_detail)

    app.dependency_overrides[_get_admin_dashboard_service] = lambda: mock_svc
    try:
        response = await admin_client.get(
            f"/api/v1/admin/workspaces/{slug}",
            headers={"Authorization": f"Bearer {_VALID_TOKEN}"},
        )
    finally:
        app.dependency_overrides.pop(_get_admin_dashboard_service, None)

    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == slug
    assert "top_members" in data
    assert "recent_ai_actions" in data
    assert "rate_limit_violation_count" in data


async def test_workspace_detail_not_found_returns_404(
    admin_client: AsyncClient,
) -> None:
    """GET /api/v1/admin/workspaces/{slug} with unknown slug returns 404."""
    from pilot_space.api.v1.dependencies import _get_admin_dashboard_service
    from pilot_space.domain.exceptions import NotFoundError
    from pilot_space.main import app

    mock_svc = AsyncMock()
    mock_svc.get_workspace_detail = AsyncMock(
        side_effect=NotFoundError("Workspace 'nonexistent-slug' not found")
    )

    app.dependency_overrides[_get_admin_dashboard_service] = lambda: mock_svc
    try:
        response = await admin_client.get(
            "/api/v1/admin/workspaces/nonexistent-slug",
            headers={"Authorization": f"Bearer {_VALID_TOKEN}"},
        )
    finally:
        app.dependency_overrides.pop(_get_admin_dashboard_service, None)

    assert response.status_code == 404


async def test_super_admin_token_masked_in_logs(
    admin_client: AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Structured log entry for admin request does not include raw token value."""
    from pilot_space.api.v1.dependencies import _get_admin_dashboard_service
    from pilot_space.main import app

    mock_svc = AsyncMock()
    mock_svc.list_workspaces = AsyncMock(return_value=[])

    app.dependency_overrides[_get_admin_dashboard_service] = lambda: mock_svc
    try:
        with caplog.at_level(logging.INFO, logger="pilot_space.api.v1.routers.admin"):
            await admin_client.get(
                "/api/v1/admin/workspaces",
                headers={"Authorization": f"Bearer {_VALID_TOKEN}"},
            )
    finally:
        app.dependency_overrides.pop(_get_admin_dashboard_service, None)

    # Token must not appear in log output
    full_log = " ".join(record.getMessage() for record in caplog.records)
    assert _VALID_TOKEN not in full_log
