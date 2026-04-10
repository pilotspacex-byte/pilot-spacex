"""Tests for AI memory telemetry admin endpoint (Phase 70 Wave 4).

Contract:

    1. ``GET /api/v1/workspaces/{wid}/ai/memory/telemetry`` (admin) returns
       memory stats, producer counters, and toggles.
    2. Non-admin members get 403.
    3. Admin PUT toggles updates the value.
    4. Non-admin PUT toggles returns 403.
    5. Unknown producer name returns 422.
    6. Route is registered with ``""`` (empty string), NOT ``"/"`` — no
       trailing slash causes 307 redirects.

Uses FastAPI dependency overrides (same pattern as test_ai_permissions_router).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from pilot_space.dependencies.auth import (
    get_current_user,
    get_session,
    require_workspace_admin,
    require_workspace_member,
)

WORKSPACE_ID = UUID("11111111-1111-1111-1111-111111111111")
USER_ID = UUID("22222222-2222-2222-2222-222222222222")

BASE = f"/api/v1/workspaces/{WORKSPACE_ID}/ai/memory/telemetry"

# ---------------------------------------------------------------------------
# Mock data for memory_metrics and toggles
# ---------------------------------------------------------------------------

_MOCK_SNAPSHOT = {
    "memory_recall.hit": 100,
    "memory_recall.miss": 50,
    "memory_recall.hit_rate": 0.667,
    "memory_recall.latency_ms.p95": 85.3,
    "memory_recall.latency_ms.samples": 150,
}

_MOCK_PRODUCER_COUNTERS = {
    "enqueued": {"agent_turn": 500, "user_correction": 45, "pr_review_finding": 120},
    "dropped": {"agent_turn::opt_out": 3, "pr_review_finding::enqueue_error": 1},
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def admin_client() -> AsyncGenerator[AsyncClient, None]:
    from pilot_space.main import app

    async def _noop_session() -> AsyncGenerator[Any, None]:
        yield MagicMock()

    mock_user = MagicMock()
    mock_user.user_id = USER_ID
    mock_user.sub = str(USER_ID)

    app.dependency_overrides[get_session] = _noop_session
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[require_workspace_admin] = lambda: WORKSPACE_ID
    app.dependency_overrides[require_workspace_member] = lambda: WORKSPACE_ID

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            headers={"Authorization": "Bearer test"},
        ) as client:
            yield client
    finally:
        for dep in (
            get_session,
            get_current_user,
            require_workspace_admin,
            require_workspace_member,
        ):
            app.dependency_overrides.pop(dep, None)


@pytest.fixture
async def member_client() -> AsyncGenerator[AsyncClient, None]:
    """Member client: admin dependency raises 403, member passes."""
    from fastapi import HTTPException, status

    from pilot_space.main import app

    async def _noop_session() -> AsyncGenerator[Any, None]:
        yield MagicMock()

    mock_user = MagicMock()
    mock_user.user_id = USER_ID
    mock_user.sub = str(USER_ID)

    def _deny_admin() -> UUID:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")

    app.dependency_overrides[get_session] = _noop_session
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[require_workspace_member] = lambda: WORKSPACE_ID
    app.dependency_overrides[require_workspace_admin] = _deny_admin

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            headers={"Authorization": "Bearer test"},
        ) as client:
            yield client
    finally:
        for dep in (
            get_session,
            get_current_user,
            require_workspace_admin,
            require_workspace_member,
        ):
            app.dependency_overrides.pop(dep, None)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@patch(
    "pilot_space.api.v1.routers.ai_memory_telemetry.memory_metrics.snapshot",
    return_value=_MOCK_SNAPSHOT,
)
@patch(
    "pilot_space.api.v1.routers.ai_memory_telemetry.memory_metrics.get_producer_counters",
    return_value=_MOCK_PRODUCER_COUNTERS,
)
@patch(
    "pilot_space.api.v1.routers.ai_memory_telemetry.get_producer_toggles",
    new_callable=AsyncMock,
)
async def test_admin_get_returns_hit_rate_and_producer_counters(
    mock_toggles: AsyncMock,
    mock_counters: MagicMock,
    mock_snapshot: MagicMock,
    admin_client: AsyncClient,
) -> None:
    from pilot_space.application.services.workspace_ai_settings_toggles import (
        ProducerToggles,
    )

    mock_toggles.return_value = ProducerToggles(
        agent_turn=True,
        user_correction=True,
        pr_review_finding=True,
        summarizer=False,
    )

    resp = await admin_client.get(BASE)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # Memory section
    assert "memory" in body
    assert body["memory"]["hit_rate"] == pytest.approx(0.667)
    assert body["memory"]["recall_p95_ms"] == pytest.approx(85.3)
    assert body["memory"]["total_recalls"] == 150  # hits + misses = 150 (samples)

    # Producers section
    assert "producers" in body
    assert body["producers"]["enqueued"]["agent_turn"] == 500

    # Toggles section
    assert "toggles" in body
    assert body["toggles"]["agent_turn"] is True
    assert body["toggles"]["summarizer"] is False


async def test_non_admin_gets_403(member_client: AsyncClient) -> None:
    resp = await member_client.get(BASE)
    assert resp.status_code == 403


@patch(
    "pilot_space.api.v1.routers.ai_memory_telemetry.set_producer_toggle",
    new_callable=AsyncMock,
)
async def test_admin_put_toggles_updates_value(
    mock_set: AsyncMock,
    admin_client: AsyncClient,
) -> None:
    from pilot_space.application.services.workspace_ai_settings_toggles import (
        ProducerToggles,
    )

    mock_set.return_value = ProducerToggles(
        agent_turn=False,
        user_correction=True,
        pr_review_finding=True,
        summarizer=False,
    )

    resp = await admin_client.put(
        f"{BASE}/toggles/agent_turn",
        json={"enabled": False},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["agent_turn"] is False
    assert body["user_correction"] is True

    mock_set.assert_called_once()


async def test_member_put_toggles_returns_403(member_client: AsyncClient) -> None:
    resp = await member_client.put(
        f"{BASE}/toggles/agent_turn",
        json={"enabled": False},
    )
    assert resp.status_code == 403


@patch(
    "pilot_space.api.v1.routers.ai_memory_telemetry.set_producer_toggle",
    new_callable=AsyncMock,
)
async def test_unknown_producer_returns_422(
    mock_set: AsyncMock,
    admin_client: AsyncClient,
) -> None:
    from pilot_space.domain.exceptions import ValidationError

    mock_set.side_effect = ValidationError("unknown memory producer: 'invalid_name'")

    resp = await admin_client.put(
        f"{BASE}/toggles/invalid_name",
        json={"enabled": True},
    )
    assert resp.status_code == 422, resp.text


async def test_root_path_has_no_trailing_slash_no_307(admin_client: AsyncClient) -> None:
    """Verify the route does NOT redirect on the trailing-slash-free path."""

    from pilot_space.api.v1.routers.ai_memory_telemetry import router

    # Check all GET routes use "" or a non-"/" path (no trailing slash)
    for route in router.routes:
        if hasattr(route, "path"):
            assert not route.path.endswith("/"), (
                f"Route {route.path} ends with / — causes 307 redirect footgun"
            )

    # Also verify the actual request (no 307)
    with patch(
        "pilot_space.api.v1.routers.ai_memory_telemetry.memory_metrics.snapshot",
        return_value=_MOCK_SNAPSHOT,
    ), patch(
        "pilot_space.api.v1.routers.ai_memory_telemetry.memory_metrics.get_producer_counters",
        return_value=_MOCK_PRODUCER_COUNTERS,
    ), patch(
        "pilot_space.api.v1.routers.ai_memory_telemetry.get_producer_toggles",
        new_callable=AsyncMock,
    ) as mock_toggles:
        from pilot_space.application.services.workspace_ai_settings_toggles import (
            ProducerToggles,
        )

        mock_toggles.return_value = ProducerToggles.defaults()
        resp = await admin_client.get(BASE)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code} (307 redirect?)"
