"""OPS-03: Two-tier health check endpoint tests.

Tests for:
- GET /health/live  — shallow liveness probe (no external deps)
- GET /health/ready — deep readiness probe with dependency checks
- GET /health       — legacy alias for /health/ready
- Auth bypass       — all health endpoints accessible without JWT

All dependency check functions are mocked at the router import level to
isolate tests from external infrastructure (DB, Redis, Supabase).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def health_client() -> AsyncGenerator[AsyncClient, None]:
    """HTTP client against the FastAPI app — no auth headers."""
    from pilot_space.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),  # type: ignore[arg-type]
        base_url="http://test",
    ) as client:
        yield client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_OK = {"status": "ok", "latency_ms": 1.0}
_ERR = {"status": "error", "error": "connection refused"}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_liveness(health_client: AsyncClient) -> None:
    """GET /health/live returns 200 with {status: ok} — no external deps."""
    response = await health_client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_readiness_healthy(health_client: AsyncClient) -> None:
    """GET /health/ready returns 200 with status=healthy when all checks pass."""
    with (
        patch(
            "pilot_space.api.routers.health.check_database",
            new=AsyncMock(return_value=_OK),
        ),
        patch(
            "pilot_space.api.routers.health.check_redis",
            new=AsyncMock(return_value=_OK),
        ),
        patch(
            "pilot_space.api.routers.health.check_supabase",
            new=AsyncMock(return_value=_OK),
        ),
    ):
        response = await health_client.get("/health/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"
    assert "timestamp" in data
    assert "database" in data["checks"]
    assert "redis" in data["checks"]
    assert "supabase" in data["checks"]


async def test_readiness_db_down(health_client: AsyncClient) -> None:
    """GET /health/ready returns status=unhealthy when database check fails."""
    with (
        patch(
            "pilot_space.api.routers.health.check_database",
            new=AsyncMock(return_value=_ERR),
        ),
        patch(
            "pilot_space.api.routers.health.check_redis",
            new=AsyncMock(return_value=_OK),
        ),
        patch(
            "pilot_space.api.routers.health.check_supabase",
            new=AsyncMock(return_value=_OK),
        ),
    ):
        response = await health_client.get("/health/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["checks"]["database"]["status"] == "error"


async def test_readiness_degraded(health_client: AsyncClient) -> None:
    """GET /health/ready returns status=degraded when only supabase check fails."""
    with (
        patch(
            "pilot_space.api.routers.health.check_database",
            new=AsyncMock(return_value=_OK),
        ),
        patch(
            "pilot_space.api.routers.health.check_redis",
            new=AsyncMock(return_value=_OK),
        ),
        patch(
            "pilot_space.api.routers.health.check_supabase",
            new=AsyncMock(return_value=_ERR),
        ),
    ):
        response = await health_client.get("/health/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["checks"]["supabase"]["status"] == "error"


async def test_legacy_health_route(health_client: AsyncClient) -> None:
    """GET /health returns same structure as /health/ready (deep check, not old stub)."""
    with (
        patch(
            "pilot_space.api.routers.health.check_database",
            new=AsyncMock(return_value=_OK),
        ),
        patch(
            "pilot_space.api.routers.health.check_redis",
            new=AsyncMock(return_value=_OK),
        ),
        patch(
            "pilot_space.api.routers.health.check_supabase",
            new=AsyncMock(return_value=_OK),
        ),
    ):
        response = await health_client.get("/health")

    assert response.status_code == 200
    data = response.json()
    # Must have the new deep-check structure, not the old {"status": "healthy"}
    assert "checks" in data
    assert "version" in data
    assert "timestamp" in data


async def test_health_no_auth_required(health_client: AsyncClient) -> None:
    """GET /health/live and /health/ready return 200 without Authorization header."""
    with (
        patch(
            "pilot_space.api.routers.health.check_database",
            new=AsyncMock(return_value=_OK),
        ),
        patch(
            "pilot_space.api.routers.health.check_redis",
            new=AsyncMock(return_value=_OK),
        ),
        patch(
            "pilot_space.api.routers.health.check_supabase",
            new=AsyncMock(return_value=_OK),
        ),
    ):
        live_response = await health_client.get("/health/live")
        ready_response = await health_client.get("/health/ready")

    # Neither endpoint requires auth
    assert live_response.status_code == 200
    assert ready_response.status_code == 200
    # Specifically NOT 401 or 403
    assert live_response.status_code != 401
    assert ready_response.status_code != 401
