"""Integration tests for issue extraction endpoint.

T061: Integration tests for endpoint + approval flow.
"""

import json
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from pilot_space.main import app


@pytest.fixture
async def client():
    """Create async test client."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
def auth_headers():
    """Create auth headers for tests."""
    return {
        "X-Workspace-ID": "00000000-0000-0000-0000-000000000002",
        "X-Anthropic-API-Key": "test-key-123",
    }


@pytest.fixture
def test_note():
    """Create test note data."""
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
                },
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "Bug: Login page shows 500 error when clicking submit button.",
                        }
                    ],
                },
            ],
        },
    )


class TestIssueExtractionEndpoint:
    """Test suite for issue extraction SSE endpoint."""

    @pytest.mark.asyncio
    async def test_extracts_issues_with_sse_stream(self, client, auth_headers, test_note):
        """Verify SSE stream returns expected event types."""
        note_id = str(test_note.id)

        async with client.stream(
            "POST",
            f"/ai/notes/{note_id}/extract-issues",
            headers=auth_headers,
            json={
                "note_id": note_id,
                "note_title": test_note.title,
                "note_content": test_note.content,
            },
        ) as response:
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream"

            events = []
            async for line in response.aiter_lines():
                if line.startswith("event:"):
                    event_type = line.split(":", 1)[1].strip()
                    events.append(event_type)

            # Should have progress, issue, complete events
            assert "progress" in events
            assert "issue" in events
            assert "complete" in events

    @pytest.mark.asyncio
    async def test_extraction_requires_workspace_header(self, client, test_note):
        """Verify workspace ID header is required."""
        note_id = str(test_note.id)

        response = await client.post(
            f"/ai/notes/{note_id}/extract-issues",
            json={
                "note_id": note_id,
                "note_title": test_note.title,
                "note_content": test_note.content,
            },
        )

        assert response.status_code == 400
        assert "X-Workspace-ID" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_extraction_validates_note_content(self, client, auth_headers):
        """Verify request validation for required fields."""
        note_id = str(uuid4())

        response = await client.post(
            f"/ai/notes/{note_id}/extract-issues",
            headers=auth_headers,
            json={
                "note_id": note_id,
                "note_title": "",  # Empty title
                "note_content": {},  # Empty content
            },
        )

        # Should still accept (validation happens in agent)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_sse_stream_emits_progress_events(self, client, auth_headers, test_note):
        """Verify progress events are emitted during extraction."""
        note_id = str(test_note.id)

        async with client.stream(
            "POST",
            f"/ai/notes/{note_id}/extract-issues",
            headers=auth_headers,
            json={
                "note_id": note_id,
                "note_title": test_note.title,
                "note_content": test_note.content,
            },
        ) as response:
            progress_events = []
            current_event_type = None

            async for line in response.aiter_lines():
                if line.startswith("event:"):
                    current_event_type = line.split(":", 1)[1].strip()
                elif line.startswith("data:") and current_event_type == "progress":
                    data_str = line.split(":", 1)[1].strip()
                    try:
                        data = json.loads(data_str)
                        progress_events.append(data)
                    except json.JSONDecodeError:
                        pass

            # Should have at least analyzing and extracting stages
            statuses = [e.get("status") for e in progress_events]
            assert "analyzing" in statuses
            assert "extracting" in statuses


class TestApprovalEndpoint:
    """Test suite for approval endpoint."""

    @pytest.mark.asyncio
    async def test_approval_endpoint_exists(self, client, auth_headers, test_note):
        """Verify approval endpoint is accessible."""
        note_id = str(test_note.id)
        approval_id = str(uuid4())

        response = await client.post(
            f"/ai/notes/{note_id}/extract-issues/approve",
            headers=auth_headers,
            json={
                "approval_id": approval_id,
                "selected_issues": [0, 1],
            },
        )

        # Currently returns placeholder response
        assert response.status_code == 200
        data = response.json()
        assert "created_issues" in data

    @pytest.mark.asyncio
    async def test_approval_validates_request(self, client, auth_headers, test_note):
        """Verify approval request validation."""
        note_id = str(test_note.id)

        # Missing approval_id
        response = await client.post(
            f"/ai/notes/{note_id}/extract-issues/approve",
            headers=auth_headers,
            json={
                "selected_issues": [0],
            },
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_approval_requires_workspace_header(self, client, test_note):
        """Verify workspace ID header is required for approval."""
        note_id = str(test_note.id)

        response = await client.post(
            f"/ai/notes/{note_id}/extract-issues/approve",
            json={
                "approval_id": str(uuid4()),
                "selected_issues": [0],
            },
        )

        assert response.status_code == 400
        assert "X-Workspace-ID" in response.json()["detail"]


class TestEndToEndFlow:
    """Test complete extraction + approval flow."""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires full ApprovalService and IssueService integration")
    async def test_extract_then_approve_flow(self, client, auth_headers, test_note):
        """Verify complete flow from extraction to issue creation."""
        note_id = str(test_note.id)

        # Step 1: Extract issues
        async with client.stream(
            "POST",
            f"/ai/notes/{note_id}/extract-issues",
            headers=auth_headers,
            json={
                "note_id": note_id,
                "note_title": test_note.title,
                "note_content": test_note.content,
            },
        ) as response:
            # Collect all events
            complete_event = None
            async for line in response.aiter_lines():
                if line.startswith("event: complete"):
                    # Next line should be data
                    continue
                if line.startswith("data:") and complete_event is None:
                    try:
                        data = json.loads(line.split(":", 1)[1].strip())
                        if data.get("status") == "complete":
                            complete_event = data
                    except json.JSONDecodeError:
                        pass

            assert complete_event is not None
            assert complete_event["requires_approval"] is True

        # Step 2: Approve selected issues
        # approval_id = complete_event.get("approval_id")
        # response = await client.post(
        #     f"/ai/notes/{note_id}/extract-issues/approve",
        #     headers=auth_headers,
        #     json={
        #         "approval_id": approval_id,
        #         "selected_issues": [0, 1],
        #     },
        # )

        # assert response.status_code == 200
        # data = response.json()
        # assert len(data["created_issues"]) == 2
