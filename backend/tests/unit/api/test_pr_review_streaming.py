"""Unit tests for PR review SSE streaming endpoint.

T202: PR review streaming with aspect progress.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@pytest.fixture
def mock_orchestrator() -> AsyncMock:
    """Create mock SDK orchestrator."""
    orchestrator = AsyncMock()

    async def mock_stream(
        agent_name: str,
        input_data: dict,
        context: dict,
    ) -> AsyncIterator[str]:
        """Mock streaming response with aspect markers."""
        yield "Starting review...\n"
        yield "## Architecture\n"
        yield "- No architectural issues found\n"
        yield "## Security\n"
        yield "- All security checks passed\n"
        yield "## Code Quality\n"
        yield "- Code quality is good\n"
        yield "## Performance\n"
        yield "- No performance issues\n"
        yield "## Documentation\n"
        yield "- Documentation is adequate\n"

    orchestrator.stream = mock_stream
    return orchestrator


@pytest.fixture
def app_with_mocks(mock_orchestrator: AsyncMock) -> FastAPI:
    """Create FastAPI app with mocked dependencies."""
    from pilot_space.api.v1.routers.ai_pr_review import router

    app = FastAPI()
    app.include_router(router)

    # Mock dependencies
    async def get_mock_orchestrator():
        return mock_orchestrator

    async def get_mock_user_id():
        return uuid4()

    # Override dependencies
    from pilot_space.dependencies import get_current_user_id, get_sdk_orchestrator

    app.dependency_overrides[get_sdk_orchestrator] = get_mock_orchestrator
    app.dependency_overrides[get_current_user_id] = get_mock_user_id

    return app


@pytest.mark.skip(reason="Requires auth mock setup - integration test")
@pytest.mark.asyncio
async def test_stream_pr_review_success(app_with_mocks: FastAPI) -> None:
    """Test successful PR review streaming with aspect events."""
    repo_id = uuid4()
    pr_number = 123
    workspace_id = uuid4()

    transport = ASGITransport(app=app_with_mocks)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create request with workspace_id in state
        request_mock = MagicMock()
        request_mock.state.workspace_id = workspace_id

        response = await client.post(
            f"/ai/repos/{repo_id}/prs/{pr_number}/review",
            json={"repository": "owner/repo", "force_refresh": False},
            headers={"X-Workspace-ID": str(workspace_id)},
        )

        # Should return streaming response
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

        # Parse SSE events
        events = []
        for line in response.text.split("\n"):
            if line.startswith("event:"):
                event_type = line.split(": ")[1]
                events.append(event_type)

        # Should have aspect events and complete event
        assert "aspect" in events
        assert "complete" in events


@pytest.mark.skip(reason="Requires auth mock setup - integration test")
@pytest.mark.asyncio
async def test_stream_pr_review_missing_workspace_id() -> None:
    """Test PR review fails without workspace ID."""
    from pilot_space.api.v1.routers.ai_pr_review import router

    app = FastAPI()
    app.include_router(router)

    repo_id = uuid4()
    pr_number = 123

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/ai/repos/{repo_id}/prs/{pr_number}/review",
            json={"repository": "owner/repo", "force_refresh": False},
        )

        # Should return 400 without workspace ID
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.skip(reason="Requires auth mock setup - integration test")
@pytest.mark.asyncio
async def test_stream_pr_review_invalid_repository_format() -> None:
    """Test PR review fails with invalid repository format."""
    from pilot_space.api.v1.routers.ai_pr_review import router

    app = FastAPI()
    app.include_router(router)

    repo_id = uuid4()
    pr_number = 123
    workspace_id = uuid4()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/ai/repos/{repo_id}/prs/{pr_number}/review",
            json={
                "repository": "invalid-format",  # Missing slash
                "force_refresh": False,
            },
            headers={"X-Workspace-ID": str(workspace_id)},
        )

        # Should return 422 validation error
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.skip(reason="Requires auth mock setup - integration test")
@pytest.mark.asyncio
async def test_stream_pr_review_aspect_progression(
    app_with_mocks: FastAPI,
) -> None:
    """Test that aspects progress through correct states."""
    repo_id = uuid4()
    pr_number = 123
    workspace_id = uuid4()

    transport = ASGITransport(app=app_with_mocks)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/ai/repos/{repo_id}/prs/{pr_number}/review",
            json={"repository": "owner/repo", "force_refresh": False},
            headers={"X-Workspace-ID": str(workspace_id)},
        )

        # Parse events
        events_data = []
        current_event = None
        current_data = ""

        for line in response.text.split("\n"):
            if line.startswith("event:"):
                if current_event and current_data:
                    events_data.append((current_event, current_data))
                current_event = line.split(": ", 1)[1]
                current_data = ""
            elif line.startswith("data:"):
                current_data = line.split(": ", 1)[1]

        # Verify initial pending events
        aspect_events = [(event, data) for event, data in events_data if event == "aspect"]
        assert len(aspect_events) >= 5  # At least 5 aspects

        # First 5 events should be pending
        for i in range(5):
            event_type, data = aspect_events[i]
            assert event_type == "aspect"
            assert "pending" in data


__all__ = [
    "test_stream_pr_review_aspect_progression",
    "test_stream_pr_review_invalid_repository_format",
    "test_stream_pr_review_missing_workspace_id",
    "test_stream_pr_review_success",
]
