"""E2E test fixtures for AI endpoints.

Provides fixtures for testing complete AI workflows with SSE streaming.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from pilot_space.main import app

if TYPE_CHECKING:
    from pilot_space.infrastructure.auth import TokenPayload


@pytest.fixture
async def e2e_client() -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for E2E testing.

    Creates a fresh container for each test to avoid event loop issues
    with SSE streaming tests.

    Yields:
        AsyncClient for making requests.
    """
    # Reset and reinitialize DI container to ensure fresh state
    from pilot_space.container import get_container

    # Always create a fresh container to avoid event loop contamination
    app.state.container = get_container()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Clean up app state after test
    if hasattr(app.state, "container"):
        delattr(app.state, "container")


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Create auth headers for E2E tests.

    Uses demo workspace for simplicity.

    Returns:
        Dictionary with auth and workspace headers.
    """
    return {
        "X-Workspace-ID": "pilot-space-demo",
        "X-Anthropic-API-Key": "test-anthropic-key",
        "X-Google-API-Key": "test-google-key",
        "X-OpenAI-API-Key": "test-openai-key",
    }


@pytest.fixture
def test_note() -> MagicMock:
    """Create test note data.

    Returns:
        Mock Note object.
    """
    return MagicMock(
        id=uuid4(),
        title="Feature Planning",
        content={
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "We need to implement user authentication with OAuth2 support.",
                        }
                    ],
                }
            ],
        },
    )


@pytest.fixture
def test_issue() -> MagicMock:
    """Create test issue data.

    Returns:
        Mock Issue object.
    """
    return MagicMock(
        id=uuid4(),
        title="Implement authentication",
        description="Add OAuth2 authentication to the application",
        state="in_progress",
    )


@pytest.fixture
def test_repo() -> MagicMock:
    """Create test repository data.

    Returns:
        Mock repository object.
    """
    return MagicMock(
        id=uuid4(),
        name="pilot-space",
        full_name="tindang/pilot-space",
        owner="tindang",
    )


@pytest.fixture
def test_pr() -> MagicMock:
    """Create test pull request data.

    Returns:
        Mock PR object.
    """
    return MagicMock(
        number=123,
        title="Add authentication feature",
        description="Implements OAuth2 authentication",
        head_sha="abc123",
        base_sha="def456",
    )


@pytest.fixture
def test_approval() -> MagicMock:
    """Create test approval request.

    Returns:
        Mock approval object.
    """
    return MagicMock(
        id=uuid4(),
        agent_name="issue_extractor",
        action_type="extract_issues",
        status="pending",
        payload={
            "issues": [
                {"title": "Issue 1", "description": "First issue"},
                {"title": "Issue 2", "description": "Second issue"},
            ]
        },
    )


@pytest.fixture
def mock_e2e_auth(mock_token_payload: TokenPayload) -> Any:
    """Mock authentication for E2E tests.

    Patches auth dependencies to allow test API keys.

    Args:
        mock_token_payload: Token payload fixture.

    Yields:
        Mock auth context.
    """
    with (
        patch(
            "pilot_space.api.dependencies.get_current_user",
            return_value=mock_token_payload,
        ),
        patch(
            "pilot_space.api.dependencies.verify_api_key",
            return_value=mock_token_payload,
        ),
        patch(
            "pilot_space.dependencies.get_current_user",
            return_value=mock_token_payload,
        ),
        patch(
            "pilot_space.dependencies.verify_api_key",
            return_value=mock_token_payload,
        ),
    ):
        yield


@pytest.fixture
async def e2e_client_with_mock_auth(
    app: Any,
    auth_headers: dict[str, str],
    mock_e2e_auth: Any,
) -> AsyncGenerator[AsyncClient, None]:
    """Create E2E client with mocked auth.

    Args:
        app: FastAPI app.
        auth_headers: Auth headers.
        mock_e2e_auth: Mock auth fixture.

    Yields:
        Authenticated AsyncClient.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers=auth_headers,
    ) as ac:
        yield ac


__all__ = [
    "auth_headers",
    "e2e_client",
    "e2e_client_with_mock_auth",
    "mock_e2e_auth",
    "test_approval",
    "test_issue",
    "test_note",
    "test_pr",
    "test_repo",
]
