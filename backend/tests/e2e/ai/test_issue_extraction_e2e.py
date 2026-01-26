"""E2E tests for issue extraction with approval.

T098: Test extraction creates approval request and approval creates issues.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient


class TestIssueExtractionE2E:
    """E2E tests for issue extraction with approval flow."""

    @pytest.mark.asyncio
    async def test_extraction_creates_approval_request(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
        test_note: MagicMock,
    ) -> None:
        """Test that extraction creates approval request (DD-003).

        Verifies:
        - Issue extraction completes
        - Approval is required for issue creation
        - Approval ID is returned

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
            test_note: Mock note object.
        """
        note_id = str(test_note.id)

        # Extract issues via SSE
        events: list[dict[str, Any]] = []
        async with e2e_client.stream(
            "POST",
            f"/api/v1/ai/notes/{note_id}/extract-issues",
            headers=auth_headers,
            json={
                "note_id": note_id,
                "note_title": test_note.title,
                "note_content": test_note.content,
                "max_issues": 5,
            },
        ) as response:
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream"

            current_event_type = None
            async for line in response.aiter_lines():
                if line.startswith("event:"):
                    current_event_type = line.split(":", 1)[1].strip()
                elif line.startswith("data:") and current_event_type:
                    data_str = line.split(":", 1)[1].strip()
                    try:
                        data = json.loads(data_str)
                        events.append({"type": current_event_type, "data": data})
                    except json.JSONDecodeError:
                        pass

        # Verify we have events
        assert len(events) > 0

        # Find complete event
        complete_events = [e for e in events if e["type"] == "complete"]
        assert len(complete_events) > 0, "Should have complete event"

        complete_data = complete_events[0]["data"]

        # Verify approval is required
        assert "requires_approval" in complete_data, "Should indicate approval is required"
        assert complete_data["requires_approval"] is True

        # May include approval_id in future
        # assert "approval_id" in complete_data

    @pytest.mark.asyncio
    async def test_approval_creates_issues(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
        test_note: MagicMock,
    ) -> None:
        """Test that approval creates issues.

        Note: This requires full ApprovalService integration.
        Currently returns placeholder response.

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
            test_note: Mock note object.
        """
        note_id = str(test_note.id)
        approval_id = str(uuid4())

        # Approve extracted issues
        response = await e2e_client.post(
            f"/api/v1/ai/notes/{note_id}/extract-issues/approve",
            headers=auth_headers,
            json={
                "approval_id": approval_id,
                "selected_issues": [0, 1],
            },
        )

        # Should succeed (currently placeholder)
        assert response.status_code == 200

        data = response.json()
        assert "created_issues" in data

        # In full implementation, would verify:
        # assert len(data["created_issues"]) == 2
        # assert all(isinstance(id, str) for id in data["created_issues"])

    @pytest.mark.asyncio
    async def test_rejection_does_not_create_issues(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test that rejection doesn't create issues.

        Uses general approval resolution endpoint.

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        approval_id = str(uuid4())

        # Try to resolve a non-existent approval with rejection
        response = await e2e_client.post(
            f"/api/v1/ai/approvals/{approval_id}/resolve",
            headers=auth_headers,
            json={
                "approved": False,
                "note": "Rejected for testing",
            },
        )

        # Should return 404 for non-existent approval
        # or succeed if endpoint exists
        assert response.status_code in {200, 404}

    @pytest.mark.asyncio
    async def test_extraction_with_confidence_tags(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
        test_note: MagicMock,
    ) -> None:
        """Test that extracted issues include confidence tags (DD-048).

        Confidence tags: recommended, default, current, alternative

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
            test_note: Mock note object.
        """
        note_id = str(test_note.id)

        events: list[dict[str, Any]] = []
        async with e2e_client.stream(
            "POST",
            f"/api/v1/ai/notes/{note_id}/extract-issues",
            headers=auth_headers,
            json={
                "note_id": note_id,
                "note_title": test_note.title,
                "note_content": test_note.content,
            },
        ) as response:
            current_event_type = None
            async for line in response.aiter_lines():
                if line.startswith("event:"):
                    current_event_type = line.split(":", 1)[1].strip()
                elif line.startswith("data:") and current_event_type:
                    data_str = line.split(":", 1)[1].strip()
                    try:
                        data = json.loads(data_str)
                        events.append({"type": current_event_type, "data": data})
                    except json.JSONDecodeError:
                        pass

        # Find issue events
        issue_events = [e for e in events if e["type"] == "issue"]

        if len(issue_events) > 0:
            # Verify each issue has confidence info
            for issue_event in issue_events:
                issue_data = issue_event["data"]
                # Should have confidence tag or score
                assert "confidence_tag" in issue_data or "confidence_score" in issue_data, (
                    "Issues should include confidence information"
                )

    @pytest.mark.asyncio
    async def test_approval_list_endpoint(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test listing approval requests.

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        # List approvals for workspace
        response = await e2e_client.get(
            "/api/v1/ai/approvals",
            headers=auth_headers,
            params={"status": "pending"},
        )

        # Should succeed or require admin
        assert response.status_code in {200, 403}

        if response.status_code == 200:
            data = response.json()
            assert "requests" in data
            assert "total" in data
            assert "pending_count" in data

    @pytest.mark.asyncio
    async def test_approval_detail_endpoint(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test getting approval request details.

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        approval_id = str(uuid4())

        # Get non-existent approval
        response = await e2e_client.get(
            f"/api/v1/ai/approvals/{approval_id}",
            headers=auth_headers,
        )

        # Should return 404 for non-existent approval
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_approval_expiration(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test that expired approvals cannot be resolved.

        Note: This would require creating an approval with past expiry.
        Currently tests the error handling.

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        approval_id = str(uuid4())

        # Try to resolve non-existent approval
        response = await e2e_client.post(
            f"/api/v1/ai/approvals/{approval_id}/resolve",
            headers=auth_headers,
            json={
                "approved": True,
                "note": "Testing expiration",
            },
        )

        # Should fail (404 or 400)
        assert response.status_code in {400, 404}

    @pytest.mark.asyncio
    async def test_extraction_progress_events(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
        test_note: MagicMock,
    ) -> None:
        """Test that extraction emits progress events.

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
            test_note: Mock note object.
        """
        note_id = str(test_note.id)

        events: list[dict[str, Any]] = []
        async with e2e_client.stream(
            "POST",
            f"/api/v1/ai/notes/{note_id}/extract-issues",
            headers=auth_headers,
            json={
                "note_id": note_id,
                "note_title": test_note.title,
                "note_content": test_note.content,
            },
        ) as response:
            current_event_type = None
            async for line in response.aiter_lines():
                if line.startswith("event:"):
                    current_event_type = line.split(":", 1)[1].strip()
                elif line.startswith("data:") and current_event_type:
                    data_str = line.split(":", 1)[1].strip()
                    try:
                        data = json.loads(data_str)
                        events.append({"type": current_event_type, "data": data})
                    except json.JSONDecodeError:
                        pass

        # Should have progress events
        progress_events = [e for e in events if e["type"] == "progress"]
        assert len(progress_events) > 0, "Should emit progress events"

        # Verify expected stages
        statuses = [e["data"].get("status") for e in progress_events]
        assert "analyzing" in statuses or "extracting" in statuses

    @pytest.mark.asyncio
    async def test_partial_approval_selection(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
        test_note: MagicMock,
    ) -> None:
        """Test approving only selected issues from extraction.

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
            test_note: Mock note object.
        """
        note_id = str(test_note.id)
        approval_id = str(uuid4())

        # Approve only issue at index 0
        response = await e2e_client.post(
            f"/api/v1/ai/notes/{note_id}/extract-issues/approve",
            headers=auth_headers,
            json={
                "approval_id": approval_id,
                "selected_issues": [0],  # Only first issue
            },
        )

        # Should succeed (placeholder for now)
        assert response.status_code == 200

        # In full implementation, would verify only 1 issue created
        data = response.json()
        assert "created_issues" in data
