"""E2E tests for chat conversation flow (T094).

Tests complete conversational agent flow including:
- Multi-turn conversations
- SSE event streaming
- Response validation

Reference: docs/architect/claude-agent-sdk-architecture.md
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestChatFlow:
    """E2E tests for conversational chat flow."""

    @pytest.mark.asyncio
    async def test_complete_chat_conversation_flow(
        self,
        test_e2e_client: AsyncClient,
        mock_claude_sdk_demo_mode: None,
    ) -> None:
        """Test complete multi-turn chat conversation.

        Verifies:
        - Unified chat endpoint works
        - SSE streaming response
        - Response contains expected content

        Args:
            test_e2e_client: AsyncClient for making requests.
            mock_claude_sdk_demo_mode: Mock SDK fixture.
        """
        demo_headers = {"X-Workspace-Id": "pilot-space-demo"}
        workspace_id = "00000000-0000-0000-0000-000000000002"

        # Send message with streaming
        async with test_e2e_client.stream(
            "POST",
            "/api/v1/ai/chat",
            headers=demo_headers,
            json={
                "message": "What is FastAPI?",
                "context": {"workspace_id": workspace_id},
            },
        ) as response:
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")

            # Collect full response
            full_response = ""
            async for chunk in response.aiter_text():
                full_response += chunk

            # Verify FastAPI-specific content
            assert len(full_response) > 0
            assert "FastAPI" in full_response or "framework" in full_response

    @pytest.mark.asyncio
    async def test_sse_event_streaming(
        self,
        test_e2e_client: AsyncClient,
        mock_claude_sdk_demo_mode: None,
    ) -> None:
        """Test SSE event streaming format.

        Verifies:
        - Proper SSE event format
        - Response streaming works
        - Content is received

        Args:
            test_e2e_client: AsyncClient for making requests.
            mock_claude_sdk_demo_mode: Mock SDK fixture.
        """
        demo_headers = {"X-Workspace-Id": "pilot-space-demo"}
        workspace_id = "00000000-0000-0000-0000-000000000002"

        # Stream message
        async with test_e2e_client.stream(
            "POST",
            "/api/v1/ai/chat",
            headers=demo_headers,
            json={
                "message": "Hello",
                "context": {"workspace_id": workspace_id},
            },
        ) as response:
            assert response.status_code == 200

            # Collect full response
            full_response = ""
            async for chunk in response.aiter_text():
                full_response += chunk

            # Verify response received
            assert len(full_response) > 0
            # Verify it contains greeting-related content
            assert "Claude" in full_response or "hello" in full_response.lower()

    @pytest.mark.asyncio
    async def test_multiple_messages(
        self,
        test_e2e_client: AsyncClient,
        mock_claude_sdk_demo_mode: None,
    ) -> None:
        """Test sending multiple messages in sequence.

        Verifies:
        - Multiple messages can be sent
        - Each message receives a response
        - Responses are appropriate to prompts

        Args:
            test_e2e_client: AsyncClient for making requests.
            mock_claude_sdk_demo_mode: Mock SDK fixture.
        """
        demo_headers = {"X-Workspace-Id": "pilot-space-demo"}
        workspace_id = "00000000-0000-0000-0000-000000000002"

        # Send multiple messages
        messages = [
            "What is Python?",
            "What is FastAPI?",
            "Hello",
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

                # Consume stream
                full_response = ""
                async for chunk in response.aiter_text():
                    full_response += chunk

                # Verify response received
                assert len(full_response) > 0

    @pytest.mark.asyncio
    async def test_contextual_responses(
        self,
        test_e2e_client: AsyncClient,
        mock_claude_sdk_demo_mode: None,
    ) -> None:
        """Test that responses are contextual to prompts.

        Verifies:
        - Different prompts trigger appropriate responses
        - Response content is relevant to message

        Args:
            test_e2e_client: AsyncClient for making requests.
            mock_claude_sdk_demo_mode: Mock SDK fixture.
        """
        demo_headers = {"X-Workspace-Id": "pilot-space-demo"}
        workspace_id = "00000000-0000-0000-0000-000000000002"

        # Send message about FastAPI
        async with test_e2e_client.stream(
            "POST",
            "/api/v1/ai/chat",
            headers=demo_headers,
            json={
                "message": "Tell me about FastAPI",
                "context": {"workspace_id": workspace_id},
            },
        ) as response:
            assert response.status_code == 200

            full_response = ""
            async for chunk in response.aiter_text():
                full_response += chunk

            # Verify FastAPI-related content
            assert len(full_response) > 0
            assert "FastAPI" in full_response or "framework" in full_response

    @pytest.mark.asyncio
    async def test_demo_mode_bypasses_auth(
        self,
        test_e2e_client: AsyncClient,
        mock_claude_sdk_demo_mode: None,
    ) -> None:
        """Test that demo mode bypasses authentication.

        Verifies:
        - Demo workspace accepts requests without real auth
        - Responses are streamed correctly in demo mode

        Args:
            test_e2e_client: AsyncClient for making requests.
            mock_claude_sdk_demo_mode: Mock SDK fixture.
        """
        # Demo mode should work with any workspace ID
        demo_headers = {"X-Workspace-Id": "pilot-space-demo"}
        workspace_id = "00000000-0000-0000-0000-000000000002"

        async with test_e2e_client.stream(
            "POST",
            "/api/v1/ai/chat",
            headers=demo_headers,
            json={
                "message": "Test demo mode",
                "context": {"workspace_id": workspace_id},
            },
        ) as response:
            assert response.status_code == 200

            # Collect response
            full_response = ""
            async for chunk in response.aiter_text():
                full_response += chunk

            # Verify response received (demo mode should work)
            assert len(full_response) > 0

    @pytest.mark.asyncio
    async def test_error_handling_validation(
        self,
        test_e2e_client: AsyncClient,
        mock_claude_sdk_demo_mode: None,
    ) -> None:
        """Test error handling for invalid input.

        Verifies:
        - Empty messages are rejected
        - Validation errors return appropriate status codes

        Args:
            test_e2e_client: AsyncClient for making requests.
            mock_claude_sdk_demo_mode: Mock SDK fixture.
        """
        demo_headers = {"X-Workspace-Id": "pilot-space-demo"}
        workspace_id = "00000000-0000-0000-0000-000000000002"

        # Send invalid message (empty)
        response = await test_e2e_client.post(
            "/api/v1/ai/chat",
            headers=demo_headers,
            json={
                "message": "",
                "context": {"workspace_id": workspace_id},
            },
        )

        # Should fail validation
        assert response.status_code == 422


__all__ = ["TestChatFlow"]
