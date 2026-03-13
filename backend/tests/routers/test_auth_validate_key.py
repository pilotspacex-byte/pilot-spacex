"""Unit tests for POST /api/v1/auth/validate-key endpoint.

Tests HTTP boundary behaviour: correct status codes, header parsing,
and service delegation. Uses dependency_overrides to bypass DI container
and Supabase JWT middleware.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi import status

from pilot_space.application.services.auth import ValidateAPIKeyResult

pytestmark = pytest.mark.asyncio

_ENDPOINT = "/api/v1/auth/validate-key"


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_service() -> AsyncMock:
    """Mock ValidateAPIKeyService."""
    return AsyncMock()


@pytest.fixture
async def validate_key_client(mock_service: AsyncMock) -> AsyncGenerator[Any, None]:
    """HTTP test client with ValidateAPIKeyService and SessionDep overridden.

    The validate-key endpoint does NOT require Supabase JWT but does require
    a database session (SessionDep) to populate the ContextVar consumed by
    repository Factory providers. Both dependencies are overridden here so
    tests run without a real database connection.
    """
    from httpx import ASGITransport, AsyncClient

    from pilot_space.api.v1.dependencies_pilot import _get_validate_api_key_service
    from pilot_space.dependencies.auth import get_session
    from pilot_space.main import app

    mock_session = AsyncMock()

    async def _mock_session_gen() -> AsyncGenerator[Any, None]:
        yield mock_session

    app.dependency_overrides[_get_validate_api_key_service] = lambda: mock_service
    app.dependency_overrides[get_session] = _mock_session_gen

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.pop(_get_validate_api_key_service, None)
    app.dependency_overrides.pop(get_session, None)


# ============================================================================
# POST /api/v1/auth/validate-key
# ============================================================================


class TestValidateAPIKeyEndpoint:
    """Tests for the validate-key endpoint."""

    async def test_valid_key_returns_200_with_workspace_slug(
        self,
        validate_key_client: Any,
        mock_service: AsyncMock,
    ) -> None:
        """Valid key returns HTTP 200 with workspace_slug in body."""
        mock_service.execute.return_value = ValidateAPIKeyResult(
            workspace_slug="acme",
            user_id="00000000-0000-0000-0000-000000000001",
        )

        response = await validate_key_client.post(
            _ENDPOINT,
            headers={"Authorization": "Bearer ps_valid_key"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"workspace_slug": "acme"}

    async def test_missing_authorization_header_returns_401(
        self,
        validate_key_client: Any,
    ) -> None:
        """Request without Authorization header returns 401."""
        response = await validate_key_client.post(_ENDPOINT)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_non_bearer_authorization_returns_401(
        self,
        validate_key_client: Any,
    ) -> None:
        """Authorization header without 'Bearer ' prefix returns 401."""
        response = await validate_key_client.post(
            _ENDPOINT,
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_invalid_key_service_raises_value_error_returns_401(
        self,
        validate_key_client: Any,
        mock_service: AsyncMock,
    ) -> None:
        """Service raising ValueError maps to HTTP 401."""
        mock_service.execute.side_effect = ValueError("invalid_api_key")

        response = await validate_key_client.post(
            _ENDPOINT,
            headers={"Authorization": "Bearer ps_bad_key"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_expired_key_service_raises_value_error_returns_401(
        self,
        validate_key_client: Any,
        mock_service: AsyncMock,
    ) -> None:
        """Service raising ValueError for expired key maps to HTTP 401."""
        mock_service.execute.side_effect = ValueError("expired_api_key")

        response = await validate_key_client.post(
            _ENDPOINT,
            headers={"Authorization": "Bearer ps_expired"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_raw_key_stripped_from_bearer_prefix_before_service_call(
        self,
        validate_key_client: Any,
        mock_service: AsyncMock,
    ) -> None:
        """The router strips 'Bearer ' before passing raw_key to the service."""
        from pilot_space.application.services.auth import ValidateAPIKeyPayload

        mock_service.execute.return_value = ValidateAPIKeyResult(
            workspace_slug="ws",
            user_id="00000000-0000-0000-0000-000000000002",
        )

        await validate_key_client.post(
            _ENDPOINT,
            headers={"Authorization": "Bearer ps_my_token_123"},
        )

        mock_service.execute.assert_awaited_once()
        call_arg: ValidateAPIKeyPayload = mock_service.execute.call_args[0][0]
        assert call_arg.raw_key == "ps_my_token_123"

    async def test_401_does_not_leak_key_value(
        self,
        validate_key_client: Any,
        mock_service: AsyncMock,
    ) -> None:
        """Error response body must not contain the raw API key value."""
        mock_service.execute.side_effect = ValueError("invalid_api_key")
        raw_key = "ps_super_secret_key"

        response = await validate_key_client.post(
            _ENDPOINT,
            headers={"Authorization": f"Bearer {raw_key}"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert raw_key not in response.text
