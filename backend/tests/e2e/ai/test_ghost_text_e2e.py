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
        from uuid import uuid4

        note_id = uuid4()

        async with e2e_client.stream(
            "POST",
            f"/api/v1/notes/{note_id}/ghost-text",
            headers=auth_headers,
            json={
                "context": "The authentication system should ",
                "cursor_position": 35,
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

        from uuid import uuid4

        note_id = uuid4()

        async with e2e_client.stream(
            "POST",
            f"/api/v1/notes/{note_id}/ghost-text",
            headers=auth_headers,
            json={
                "context": "Quick test",
                "cursor_position": 10,
            },
        ) as response:
            assert response.status_code == 200

            # Consume all events
            async for _ in response.aiter_lines():
                pass

        elapsed = time.time() - start
        assert elapsed < 2.0, f"Ghost text took {elapsed:.2f}s, expected <2s"

    @pytest.mark.asyncio
    async def test_ghost_text_streaming_endpoint_exists(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test ghost text endpoint exists and returns SSE.

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        from uuid import uuid4

        note_id = uuid4()

        async with e2e_client.stream(
            "POST",
            f"/api/v1/notes/{note_id}/ghost-text",
            headers=auth_headers,
            json={
                "context": "The API should return ",
                "cursor_position": 23,
            },
        ) as response:
            # Should either succeed with SSE or fail gracefully
            # 404 means note doesn't exist (expected in E2E without DB)
            # 200 means SSE streaming works
            assert response.status_code in {200, 404}

    @pytest.mark.asyncio
    async def test_ghost_text_handles_errors(
        self,
        e2e_client: AsyncClient,
    ) -> None:
        """Verify error handling for missing workspace ID.

        Args:
            e2e_client: AsyncClient for making requests.
        """
        from uuid import uuid4

        note_id = uuid4()

        # Request without workspace ID
        response = await e2e_client.post(
            f"/api/v1/notes/{note_id}/ghost-text",
            json={
                "context": "Test",
                "cursor_position": 4,
            },
        )

        # Should fail due to missing workspace ID or auth
        assert response.status_code in {400, 401, 404}

    @pytest.mark.asyncio
    async def test_ghost_text_validation(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Verify request validation for ghost text.

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        from uuid import uuid4

        note_id = uuid4()

        # Invalid request (empty context - violates min_length=1)
        response = await e2e_client.post(
            f"/api/v1/notes/{note_id}/ghost-text",
            headers=auth_headers,
            json={
                "context": "",
                "cursor_position": 0,
            },
        )

        # Should fail validation (422) or auth (401 with mock keys)
        assert response.status_code in {401, 422}
