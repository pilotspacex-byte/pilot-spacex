"""API-level test fixtures.

Overrides the FastAPI app's `get_session` dependency to use the SQLite
in-memory test engine, allowing API-layer integration tests to run without
a real PostgreSQL instance.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker


@pytest.fixture
async def app_with_test_db(test_engine: AsyncEngine) -> AsyncGenerator[Any, None]:
    """FastAPI app with DB session overridden to use the SQLite test engine.

    Overrides ``get_session`` so every route handler receives a session bound
    to the same in-memory SQLite database as the test fixtures, enabling
    real end-to-end flow without an external PostgreSQL server.

    Yields:
        FastAPI application with session dependency overridden.
    """
    from collections.abc import AsyncGenerator as _AG

    from pilot_space.dependencies.auth import get_session
    from pilot_space.main import app

    # Build a session factory using the test engine
    session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async def _test_session() -> _AG[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = _test_session

    yield app

    app.dependency_overrides.pop(get_session, None)


@pytest.fixture
async def mcp_api_client(
    app_with_test_db: Any,
) -> AsyncGenerator[Any, None]:
    """Authenticated HTTP test client wired to the SQLite test DB.

    Used by Phase 25 MCP API tests that require a real DB session (not mocks)
    but don't need a live PostgreSQL server.

    Yields:
        httpx.AsyncClient with auth headers.
    """
    from unittest.mock import MagicMock

    from httpx import ASGITransport, AsyncClient

    from pilot_space.dependencies.auth import get_current_user
    from pilot_space.infrastructure.auth.models import TokenPayload

    # Create a minimal mock token
    mock_payload = MagicMock(spec=TokenPayload)
    mock_payload.sub = "test-user-id"
    mock_payload.user_id = None  # Will be set by test fixtures

    app_with_test_db.dependency_overrides[get_current_user] = lambda: mock_payload

    transport = ASGITransport(app=app_with_test_db)
    try:
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            headers={"Authorization": "Bearer test-token"},
        ) as ac:
            yield ac
    finally:
        app_with_test_db.dependency_overrides.pop(get_current_user, None)
