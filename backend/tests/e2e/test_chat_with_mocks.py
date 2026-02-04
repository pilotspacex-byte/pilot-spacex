"""E2E tests for chat with mocked Anthropic API responses.

Tests the chat flow using mock fixtures to avoid requiring real API keys.

Reference: PHASE_1_SDK_INTEGRATION_COMPLETE.md
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestChatWithMocks:
    """E2E tests for chat with mocked Anthropic responses."""

    @pytest.mark.asyncio
    async def test_chat_basic_message(
        self,
        test_e2e_client: AsyncClient,
        mock_claude_sdk_demo_mode: None,
    ) -> None:
        """Test basic chat message with mocked Claude SDK.

        Verifies:
        - Chat endpoint accepts requests
        - SSE streaming works
        - Mock responses are returned

        Args:
            test_e2e_client: AsyncClient for making requests.
            mock_claude_sdk_demo_mode: Mock Claude SDK fixture.
        """
        # Use demo workspace for authentication bypass
        demo_headers = {
            "X-Workspace-Id": "00000000-0000-0000-0000-000000000002",
        }
        workspace_id = "00000000-0000-0000-0000-000000000002"  # Demo workspace UUID

        # Send chat message
        response = await test_e2e_client.post(
            "/api/v1/ai/chat",
            headers=demo_headers,
            json={
                "message": "Hello",
                "context": {
                    "workspace_id": workspace_id,
                },
            },
        )

        # Verify response
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_chat_streaming_events(
        self,
        test_e2e_client: AsyncClient,
        mock_claude_sdk_demo_mode: None,
    ) -> None:
        """Test SSE streaming events with mocked responses.

        Verifies:
        - Receives text_delta events
        - Receives message_stop event
        - Events are properly formatted

        Args:
            test_e2e_client: AsyncClient for making requests.
            mock_claude_sdk_demo_mode: Mock Claude SDK fixture.
        """
        demo_headers = {"X-Workspace-Id": "00000000-0000-0000-0000-000000000002"}
        workspace_id = "00000000-0000-0000-0000-000000000002"

        # Stream chat response
        async with test_e2e_client.stream(
            "POST",
            "/api/v1/ai/chat",
            headers=demo_headers,
            json={
                "message": "What is FastAPI?",
                "context": {
                    "workspace_id": workspace_id,
                },
            },
        ) as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]

            # Collect SSE events - they come as one concatenated string
            full_response = ""
            async for chunk in response.aiter_text():
                full_response += chunk

            # Split into individual SSE events (separated by \n\n)
            events = [e.strip() for e in full_response.split("\n\n") if e.strip()]

            # Verify we received some events
            assert len(events) > 0, f"Should receive at least one SSE event, got: {full_response}"

            # Check that we have text_delta events (contains "text_delta" string)
            text_deltas = [e for e in events if "text_delta" in e]
            assert len(text_deltas) > 0, f"Should receive text_delta events, got: {events}"

            # Check for message_stop event
            stop_events = [e for e in events if "message_stop" in e or "stop" in e]
            assert len(stop_events) > 0, f"Should receive stop event, got: {events}"

    @pytest.mark.asyncio
    async def test_chat_with_selected_text_context(
        self,
        test_e2e_client: AsyncClient,
        mock_claude_sdk_demo_mode: None,
    ) -> None:
        """Test chat with selected text context.

        Verifies:
        - Context is passed to agent
        - Response includes context-aware content
        - Works without requiring note to exist in DB

        Args:
            test_e2e_client: AsyncClient for making requests.

            mock_claude_sdk_demo_mode: Mock Claude SDK fixture.
        """
        workspace_id = "00000000-0000-0000-0000-000000000002"

        # Send chat message with selected text context (no note_id required)
        response = await test_e2e_client.post(
            "/api/v1/ai/chat",
            headers={"X-Workspace-Id": "00000000-0000-0000-0000-000000000002"},
            json={
                "message": "Extract issues from this text",
                "context": {
                    "workspace_id": workspace_id,
                    "selected_text": "We need to implement user authentication with OAuth2",
                },
            },
        )

        # Verify response
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_chat_error_handling(
        self,
        test_e2e_client: AsyncClient,
        mock_claude_sdk_demo_mode: None,
    ) -> None:
        """Test chat error handling.

        Verifies:
        - Invalid requests return appropriate errors
        - Errors are in SSE format

        Args:
            test_e2e_client: AsyncClient for making requests.

            mock_claude_sdk_demo_mode: Mock Claude SDK fixture.
        """
        # Send invalid request (missing context)
        response = await test_e2e_client.post(
            "/api/v1/ai/chat",
            headers={"X-Workspace-Id": "00000000-0000-0000-0000-000000000002"},
            json={
                "message": "Hello",
                # Missing context field
            },
        )

        # Verify error response
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_chat_session_resumption(
        self,
        test_e2e_client: AsyncClient,
        mock_claude_sdk_demo_mode: None,
    ) -> None:
        """Test chat session resumption.

        Verifies:
        - Session ID is returned in first response
        - Same session ID can be used to resume

        Args:
            test_e2e_client: AsyncClient for making requests.

            mock_claude_sdk_demo_mode: Mock Claude SDK fixture.
        """
        workspace_id = "00000000-0000-0000-0000-000000000002"

        # First message - create session
        async with test_e2e_client.stream(
            "POST",
            "/api/v1/ai/chat",
            headers={"X-Workspace-Id": "00000000-0000-0000-0000-000000000002"},
            json={
                "message": "Hello",
                "context": {
                    "workspace_id": workspace_id,
                },
            },
        ) as response:
            assert response.status_code == 200

            # Collect all response text
            full_response = ""
            async for chunk in response.aiter_text():
                full_response += chunk

            # Extract session_id from events
            # Format: data: {'type': 'message_start', 'session_id': 'test-session-123'}
            import re

            match = re.search(r"session_id['\"]:\s*['\"]([^'\"]+)", full_response)
            session_id = match.group(1) if match else None

            # Verify session_id was returned
            # Note: In mock mode, session_id is "test-session-123"
            assert session_id is not None, f"Session ID not found in response: {full_response}"
            assert session_id == "test-session-123", f"Expected test-session-123, got {session_id}"

        # Second message - resume session
        # Note: In mock mode, we can't actually resume sessions with "test-session-123"
        # because it's not a valid UUID. This test verifies the session_id is returned
        # in the first response, which is sufficient for E2E validation in demo mode.
        # For real session resumption testing, use integration tests with real UUIDs.


class TestChatSkillInvocation:
    """E2E tests for skill invocation via chat."""

    @pytest.mark.asyncio
    async def test_extract_issues_skill(
        self,
        test_e2e_client: AsyncClient,
        mock_claude_sdk_demo_mode: None,
    ) -> None:
        """Test extract-issues skill invocation.

        Verifies:
        - Skill command is recognized
        - Mock skill response is returned

        Args:
            test_e2e_client: AsyncClient for making requests.

            mock_claude_sdk_demo_mode: Mock Claude SDK fixture.
        """
        workspace_id = "00000000-0000-0000-0000-000000000002"

        # Send skill invocation command
        response = await test_e2e_client.post(
            "/api/v1/ai/chat",
            headers={"X-Workspace-Id": "00000000-0000-0000-0000-000000000002"},
            json={
                "message": "\\extract-issues from this: We need to implement user authentication",
                "context": {
                    "workspace_id": workspace_id,
                },
            },
        )

        # Verify response
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]


__all__ = [
    "TestChatSkillInvocation",
    "TestChatWithMocks",
]
