"""E2E test fixtures for AI endpoints.

Provides fixtures for testing complete AI workflows with SSE streaming.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from pilot_space.infrastructure.auth import TokenPayload
from pilot_space.main import app

# Test user ID for E2E tests (matches seed_demo.py real user)
_E2E_TEST_USER_ID = UUID("77a6813e-0aa3-400c-8d4e-540b6ed2187a")


@pytest.fixture
async def e2e_client() -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for E2E testing with mocked auth.

    Creates a fresh container for each test to avoid event loop issues
    with SSE streaming tests. Auth is mocked to return a consistent test user.

    Yields:
        AsyncClient for making requests.
    """
    # Reset and reinitialize DI container to ensure fresh state
    from pilot_space.container import get_container

    # Always create a fresh container to avoid event loop contamination
    app.state.container = get_container()

    # Override auth dependencies to return test user (replaces demo user fallback)
    from pilot_space.dependencies.auth import get_current_user, get_current_user_id

    now = datetime.now(tz=UTC)
    mock_payload = TokenPayload(
        sub=str(_E2E_TEST_USER_ID),
        email="test@pilot.space",
        role="authenticated",
        aud="authenticated",
        exp=int(now.timestamp() + 3600),
        iat=int(now.timestamp()),
        app_metadata={},
        user_metadata={"full_name": "Tin Dang"},
    )

    app.dependency_overrides[get_current_user] = lambda: mock_payload
    app.dependency_overrides[get_current_user_id] = lambda: _E2E_TEST_USER_ID

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Clean up overrides after test
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_current_user_id, None)
    if hasattr(app.state, "container"):
        delattr(app.state, "container")


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Create auth headers for E2E tests.

    Returns:
        Dictionary with auth and workspace headers.
    """
    return {
        "X-Workspace-ID": "00000000-0000-0000-0000-000000000002",
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
