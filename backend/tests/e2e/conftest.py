"""Shared E2E test fixtures with Redis mocking and auth override.

Provides:
- test_e2e_client: HTTP client with mocked Redis and auth for E2E tests
- Redis mock that works with SessionManager and other Redis-dependent services
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from pilot_space.infrastructure.auth import TokenPayload

# Test user ID for E2E tests (matches seed_demo.py real user)
E2E_TEST_USER_ID = UUID("77a6813e-0aa3-400c-8d4e-540b6ed2187a")
E2E_TEST_WORKSPACE_ID = "00000000-0000-0000-0000-000000000002"


@pytest.fixture
async def test_e2e_client() -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for E2E testing with mocked Redis and auth.

    This fixture ensures Redis-dependent services (SessionManager, ApprovalService, etc.)
    work properly in E2E tests by providing a working in-memory Redis mock.
    Auth is mocked to return a consistent test user.

    Yields:
        AsyncClient for making requests to the test application.
    """
    from pilot_space.container import get_container
    from pilot_space.main import app

    # Create in-memory cache for Redis mock
    redis_cache: dict[str, Any] = {}

    # Create mock Redis client with working operations
    mock_redis_client = MagicMock()
    mock_redis_client.get = AsyncMock(side_effect=lambda key: redis_cache.get(key))

    def mock_set(key: str, value: Any, **_kwargs: Any) -> bool:
        redis_cache[key] = value
        return True

    mock_redis_client.set = AsyncMock(side_effect=mock_set)
    mock_redis_client.delete = AsyncMock(
        side_effect=lambda key: redis_cache.pop(key, None) is not None
    )
    mock_redis_client.expire = AsyncMock(return_value=True)
    mock_redis_client.close = AsyncMock()

    # Reset and reinitialize DI container with mocked Redis
    container = get_container()
    container.redis_client.override(mock_redis_client)
    app.state.container = container

    # Override auth dependencies to return test user (replaces demo user fallback)
    from pilot_space.dependencies.auth import get_current_user, get_current_user_id

    now = datetime.now(tz=UTC)
    mock_payload = TokenPayload(
        sub=str(E2E_TEST_USER_ID),
        email="test@pilot.space",
        role="authenticated",
        aud="authenticated",
        exp=int(now.timestamp() + 3600),
        iat=int(now.timestamp()),
        app_metadata={},
        user_metadata={"full_name": "Tin Dang"},
    )

    app.dependency_overrides[get_current_user] = lambda: mock_payload
    app.dependency_overrides[get_current_user_id] = lambda: E2E_TEST_USER_ID

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Clean up overrides after test
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_current_user_id, None)
    container.redis_client.reset_override()
    if hasattr(app.state, "container"):
        delattr(app.state, "container")
