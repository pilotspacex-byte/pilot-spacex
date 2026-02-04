"""Integration tests for margin annotation endpoint.

T072: Integration tests for SSE streaming annotation endpoint.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from pilot_space.main import app


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Authentication headers for test requests."""
    return {
        "Authorization": "Bearer test-token",
        "X-Workspace-ID": str(uuid4()),
    }


@pytest.fixture
def test_note_id() -> UUID:
    """Test note UUID."""
    return uuid4()


@pytest.fixture
def mock_dependencies():
    """Override FastAPI dependencies for testing."""
    from pilot_space.dependencies import (
        get_current_user_id_or_demo,
        get_sdk_orchestrator,
        get_session,
    )

    async def mock_get_session():
        """Mock database session."""
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        # Mock the get method for note retrieval
        mock_session.get = AsyncMock(return_value=None)  # Return None to skip DB validation
        yield mock_session

    def mock_get_user_id():
        """Mock user ID."""
        return uuid4()

    async def mock_get_orchestrator():
        """Mock SDK orchestrator - will be replaced in individual tests."""
        # Return a default mock - tests can override with patches
        mock_orch = MagicMock()
        mock_orch.execute = AsyncMock()
        return mock_orch

    # Override dependencies at the app level
    app.dependency_overrides[get_session] = mock_get_session
    app.dependency_overrides[get_current_user_id_or_demo] = mock_get_user_id
    app.dependency_overrides[get_sdk_orchestrator] = mock_get_orchestrator

    yield

    # Clean up overrides after test
    app.dependency_overrides.clear()


class TestMarginAnnotationEndpoint:
    """Test suite for margin annotation SSE endpoint."""

    @pytest.mark.asyncio
    async def test_generates_annotations_via_sse(
        self,
        auth_headers: dict[str, str],
        test_note_id: UUID,
        mock_dependencies,
    ) -> None:
        """Verify endpoint streams annotations via SSE."""
        # Arrange
        request_body = {
            "block_ids": ["block-1", "block-2"],
            "context_blocks": 3,
        }

        # Mock the orchestrator execution
        mock_output = MagicMock()
        mock_output.annotations = [
            MagicMock(
                block_id="block-1",
                type=MagicMock(value="suggestion"),
                title="Add examples",
                content="Consider adding examples",
                confidence=0.8,
                action_label=None,
                action_payload=None,
            ),
            MagicMock(
                block_id="block-2",
                type=MagicMock(value="warning"),
                title="Check syntax",
                content="Verify syntax",
                confidence=0.9,
                action_label="Validate",
                action_payload=None,
            ),
        ]
        mock_output.processed_blocks = 2

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output = mock_output

        # Override the orchestrator dependency for this specific test
        from pilot_space.dependencies import get_sdk_orchestrator

        mock_orchestrator = MagicMock()
        mock_orchestrator.execute = AsyncMock(return_value=mock_result)

        async def mock_get_orch():
            return mock_orchestrator

        app.dependency_overrides[get_sdk_orchestrator] = mock_get_orch

        try:
            # Act
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    f"/api/v1/notes/{test_note_id}/annotations",
                    headers=auth_headers,
                    json=request_body,
                )

                # Assert
                assert response.status_code == 200
                assert response.headers["content-type"].startswith("text/event-stream")

                # Parse SSE events
                events = []
                for line in response.text.split("\n"):
                    if line.startswith("event:"):
                        event_type = line.split("event:")[1].strip()
                        events.append(event_type)

                # Should have progress, annotation (x2), and done events
                assert "progress" in events
                assert "annotation" in events
                assert "done" in events
        finally:
            # Restore original override from fixture
            async def default_mock_get_orchestrator():
                mock_orch = MagicMock()
                mock_orch.execute = AsyncMock()
                return mock_orch

            app.dependency_overrides[get_sdk_orchestrator] = default_mock_get_orchestrator

    @pytest.mark.asyncio
    async def test_validates_block_ids_min_length(
        self,
        auth_headers: dict[str, str],
        test_note_id: UUID,
        mock_dependencies,
    ) -> None:
        """Verify endpoint validates minimum block_ids length."""
        # Arrange
        request_body = {
            "block_ids": [],  # Empty list
            "context_blocks": 3,
        }

        # Act
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/notes/{test_note_id}/annotations",
                headers=auth_headers,
                json=request_body,
            )

            # Assert
            assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_validates_block_ids_max_length(
        self,
        auth_headers: dict[str, str],
        test_note_id: UUID,
        mock_dependencies,
    ) -> None:
        """Verify endpoint validates maximum block_ids length."""
        # Arrange
        request_body = {
            "block_ids": [f"block-{i}" for i in range(25)],  # More than 20
            "context_blocks": 3,
        }

        # Act
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/notes/{test_note_id}/annotations",
                headers=auth_headers,
                json=request_body,
            )

            # Assert
            assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_validates_context_blocks_range(
        self,
        auth_headers: dict[str, str],
        test_note_id: UUID,
        mock_dependencies,
    ) -> None:
        """Verify endpoint validates context_blocks range."""
        # Arrange
        request_body = {
            "block_ids": ["block-1"],
            "context_blocks": 15,  # More than 10
        }

        # Act
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/notes/{test_note_id}/annotations",
                headers=auth_headers,
                json=request_body,
            )

            # Assert
            assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_requires_workspace_header(
        self,
        test_note_id: UUID,
        mock_dependencies,
    ) -> None:
        """Verify endpoint requires X-Workspace-ID header."""
        # Arrange
        request_body = {
            "block_ids": ["block-1"],
            "context_blocks": 3,
        }

        headers = {
            "Authorization": "Bearer test-token",
            # Missing X-Workspace-ID
        }

        # Act
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/notes/{test_note_id}/annotations",
                headers=headers,
                json=request_body,
            )

            # Assert
            assert response.status_code == 400  # Bad request

    @pytest.mark.asyncio
    async def test_handles_agent_execution_failure(
        self,
        auth_headers: dict[str, str],
        test_note_id: UUID,
        mock_dependencies,
    ) -> None:
        """Verify endpoint handles agent execution failures gracefully."""
        # Arrange
        request_body = {
            "block_ids": ["block-1"],
            "context_blocks": 3,
        }

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.output = None
        mock_result.error = "Agent execution failed"

        # Override dependency using FastAPI pattern
        from pilot_space.dependencies import get_sdk_orchestrator

        mock_orchestrator = MagicMock()
        mock_orchestrator.execute = AsyncMock(return_value=mock_result)

        async def mock_get_orch():
            return mock_orchestrator

        app.dependency_overrides[get_sdk_orchestrator] = mock_get_orch

        try:
            # Act
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    f"/api/v1/notes/{test_note_id}/annotations",
                    headers=auth_headers,
                    json=request_body,
                )

                # Assert
                assert response.status_code == 200  # SSE always returns 200
                # Should contain error event
                assert "error" in response.text
        finally:
            # Restore default mock
            async def default_mock():
                mock_orch = MagicMock()
                mock_orch.execute = AsyncMock()
                return mock_orch

            app.dependency_overrides[get_sdk_orchestrator] = default_mock

    @pytest.mark.asyncio
    async def test_streams_multiple_annotations(
        self,
        auth_headers: dict[str, str],
        test_note_id: UUID,
        mock_dependencies,
    ) -> None:
        """Verify endpoint streams multiple annotations correctly."""
        # Arrange
        request_body = {
            "block_ids": ["block-1", "block-2", "block-3"],
            "context_blocks": 3,
        }

        # Create 3 mock annotations
        mock_annotations = []
        for i in range(3):
            mock_ann = MagicMock()
            mock_ann.block_id = f"block-{i + 1}"
            mock_ann.type.value = "suggestion"
            mock_ann.title = f"Annotation {i + 1}"
            mock_ann.content = f"Content {i + 1}"
            mock_ann.confidence = 0.8
            mock_ann.action_label = None
            mock_ann.action_payload = None
            mock_annotations.append(mock_ann)

        mock_output = MagicMock()
        mock_output.annotations = mock_annotations
        mock_output.processed_blocks = 3

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output = mock_output

        # Override dependency using FastAPI pattern
        from pilot_space.dependencies import get_sdk_orchestrator

        mock_orchestrator = MagicMock()
        mock_orchestrator.execute = AsyncMock(return_value=mock_result)

        async def mock_get_orch():
            return mock_orchestrator

        app.dependency_overrides[get_sdk_orchestrator] = mock_get_orch

        try:
            # Act
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    f"/api/v1/notes/{test_note_id}/annotations",
                    headers=auth_headers,
                    json=request_body,
                )

                # Assert
                assert response.status_code == 200

                # Count annotation events
                annotation_events = response.text.count("event: annotation")
                assert annotation_events == 3
        finally:
            # Restore default mock
            async def default_mock():
                mock_orch = MagicMock()
                mock_orch.execute = AsyncMock()
                return mock_orch

            app.dependency_overrides[get_sdk_orchestrator] = default_mock

    @pytest.mark.asyncio
    async def test_includes_completion_metadata(
        self,
        auth_headers: dict[str, str],
        test_note_id: UUID,
        mock_dependencies,
    ) -> None:
        """Verify endpoint includes completion metadata in done event."""
        # Arrange
        request_body = {
            "block_ids": ["block-1", "block-2"],
            "context_blocks": 3,
        }

        mock_ann1 = MagicMock()
        mock_ann1.block_id = "block-1"
        mock_ann1.type.value = "suggestion"
        mock_ann1.title = "Title 1"
        mock_ann1.content = "Content 1"
        mock_ann1.confidence = 0.8
        mock_ann1.action_label = None
        mock_ann1.action_payload = None

        mock_ann2 = MagicMock()
        mock_ann2.block_id = "block-2"
        mock_ann2.type.value = "warning"
        mock_ann2.title = "Title 2"
        mock_ann2.content = "Content 2"
        mock_ann2.confidence = 0.9
        mock_ann2.action_label = None
        mock_ann2.action_payload = None

        mock_output = MagicMock()
        mock_output.annotations = [mock_ann1, mock_ann2]
        mock_output.processed_blocks = 2

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output = mock_output

        # Override dependency using FastAPI pattern
        from pilot_space.dependencies import get_sdk_orchestrator

        mock_orchestrator = MagicMock()
        mock_orchestrator.execute = AsyncMock(return_value=mock_result)

        async def mock_get_orch():
            return mock_orchestrator

        app.dependency_overrides[get_sdk_orchestrator] = mock_get_orch

        try:
            # Act
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    f"/api/v1/notes/{test_note_id}/annotations",
                    headers=auth_headers,
                    json=request_body,
                )

                # Assert
                assert response.status_code == 200
                # Check for done event with metadata
                assert "event: done" in response.text
                assert "total_annotations" in response.text
                assert "processed_blocks" in response.text
        finally:
            # Restore default mock
            async def default_mock():
                mock_orch = MagicMock()
                mock_orch.execute = AsyncMock()
                return mock_orch

            app.dependency_overrides[get_sdk_orchestrator] = default_mock

    @pytest.mark.asyncio
    async def test_default_context_blocks_value(
        self,
        auth_headers: dict[str, str],
        test_note_id: UUID,
        mock_dependencies,
    ) -> None:
        """Verify endpoint uses default context_blocks value."""
        # Arrange
        request_body = {
            "block_ids": ["block-1"],
            # context_blocks omitted - should default to 3
        }

        mock_output = MagicMock()
        mock_output.annotations = []
        mock_output.processed_blocks = 1

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output = mock_output

        # Override dependency using FastAPI pattern
        from pilot_space.dependencies import get_sdk_orchestrator

        mock_orchestrator = MagicMock()
        mock_orchestrator.execute = AsyncMock(return_value=mock_result)

        async def mock_get_orch():
            return mock_orchestrator

        app.dependency_overrides[get_sdk_orchestrator] = mock_get_orch

        try:
            # Act
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    f"/api/v1/notes/{test_note_id}/annotations",
                    headers=auth_headers,
                    json=request_body,
                )

                # Assert
                assert response.status_code == 200

                # Verify execute was called with default context_blocks=3
                assert mock_orchestrator.execute.called
                call_args = mock_orchestrator.execute.call_args
                if call_args:
                    input_data = call_args[0][1]
                    assert input_data.context_blocks == 3
        finally:
            # Restore default mock
            async def default_mock():
                mock_orch = MagicMock()
                mock_orch.execute = AsyncMock()
                return mock_orch

            app.dependency_overrides[get_sdk_orchestrator] = default_mock
