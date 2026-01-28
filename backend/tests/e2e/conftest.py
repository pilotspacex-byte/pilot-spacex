"""Shared E2E test fixtures with Redis mocking.

Provides:
- test_e2e_client: HTTP client with mocked Redis for E2E tests
- Redis mock that works with SessionManager and other Redis-dependent services
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def test_e2e_client() -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for E2E testing with mocked Redis.

    This fixture ensures Redis-dependent services (SessionManager, ApprovalService, etc.)
    work properly in E2E tests by providing a working in-memory Redis mock.

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

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Clean up container overrides and app state after test
    container.redis_client.reset_override()
    if hasattr(app.state, "container"):
        delattr(app.state, "container")
