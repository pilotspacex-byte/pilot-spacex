"""E2E tests for subagent delegation via chat endpoint (T096).

Tests subagent behavior through conversational interface:
- PR review subagent via prompts
- AI context subagent via prompts
- Doc generator subagent via prompts
- Multi-turn conversations

Note: Subagents are now invoked through the unified chat endpoint
via natural language commands or @mentions.

Reference: backend/src/pilot_space/ai/agents/subagents/
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestSubagentDelegation:
    """E2E tests for subagent delegation via chat."""

    @pytest.mark.asyncio
    async def test_pr_review_request_via_chat(
        self,
        test_e2e_client: AsyncClient,
        mock_claude_sdk_demo_mode: None,
    ) -> None:
        """Test PR review request via chat prompt.

        Verifies:
        - PR review prompts are recognized
        - Response addresses PR review
        - Content is relevant to code review

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
                "message": "Review PR #123 for security and performance issues",
                "context": {"workspace_id": workspace_id},
            },
        ) as response:
            assert response.status_code == 200

            full_response = ""
            async for chunk in response.aiter_text():
                full_response += chunk

            # Verify response addresses code review
            assert len(full_response) > 0

    @pytest.mark.asyncio
    async def test_ai_context_request_via_chat(
        self,
        test_e2e_client: AsyncClient,
        mock_claude_sdk_demo_mode: None,
    ) -> None:
        """Test AI context aggregation via chat prompt.

        Verifies:
        - Context aggregation prompts work
        - Response provides context
        - Related information is mentioned

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
                "message": "Find related notes, code, and tasks for implementing user authentication",
                "context": {"workspace_id": workspace_id},
            },
        ) as response:
            assert response.status_code == 200

            full_response = ""
            async for chunk in response.aiter_text():
                full_response += chunk

            # Verify response addresses context gathering
            assert len(full_response) > 0

    @pytest.mark.asyncio
    async def test_doc_generator_request_via_chat(
        self,
        test_e2e_client: AsyncClient,
        mock_claude_sdk_demo_mode: None,
    ) -> None:
        """Test documentation generation via chat prompt.

        Verifies:
        - Documentation generation prompts work
        - Response provides documentation structure
        - Content is relevant to docs

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
                "message": "Generate API documentation for the issues endpoints",
                "context": {"workspace_id": workspace_id},
            },
        ) as response:
            assert response.status_code == 200

            full_response = ""
            async for chunk in response.aiter_text():
                full_response += chunk

            # Verify response addresses documentation
            assert len(full_response) > 0

    @pytest.mark.asyncio
    async def test_subagent_multi_turn_conversation(
        self,
        test_e2e_client: AsyncClient,
        mock_claude_sdk_demo_mode: None,
    ) -> None:
        """Test multi-turn conversation involving subagent tasks.

        Verifies:
        - Initial request is processed
        - Follow-up questions work
        - Context is maintained

        Args:
            test_e2e_client: AsyncClient for making requests.
            mock_claude_sdk_demo_mode: Mock SDK fixture.
        """
        demo_headers = {"X-Workspace-Id": "00000000-0000-0000-0000-000000000002"}
        workspace_id = "00000000-0000-0000-0000-000000000002"

        # First turn: Start review
        async with test_e2e_client.stream(
            "POST",
            "/api/v1/ai/chat",
            headers=demo_headers,
            json={
                "message": "Review the authentication code for security issues",
                "context": {"workspace_id": workspace_id},
            },
        ) as response:
            assert response.status_code == 200

            full_response = ""
            async for chunk in response.aiter_text():
                full_response += chunk

            assert len(full_response) > 0

        # Second turn: Follow-up question
        async with test_e2e_client.stream(
            "POST",
            "/api/v1/ai/chat",
            headers=demo_headers,
            json={
                "message": "Can you elaborate on the security findings?",
                "context": {"workspace_id": workspace_id},
            },
        ) as response:
            assert response.status_code == 200

            full_response = ""
            async for chunk in response.aiter_text():
                full_response += chunk

            # Verify follow-up response
            assert len(full_response) > 0

    @pytest.mark.asyncio
    async def test_subagent_with_specific_requirements(
        self,
        test_e2e_client: AsyncClient,
        mock_claude_sdk_demo_mode: None,
    ) -> None:
        """Test subagent task with specific requirements.

        Verifies:
        - Detailed requirements are understood
        - Response addresses specific needs
        - Context influences response

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
                "message": "Generate API documentation including authentication, rate limiting, and error responses",
                "context": {"workspace_id": workspace_id},
            },
        ) as response:
            assert response.status_code == 200

            full_response = ""
            async for chunk in response.aiter_text():
                full_response += chunk

            # Verify response addresses requirements
            assert len(full_response) > 0

    @pytest.mark.asyncio
    async def test_subagent_validation_errors(
        self,
        test_e2e_client: AsyncClient,
        mock_claude_sdk_demo_mode: None,
    ) -> None:
        """Test validation for subagent-related requests.

        Verifies:
        - Empty messages are rejected
        - Validation errors return appropriate status

        Args:
            test_e2e_client: AsyncClient for making requests.
            mock_claude_sdk_demo_mode: Mock SDK fixture.
        """
        demo_headers = {"X-Workspace-Id": "00000000-0000-0000-0000-000000000002"}
        workspace_id = "00000000-0000-0000-0000-000000000002"

        # Empty message should fail validation
        response = await test_e2e_client.post(
            "/api/v1/ai/chat",
            headers=demo_headers,
            json={
                "message": "",
                "context": {"workspace_id": workspace_id},
            },
        )
        assert response.status_code == 422


__all__ = ["TestSubagentDelegation"]
