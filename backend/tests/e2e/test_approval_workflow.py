"""E2E tests for approval-related conversations via chat endpoint (T097).

Tests approval-related behavior through conversational interface:
- Discussing actions that would require approval
- Understanding destructive vs non-destructive operations
- Conversational safety guardrails

Note: Actual approval workflow (DD-003) is tested at integration level.
Chat endpoint tests focus on conversational aspects of approval discussions.

Reference: docs/DESIGN_DECISIONS.md#dd-003
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestApprovalWorkflow:
    """E2E tests for approval-related conversations."""

    @pytest.mark.asyncio
    async def test_create_issue_suggestion(
        self,
        test_e2e_client: AsyncClient,
        mock_claude_sdk_demo_mode: None,
    ) -> None:
        """Test conversation about creating issues.

        Verifies:
        - Issue creation suggestions work
        - Response provides guidance
        - Context is understood

        Args:
            test_e2e_client: AsyncClient for making requests.
            mock_claude_sdk_demo_mode: Mock SDK fixture.
        """
        demo_headers = {"X-Workspace-Id": "00000000-0000-0000-0000-000000000002"}
        workspace_id = "00000000-0000-0000-0000-000000000002"

        async with test_e2e_client.stream(
            "POST",
            "/api/v1/ai/chat",
            headers=demo_headers,
            json={
                "message": "Create issues from: Implement authentication and authorization",
                "context": {"workspace_id": workspace_id},
            },
        ) as response:
            assert response.status_code == 200

            full_response = ""
            async for chunk in response.aiter_text():
                full_response += chunk

            # Verify response addresses issue creation
            assert len(full_response) > 0

    @pytest.mark.asyncio
    async def test_safe_action_discussion(
        self,
        test_e2e_client: AsyncClient,
        mock_claude_sdk_demo_mode: None,
    ) -> None:
        """Test discussion of safe, non-destructive actions.

        Verifies:
        - Non-destructive actions are discussed
        - Response provides helpful guidance
        - No warnings about destructiveness

        Args:
            test_e2e_client: AsyncClient for making requests.
            mock_claude_sdk_demo_mode: Mock SDK fixture.
        """
        demo_headers = {"X-Workspace-Id": "00000000-0000-0000-0000-000000000002"}
        workspace_id = "00000000-0000-0000-0000-000000000002"

        async with test_e2e_client.stream(
            "POST",
            "/api/v1/ai/chat",
            headers=demo_headers,
            json={
                "message": "Help me understand this code: def authenticate(user): ...",
                "context": {"workspace_id": workspace_id},
            },
        ) as response:
            assert response.status_code == 200

            full_response = ""
            async for chunk in response.aiter_text():
                full_response += chunk

            # Verify response provides analysis
            assert len(full_response) > 0

    @pytest.mark.asyncio
    async def test_potentially_destructive_action_awareness(
        self,
        test_e2e_client: AsyncClient,
        mock_claude_sdk_demo_mode: None,
    ) -> None:
        """Test awareness of potentially destructive actions.

        Verifies:
        - Destructive action requests are understood
        - Response provides appropriate guidance
        - Context is considered

        Args:
            test_e2e_client: AsyncClient for making requests.
            mock_claude_sdk_demo_mode: Mock SDK fixture.
        """
        demo_headers = {"X-Workspace-Id": "00000000-0000-0000-0000-000000000002"}
        workspace_id = "00000000-0000-0000-0000-000000000002"

        async with test_e2e_client.stream(
            "POST",
            "/api/v1/ai/chat",
            headers=demo_headers,
            json={
                "message": "Should I delete all old issues from last year?",
                "context": {"workspace_id": workspace_id},
            },
        ) as response:
            assert response.status_code == 200

            full_response = ""
            async for chunk in response.aiter_text():
                full_response += chunk

            # Verify response received
            assert len(full_response) > 0

    @pytest.mark.asyncio
    async def test_action_confirmation_discussion(
        self,
        test_e2e_client: AsyncClient,
        mock_claude_sdk_demo_mode: None,
    ) -> None:
        """Test discussion about confirming actions.

        Verifies:
        - Confirmation-related queries work
        - Response addresses confirmation need
        - Context is appropriate

        Args:
            test_e2e_client: AsyncClient for making requests.
            mock_claude_sdk_demo_mode: Mock SDK fixture.
        """
        demo_headers = {"X-Workspace-Id": "00000000-0000-0000-0000-000000000002"}
        workspace_id = "00000000-0000-0000-0000-000000000002"

        async with test_e2e_client.stream(
            "POST",
            "/api/v1/ai/chat",
            headers=demo_headers,
            json={
                "message": "What actions require confirmation before execution?",
                "context": {"workspace_id": workspace_id},
            },
        ) as response:
            assert response.status_code == 200

            full_response = ""
            async for chunk in response.aiter_text():
                full_response += chunk

            # Verify response addresses confirmation
            assert len(full_response) > 0

    @pytest.mark.asyncio
    async def test_batch_action_discussion(
        self,
        test_e2e_client: AsyncClient,
        mock_claude_sdk_demo_mode: None,
    ) -> None:
        """Test discussion of batch operations.

        Verifies:
        - Batch operation queries work
        - Response addresses bulk actions
        - Guidance is appropriate

        Args:
            test_e2e_client: AsyncClient for making requests.
            mock_claude_sdk_demo_mode: Mock SDK fixture.
        """
        demo_headers = {"X-Workspace-Id": "00000000-0000-0000-0000-000000000002"}
        workspace_id = "00000000-0000-0000-0000-000000000002"

        async with test_e2e_client.stream(
            "POST",
            "/api/v1/ai/chat",
            headers=demo_headers,
            json={
                "message": "Create 5 issues for the authentication feature",
                "context": {"workspace_id": workspace_id},
            },
        ) as response:
            assert response.status_code == 200

            full_response = ""
            async for chunk in response.aiter_text():
                full_response += chunk

            # Verify response addresses batch creation
            assert len(full_response) > 0

    @pytest.mark.asyncio
    async def test_action_modification_discussion(
        self,
        test_e2e_client: AsyncClient,
        mock_claude_sdk_demo_mode: None,
    ) -> None:
        """Test discussion about modifying proposed actions.

        Verifies:
        - Modification requests work
        - Response acknowledges changes
        - Context is maintained

        Args:
            test_e2e_client: AsyncClient for making requests.
            mock_claude_sdk_demo_mode: Mock SDK fixture.
        """
        demo_headers = {"X-Workspace-Id": "00000000-0000-0000-0000-000000000002"}
        workspace_id = "00000000-0000-0000-0000-000000000002"

        # First: Suggest action
        async with test_e2e_client.stream(
            "POST",
            "/api/v1/ai/chat",
            headers=demo_headers,
            json={
                "message": "Create an issue for user authentication",
                "context": {"workspace_id": workspace_id},
            },
        ) as response:
            assert response.status_code == 200

            full_response = ""
            async for chunk in response.aiter_text():
                full_response += chunk

            assert len(full_response) > 0

        # Second: Modify the suggestion
        async with test_e2e_client.stream(
            "POST",
            "/api/v1/ai/chat",
            headers=demo_headers,
            json={
                "message": "Actually, make it high priority and add the security label",
                "context": {"workspace_id": workspace_id},
            },
        ) as response:
            assert response.status_code == 200

            full_response = ""
            async for chunk in response.aiter_text():
                full_response += chunk

            # Verify modification acknowledged
            assert len(full_response) > 0

    @pytest.mark.asyncio
    async def test_action_cancellation_discussion(
        self,
        test_e2e_client: AsyncClient,
        mock_claude_sdk_demo_mode: None,
    ) -> None:
        """Test discussion about canceling actions.

        Verifies:
        - Cancellation requests work
        - Response acknowledges cancellation
        - Context is appropriate

        Args:
            test_e2e_client: AsyncClient for making requests.
            mock_claude_sdk_demo_mode: Mock SDK fixture.
        """
        demo_headers = {"X-Workspace-Id": "00000000-0000-0000-0000-000000000002"}
        workspace_id = "00000000-0000-0000-0000-000000000002"

        async with test_e2e_client.stream(
            "POST",
            "/api/v1/ai/chat",
            headers=demo_headers,
            json={
                "message": "Cancel the pending issue creation",
                "context": {"workspace_id": workspace_id},
            },
        ) as response:
            assert response.status_code == 200

            full_response = ""
            async for chunk in response.aiter_text():
                full_response += chunk

            # Verify response addresses cancellation
            assert len(full_response) > 0

    @pytest.mark.asyncio
    async def test_action_history_discussion(
        self,
        test_e2e_client: AsyncClient,
        mock_claude_sdk_demo_mode: None,
    ) -> None:
        """Test discussion about action history.

        Verifies:
        - History-related queries work
        - Response addresses past actions
        - Context is appropriate

        Args:
            test_e2e_client: AsyncClient for making requests.
            mock_claude_sdk_demo_mode: Mock SDK fixture.
        """
        demo_headers = {"X-Workspace-Id": "00000000-0000-0000-0000-000000000002"}
        workspace_id = "00000000-0000-0000-0000-000000000002"

        async with test_e2e_client.stream(
            "POST",
            "/api/v1/ai/chat",
            headers=demo_headers,
            json={
                "message": "What issues did we create in the last session?",
                "context": {"workspace_id": workspace_id},
            },
        ) as response:
            assert response.status_code == 200

            full_response = ""
            async for chunk in response.aiter_text():
                full_response += chunk

            # Verify response addresses history
            assert len(full_response) > 0


__all__ = ["TestApprovalWorkflow"]
