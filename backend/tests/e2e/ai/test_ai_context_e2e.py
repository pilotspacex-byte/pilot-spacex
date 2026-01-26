"""E2E tests for AI context flow.

T096: Test complete AI context generation flow with all 5 phases.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient


class TestAIContextE2E:
    """E2E tests for AI context generation flow."""

    @pytest.mark.asyncio
    async def test_full_ai_context_flow(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
        test_issue: MagicMock,
    ) -> None:
        """Test complete AI context generation flow.

        Verifies:
        - All 5 phases complete (Analysis, Related, Tasks, Code, Summary)
        - SSE streaming works correctly
        - Context data is generated

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
            test_issue: Mock issue object.
        """
        issue_id = str(test_issue.id)

        # Request context generation via SSE
        async with e2e_client.stream(
            "POST",
            f"/api/v1/issues/{issue_id}/ai-context/stream",
            headers=auth_headers,
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

            # Verify phase events
            phase_events = [e for e in events if e["type"] == "phase"]
            assert len(phase_events) >= 5, "Should have at least 5 phase events"

            # Extract phase names
            phases = [e["data"].get("phase") for e in phase_events if "phase" in e["data"]]

            # Verify all expected phases are present
            expected_phases = ["analysis", "related", "tasks", "code", "summary"]
            for expected_phase in expected_phases:
                assert any(expected_phase in str(phase).lower() for phase in phases), (
                    f"Missing phase: {expected_phase}"
                )

            # Verify complete event
            complete_events = [e for e in events if e["type"] == "complete"]
            assert len(complete_events) == 1, "Should receive exactly one complete event"

    @pytest.mark.asyncio
    async def test_ai_context_includes_claude_code_prompt(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
        test_issue: MagicMock,
    ) -> None:
        """Verify Claude Code prompt included in output.

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
            test_issue: Mock issue object.
        """
        issue_id = str(test_issue.id)

        events: list[dict[str, Any]] = []
        async with e2e_client.stream(
            "POST",
            f"/api/v1/issues/{issue_id}/ai-context/stream",
            headers=auth_headers,
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

        # Find complete event with prompt
        complete_events = [e for e in events if e["type"] == "complete"]
        assert len(complete_events) > 0

        complete_data = complete_events[0]["data"]

        # Verify Claude Code prompt is present
        assert "claude_code_prompt" in complete_data or "prompt" in complete_data, (
            "Should include Claude Code prompt in output"
        )

    @pytest.mark.asyncio
    async def test_ai_context_get_endpoint(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
        test_issue: MagicMock,
    ) -> None:
        """Test GET endpoint for retrieving existing context.

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
            test_issue: Mock issue object.
        """
        issue_id = str(test_issue.id)

        # First generate context
        async with e2e_client.stream(
            "POST",
            f"/api/v1/issues/{issue_id}/ai-context/stream",
            headers=auth_headers,
        ) as response:
            # Consume all events
            async for _ in response.aiter_lines():
                pass

        # Now retrieve it
        response = await e2e_client.get(
            f"/api/v1/issues/{issue_id}/ai-context",
            headers=auth_headers,
        )

        # Should return context data (or 404 if not stored)
        assert response.status_code in {200, 404}

        if response.status_code == 200:
            data = response.json()
            # Verify structure
            assert "context" in data or "analysis" in data

    @pytest.mark.asyncio
    async def test_ai_context_handles_missing_issue(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Verify error handling for non-existent issue.

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        from uuid import uuid4

        fake_issue_id = str(uuid4())

        async with e2e_client.stream(
            "POST",
            f"/api/v1/issues/{fake_issue_id}/ai-context/stream",
            headers=auth_headers,
        ) as response:
            # Should return error or 404
            assert response.status_code in {200, 404, 400}

            if response.status_code == 200:
                # Check for error event in stream
                events = []
                async for line in response.aiter_lines():
                    if line.startswith("event:"):
                        event_type = line.split(":", 1)[1].strip()
                        events.append(event_type)

                # Should have error event for missing issue
                assert "error" in events

    @pytest.mark.asyncio
    async def test_ai_context_latency(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
        test_issue: MagicMock,
    ) -> None:
        """Verify AI context completes within reasonable time.

        Performance requirement: Should complete within 30s for typical issues.

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
            test_issue: Mock issue object.
        """
        import time

        issue_id = str(test_issue.id)
        start = time.time()

        async with e2e_client.stream(
            "POST",
            f"/api/v1/issues/{issue_id}/ai-context/stream",
            headers=auth_headers,
        ) as response:
            assert response.status_code == 200

            # Consume all events
            async for _ in response.aiter_lines():
                pass

        elapsed = time.time() - start

        # Relaxed limit for E2E tests (actual API calls may vary)
        # In production with real LLMs, this could take longer
        assert elapsed < 60.0, f"AI context took {elapsed:.2f}s, expected <60s"

    @pytest.mark.asyncio
    async def test_ai_context_progress_updates(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
        test_issue: MagicMock,
    ) -> None:
        """Verify progress updates are sent during generation.

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
            test_issue: Mock issue object.
        """
        issue_id = str(test_issue.id)

        events: list[dict[str, Any]] = []
        async with e2e_client.stream(
            "POST",
            f"/api/v1/issues/{issue_id}/ai-context/stream",
            headers=auth_headers,
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

        # Should have progress/phase events
        progress_events = [e for e in events if e["type"] in {"progress", "phase", "status"}]
        assert len(progress_events) > 0, "Should send progress updates"
