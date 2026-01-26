"""E2E tests for ghost text flow.

T095: Test complete ghost text suggestion flow with SSE streaming.
"""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient


class TestGhostTextE2E:
    """E2E tests for ghost text suggestion flow."""

    @pytest.mark.asyncio
    async def test_full_ghost_text_flow(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test complete ghost text suggestion flow.

        Verifies:
        - SSE streaming works correctly
        - Token events are received
        - Suggestion is generated

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        # Request ghost text with streaming
        async with e2e_client.stream(
            "POST",
            "/api/v1/ai/ghost-text?stream=true",
            headers=auth_headers,
            json={
                "current_text": "The authentication system should ",
                "cursor_position": 35,
                "context": "Building OAuth2 authentication for web application",
                "is_code": False,
            },
        ) as response:
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream"

            # Collect all events
            events: list[dict[str, Any]] = []
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

            # Verify we received token events
            token_events = [e for e in events if e["type"] == "token"]
            assert len(token_events) > 0, "Should receive at least one token event"

            # Verify done event
            done_events = [e for e in events if e["type"] == "done"]
            assert len(done_events) == 1, "Should receive exactly one done event"

    @pytest.mark.asyncio
    async def test_ghost_text_latency(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Verify ghost text completes within 2s.

        Performance requirement: P95 latency < 2s

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        start = time.time()

        async with e2e_client.stream(
            "POST",
            "/api/v1/ai/ghost-text?stream=true",
            headers=auth_headers,
            json={
                "current_text": "Quick test",
                "cursor_position": 10,
                "is_code": False,
            },
        ) as response:
            assert response.status_code == 200

            # Consume all events
            async for _ in response.aiter_lines():
                pass

        elapsed = time.time() - start
        assert elapsed < 2.0, f"Ghost text took {elapsed:.2f}s, expected <2s"

    @pytest.mark.asyncio
    async def test_ghost_text_non_streaming(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test ghost text without streaming (JSON response).

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        response = await e2e_client.post(
            "/api/v1/ai/ghost-text?stream=false",
            headers=auth_headers,
            json={
                "current_text": "The API should return ",
                "cursor_position": 23,
                "is_code": True,
                "language": "python",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "suggestion" in data
        assert isinstance(data["suggestion"], str)
        assert "cursor_offset" in data
        assert "is_empty" in data

    @pytest.mark.asyncio
    async def test_ghost_text_handles_errors(
        self,
        e2e_client: AsyncClient,
    ) -> None:
        """Verify error handling for missing API keys.

        Args:
            e2e_client: AsyncClient for making requests.
        """
        # Request without API keys
        response = await e2e_client.post(
            "/api/v1/ai/ghost-text",
            headers={"X-Workspace-ID": "pilot-space-demo"},
            json={
                "current_text": "Test",
                "cursor_position": 4,
            },
        )

        # Should fail due to missing API key
        assert response.status_code in {400, 401, 500}

    @pytest.mark.asyncio
    async def test_ghost_text_sse_error_events(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Verify SSE error events for invalid requests.

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        # Invalid request (empty text)
        async with e2e_client.stream(
            "POST",
            "/api/v1/ai/ghost-text?stream=true",
            headers=auth_headers,
            json={
                "current_text": "",
                "cursor_position": 0,
            },
        ) as response:
            # May succeed but return error event or fail validation
            if response.status_code == 200:
                events = []
                async for line in response.aiter_lines():
                    if line.startswith("event:"):
                        event_type = line.split(":", 1)[1].strip()
                        events.append(event_type)

                # Should either have error event or complete gracefully
                assert "error" in events or "done" in events
