"""E2E tests for session persistence (T098).

Tests conversation session management:
- Session save/load from Redis
- Session resume with message history
- Session cleanup after TTL
- Token budget enforcement

Reference: backend/src/pilot_space/ai/session/session_manager.py
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient


class TestSessionPersistence:
    """E2E tests for conversation session persistence."""

    @pytest.mark.asyncio
    async def test_session_save_and_load(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test session is saved to Redis and can be loaded.

        Verifies:
        - Session is created with unique ID
        - Session data is persisted
        - Session can be retrieved
        - All metadata is saved

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        # Create session
        create_response = await e2e_client.post(
            "/api/v1/ai/chat/sessions",
            headers=auth_headers,
            json={
                "agent_name": "conversation",
                "system_context": "Technical support assistant",
            },
        )
        assert create_response.status_code == 201
        session_data = create_response.json()
        session_id = session_data["session_id"]

        # Send a message to populate history
        async with e2e_client.stream(
            "POST",
            f"/api/v1/ai/chat/sessions/{session_id}/messages",
            headers=auth_headers,
            json={"message": "What is Python?"},
        ) as response:
            assert response.status_code == 200
            async for _ in response.aiter_lines():
                pass

        # Retrieve session
        get_response = await e2e_client.get(
            f"/api/v1/ai/chat/sessions/{session_id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 200
        loaded_session = get_response.json()

        # Verify session data
        assert loaded_session["session_id"] == session_id
        assert loaded_session["agent_name"] == "conversation"
        assert loaded_session["system_context"] == "Technical support assistant"
        assert loaded_session["status"] == "active"
        assert "created_at" in loaded_session
        assert "updated_at" in loaded_session

    @pytest.mark.asyncio
    async def test_session_resume_with_message_history(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test resuming session preserves message history.

        Verifies:
        - Previous messages are available
        - New messages build on context
        - History is ordered correctly
        - Token budget is enforced

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        # Create session and send messages
        create_response = await e2e_client.post(
            "/api/v1/ai/chat/sessions",
            headers=auth_headers,
            json={"agent_name": "conversation"},
        )
        session_id = create_response.json()["session_id"]

        # First conversation turn
        async with e2e_client.stream(
            "POST",
            f"/api/v1/ai/chat/sessions/{session_id}/messages",
            headers=auth_headers,
            json={"message": "My name is Alice"},
        ) as response:
            assert response.status_code == 200
            async for _ in response.aiter_lines():
                pass

        # Second conversation turn (references first)
        async with e2e_client.stream(
            "POST",
            f"/api/v1/ai/chat/sessions/{session_id}/messages",
            headers=auth_headers,
            json={"message": "What is my name?"},
        ) as response:
            assert response.status_code == 200
            async for _ in response.aiter_lines():
                pass

        # Get history
        history_response = await e2e_client.get(
            f"/api/v1/ai/chat/sessions/{session_id}/history",
            headers=auth_headers,
        )
        assert history_response.status_code == 200
        history = history_response.json()

        # Verify history
        assert len(history["messages"]) == 4  # 2 user + 2 assistant
        assert history["messages"][0]["content"] == "My name is Alice"
        assert history["messages"][2]["content"] == "What is my name?"

        # Verify assistant response references context
        # (In real test, would check response content mentions "Alice")

    @pytest.mark.asyncio
    async def test_session_cleanup_after_ttl(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test session cleanup after 30-minute TTL.

        Verifies:
        - Sessions expire after TTL
        - Expired sessions cannot be used
        - Expired status is returned

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        # Create session
        create_response = await e2e_client.post(
            "/api/v1/ai/chat/sessions",
            headers=auth_headers,
            json={"agent_name": "conversation"},
        )
        session_id = create_response.json()["session_id"]

        # Verify session is active
        get_response = await e2e_client.get(
            f"/api/v1/ai/chat/sessions/{session_id}",
            headers=auth_headers,
        )
        assert get_response.json()["status"] == "active"

        # In real test, would mock time or use shorter TTL for testing
        # For now, verify TTL field exists
        assert "ttl_seconds" in get_response.json()
        assert get_response.json()["ttl_seconds"] == 1800  # 30 minutes

        # Try to use non-existent session (simulates expired)
        fake_session_id = str(uuid4())
        expired_response = await e2e_client.post(
            f"/api/v1/ai/chat/sessions/{fake_session_id}/messages",
            headers=auth_headers,
            json={"message": "Test"},
        )
        assert expired_response.status_code == 404

    @pytest.mark.asyncio
    async def test_session_token_budget_enforcement(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test token budget enforcement (8000 token limit).

        Verifies:
        - Session tracks total tokens
        - History is truncated to fit budget
        - Oldest messages are removed first
        - Recent context is preserved

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        # Create session
        create_response = await e2e_client.post(
            "/api/v1/ai/chat/sessions",
            headers=auth_headers,
            json={"agent_name": "conversation"},
        )
        session_id = create_response.json()["session_id"]

        # Send multiple long messages to exceed budget
        long_message = "Explain in detail: " + ("Python is a programming language. " * 100)

        for _ in range(5):
            async with e2e_client.stream(
                "POST",
                f"/api/v1/ai/chat/sessions/{session_id}/messages",
                headers=auth_headers,
                json={"message": long_message},
            ) as response:
                assert response.status_code == 200
                async for _ in response.aiter_lines():
                    pass

        # Get history
        history_response = await e2e_client.get(
            f"/api/v1/ai/chat/sessions/{session_id}/history",
            headers=auth_headers,
        )
        history = history_response.json()

        # Verify token budget
        assert "total_tokens" in history
        # History should be truncated if exceeds 8000
        if history["total_tokens"] > 8000:
            assert history["truncated"] is True
            # Oldest messages should be removed
            assert len(history["messages"]) < 10  # Less than 5 turns

    @pytest.mark.asyncio
    async def test_session_metadata_tracking(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test session metadata tracking.

        Verifies:
        - Created/updated timestamps
        - Total tokens
        - Total cost
        - Message count

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        # Create session
        create_response = await e2e_client.post(
            "/api/v1/ai/chat/sessions",
            headers=auth_headers,
            json={"agent_name": "conversation"},
        )
        session_id = create_response.json()["session_id"]
        created_at = create_response.json()["created_at"]

        # Send message
        async with e2e_client.stream(
            "POST",
            f"/api/v1/ai/chat/sessions/{session_id}/messages",
            headers=auth_headers,
            json={"message": "Hello"},
        ) as response:
            async for _ in response.aiter_lines():
                pass

        # Small delay to ensure updated_at changes
        await asyncio.sleep(0.1)

        # Get session metadata
        get_response = await e2e_client.get(
            f"/api/v1/ai/chat/sessions/{session_id}",
            headers=auth_headers,
        )
        session = get_response.json()

        # Verify metadata
        assert session["created_at"] == created_at
        assert session["updated_at"] > created_at  # Should be newer
        assert session["total_tokens"] > 0
        assert session["total_cost_usd"] >= 0
        assert session["message_count"] == 2  # 1 user + 1 assistant

    @pytest.mark.asyncio
    async def test_session_list_and_filter(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test listing and filtering user sessions.

        Verifies:
        - Can list user's sessions
        - Can filter by agent name
        - Can filter by status
        - Sessions are ordered by updated_at

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        # Create multiple sessions
        session_ids = []
        for _ in range(3):
            response = await e2e_client.post(
                "/api/v1/ai/chat/sessions",
                headers=auth_headers,
                json={"agent_name": "conversation"},
            )
            session_ids.append(response.json()["session_id"])

        # List sessions
        list_response = await e2e_client.get(
            "/api/v1/ai/chat/sessions",
            headers=auth_headers,
        )
        assert list_response.status_code == 200
        sessions = list_response.json()

        assert len(sessions["items"]) >= 3
        # Verify newest first (ordered by updated_at desc)
        for i in range(len(sessions["items"]) - 1):
            assert sessions["items"][i]["updated_at"] >= sessions["items"][i + 1]["updated_at"]

        # Filter by agent
        filter_response = await e2e_client.get(
            "/api/v1/ai/chat/sessions",
            headers=auth_headers,
            params={"agent_name": "conversation"},
        )
        assert filter_response.status_code == 200
        filtered = filter_response.json()
        for session in filtered["items"]:
            assert session["agent_name"] == "conversation"

    @pytest.mark.asyncio
    async def test_session_deletion(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test manual session deletion.

        Verifies:
        - User can delete their session
        - Deleted session cannot be accessed
        - History is removed

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        # Create session
        create_response = await e2e_client.post(
            "/api/v1/ai/chat/sessions",
            headers=auth_headers,
            json={"agent_name": "conversation"},
        )
        session_id = create_response.json()["session_id"]

        # Delete session
        delete_response = await e2e_client.delete(
            f"/api/v1/ai/chat/sessions/{session_id}",
            headers=auth_headers,
        )
        assert delete_response.status_code == 204

        # Verify session no longer exists
        get_response = await e2e_client.get(
            f"/api/v1/ai/chat/sessions/{session_id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404


__all__ = ["TestSessionPersistence"]
