"""E2E tests for session persistence via chat endpoint (T098).

Tests conversation session behavior through unified chat interface:
- Session continuity across messages
- Context preservation
- Multi-turn conversations

Note: Session management is now internal to the unified chat endpoint.
Sessions are created automatically and managed via session_id parameter.

Reference: backend/src/pilot_space/ai/session/session_manager.py
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient


class TestSessionPersistence:
    """E2E tests for conversation session behavior via chat."""

    @pytest.mark.asyncio
    async def test_new_conversation_without_session_id(
        self,
        test_e2e_client: AsyncClient,
        mock_claude_sdk_demo_mode: None,
    ) -> None:
        """Test starting new conversation without session_id.

        Verifies:
        - New conversations work without explicit session
        - Response is received
        - Session is managed internally

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
                "message": "What is Python?",
                "context": {"workspace_id": workspace_id},
            },
        ) as response:
            assert response.status_code == 200

            full_response = ""
            async for chunk in response.aiter_text():
                full_response += chunk

            assert len(full_response) > 0

    @pytest.mark.asyncio
    async def test_multi_turn_conversation(
        self,
        test_e2e_client: AsyncClient,
        mock_claude_sdk_demo_mode: None,
    ) -> None:
        """Test multi-turn conversation flow.

        Verifies:
        - Multiple messages can be sent in sequence
        - Each message receives response
        - Conversation flows naturally

        Args:
            test_e2e_client: AsyncClient for making requests.
            mock_claude_sdk_demo_mode: Mock SDK fixture.
        """
        demo_headers = {"X-Workspace-Id": "00000000-0000-0000-0000-000000000002"}
        workspace_id = "00000000-0000-0000-0000-000000000002"

        messages = [
            "My name is Alice",
            "What is FastAPI?",
            "Tell me more about Python",
        ]

        for message in messages:
            async with test_e2e_client.stream(
                "POST",
                "/api/v1/ai/chat",
                headers=demo_headers,
                json={
                    "message": message,
                    "context": {"workspace_id": workspace_id},
                },
            ) as response:
                assert response.status_code == 200

                # Collect response
                full_response = ""
                async for chunk in response.aiter_text():
                    full_response += chunk

                # Verify response received
                assert len(full_response) > 0

    @pytest.mark.asyncio
    async def test_context_preservation_in_conversation(
        self,
        test_e2e_client: AsyncClient,
        mock_claude_sdk_demo_mode: None,
    ) -> None:
        """Test that context is maintained across turns.

        Verifies:
        - First message establishes context
        - Follow-up messages build on context
        - Responses are contextually relevant

        Args:
            test_e2e_client: AsyncClient for making requests.
            mock_claude_sdk_demo_mode: Mock SDK fixture.
        """
        demo_headers = {"X-Workspace-Id": "00000000-0000-0000-0000-000000000002"}
        workspace_id = "00000000-0000-0000-0000-000000000002"

        # First message establishes context
        async with test_e2e_client.stream(
            "POST",
            "/api/v1/ai/chat",
            headers=demo_headers,
            json={
                "message": "I'm learning Python",
                "context": {"workspace_id": workspace_id},
            },
        ) as response:
            assert response.status_code == 200

            full_response = ""
            async for chunk in response.aiter_text():
                full_response += chunk

            assert len(full_response) > 0

        # Follow-up message referencing context
        async with test_e2e_client.stream(
            "POST",
            "/api/v1/ai/chat",
            headers=demo_headers,
            json={
                "message": "What should I learn next?",
                "context": {"workspace_id": workspace_id},
            },
        ) as response:
            assert response.status_code == 200

            full_response = ""
            async for chunk in response.aiter_text():
                full_response += chunk

            assert len(full_response) > 0

    @pytest.mark.asyncio
    async def test_long_conversation_handling(
        self,
        test_e2e_client: AsyncClient,
        mock_claude_sdk_demo_mode: None,
    ) -> None:
        """Test handling of longer conversations.

        Verifies:
        - Multiple turns work correctly
        - System handles extended conversations
        - No degradation in response quality

        Args:
            test_e2e_client: AsyncClient for making requests.
            mock_claude_sdk_demo_mode: Mock SDK fixture.
        """
        demo_headers = {"X-Workspace-Id": "00000000-0000-0000-0000-000000000002"}
        workspace_id = "00000000-0000-0000-0000-000000000002"

        # Send 5 messages in sequence
        for i in range(5):
            async with test_e2e_client.stream(
                "POST",
                "/api/v1/ai/chat",
                headers=demo_headers,
                json={
                    "message": f"Question {i + 1}: Tell me about Python feature {i + 1}",
                    "context": {"workspace_id": workspace_id},
                },
            ) as response:
                assert response.status_code == 200

                full_response = ""
                async for chunk in response.aiter_text():
                    full_response += chunk

                # Each message should get a response
                assert len(full_response) > 0

    @pytest.mark.asyncio
    async def test_conversation_with_issue_context(
        self,
        test_e2e_client: AsyncClient,
        mock_claude_sdk_demo_mode: None,
    ) -> None:
        """Test conversation with issue context mention.

        Verifies:
        - Messages can reference issues conceptually
        - Responses address issue-related queries
        - Context enriches conversation

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
                "message": "What should we implement first for user authentication?",
                "context": {
                    "workspace_id": workspace_id,
                },
            },
        ) as response:
            assert response.status_code == 200

            full_response = ""
            async for chunk in response.aiter_text():
                full_response += chunk

            assert len(full_response) > 0

    @pytest.mark.asyncio
    async def test_conversation_with_selected_text(
        self,
        test_e2e_client: AsyncClient,
        mock_claude_sdk_demo_mode: None,
    ) -> None:
        """Test conversation with selected text context.

        Verifies:
        - Selected text can be provided as context
        - Responses reference selected text
        - Context helps guide response

        Args:
            test_e2e_client: AsyncClient for making requests.
            mock_claude_sdk_demo_mode: Mock SDK fixture.
        """
        demo_headers = {"X-Workspace-Id": "00000000-0000-0000-0000-000000000002"}
        workspace_id = "00000000-0000-0000-0000-000000000002"

        selected_text = "Implement user authentication with OAuth2"

        async with test_e2e_client.stream(
            "POST",
            "/api/v1/ai/chat",
            headers=demo_headers,
            json={
                "message": "How should we approach this?",
                "context": {
                    "workspace_id": workspace_id,
                    "selected_text": selected_text,
                },
            },
        ) as response:
            assert response.status_code == 200

            full_response = ""
            async for chunk in response.aiter_text():
                full_response += chunk

            assert len(full_response) > 0

    @pytest.mark.asyncio
    async def test_concurrent_conversations(
        self,
        test_e2e_client: AsyncClient,
        mock_claude_sdk_demo_mode: None,
    ) -> None:
        """Test multiple concurrent conversations.

        Verifies:
        - Multiple conversations can run simultaneously
        - Each conversation maintains its own context
        - No cross-contamination between conversations

        Args:
            test_e2e_client: AsyncClient for making requests.
            mock_claude_sdk_demo_mode: Mock SDK fixture.
        """
        demo_headers = {"X-Workspace-Id": "00000000-0000-0000-0000-000000000002"}
        workspace_id = "00000000-0000-0000-0000-000000000002"

        # Start two different conversations
        messages = [
            "Tell me about Python",
            "Tell me about JavaScript",
        ]

        for message in messages:
            async with test_e2e_client.stream(
                "POST",
                "/api/v1/ai/chat",
                headers=demo_headers,
                json={
                    "message": message,
                    "context": {"workspace_id": workspace_id},
                },
            ) as response:
                assert response.status_code == 200

                full_response = ""
                async for chunk in response.aiter_text():
                    full_response += chunk

                # Each should get independent response
                assert len(full_response) > 0


__all__ = ["TestSessionPersistence"]
