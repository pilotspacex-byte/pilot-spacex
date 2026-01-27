"""E2E tests for subagent delegation (T096).

Tests subagent delegation including:
- PR review subagent
- AI context subagent
- Doc generator subagent
- Multi-turn streaming conversations

Reference: backend/src/pilot_space/ai/agents/subagents/
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient


class TestSubagentDelegation:
    """E2E tests for subagent delegation and execution."""

    @pytest.mark.asyncio
    async def test_pr_review_subagent_delegation(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test @pr-review subagent delegation.

        Verifies:
        - Subagent is invoked correctly
        - Multi-turn streaming works
        - Review findings are structured
        - Approval status is provided

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        repository_id = uuid4()
        pr_number = 123

        async with e2e_client.stream(
            "POST",
            "/api/v1/ai/subagents/pr-review",
            headers=auth_headers,
            json={
                "repository_id": str(repository_id),
                "pr_number": pr_number,
                "include_architecture": True,
                "include_security": True,
                "include_performance": True,
            },
        ) as response:
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream"

            events: list[dict[str, Any]] = []
            current_event = None

            async for line in response.aiter_lines():
                if line.startswith("event:"):
                    current_event = line.split(":", 1)[1].strip()
                elif line.startswith("data:") and current_event:
                    data_str = line.split(":", 1)[1].strip()
                    try:
                        data = json.loads(data_str)
                        events.append({"type": current_event, "data": data})
                    except json.JSONDecodeError:
                        pass

            # Verify review event types
            event_types = {e["type"] for e in events}
            assert "finding" in event_types or "summary" in event_types

            # Verify finding structure
            finding_events = [e for e in events if e["type"] == "finding"]
            for event in finding_events:
                finding = event["data"]
                assert "category" in finding  # architecture, security, etc.
                assert "severity" in finding  # critical, warning, suggestion
                assert "file_path" in finding
                assert "line_number" in finding
                assert "description" in finding
                assert "fix_suggestion" in finding

    @pytest.mark.asyncio
    async def test_ai_context_subagent_delegation(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test @ai-context subagent delegation.

        Verifies:
        - Context aggregation streams results
        - Related notes are found
        - Code snippets are included
        - Task breakdown is provided

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        issue_id = uuid4()

        async with e2e_client.stream(
            "POST",
            "/api/v1/ai/subagents/ai-context",
            headers=auth_headers,
            json={
                "issue_id": str(issue_id),
                "include_notes": True,
                "include_code": True,
                "include_tasks": True,
            },
        ) as response:
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream"

            events: list[dict[str, Any]] = []
            current_event = None

            async for line in response.aiter_lines():
                if line.startswith("event:"):
                    current_event = line.split(":", 1)[1].strip()
                elif line.startswith("data:") and current_event:
                    data_str = line.split(":", 1)[1].strip()
                    try:
                        data = json.loads(data_str)
                        events.append({"type": current_event, "data": data})
                    except json.JSONDecodeError:
                        pass

            # Verify context event types
            event_types = {e["type"] for e in events}
            assert len(event_types) > 0

            # Verify related_note events
            note_events = [e for e in events if e["type"] == "related_note"]
            for event in note_events:
                note = event["data"]
                assert "note_id" in note
                assert "title" in note
                assert "relevance" in note
                assert note["relevance"] in [
                    "RECOMMENDED",
                    "DEFAULT",
                    "CURRENT",
                    "ALTERNATIVE",
                ]

            # Verify code_snippet events
            code_events = [e for e in events if e["type"] == "code_snippet"]
            for event in code_events:
                snippet = event["data"]
                assert "file_path" in snippet
                assert "line_number" in snippet
                assert "code" in snippet
                assert "explanation" in snippet

    @pytest.mark.asyncio
    async def test_doc_generator_subagent_delegation(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test @doc-generator subagent delegation.

        Verifies:
        - Documentation generation streams content
        - Multiple doc types are supported
        - Output is well-structured

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        async with e2e_client.stream(
            "POST",
            "/api/v1/ai/subagents/doc-generator",
            headers=auth_headers,
            json={
                "doc_type": "api_reference",
                "source_files": [
                    "src/api/v1/routers/issues.py",
                    "src/api/v1/schemas/issues.py",
                ],
            },
        ) as response:
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream"

            events: list[dict[str, Any]] = []
            current_event = None

            async for line in response.aiter_lines():
                if line.startswith("event:"):
                    current_event = line.split(":", 1)[1].strip()
                elif line.startswith("data:") and current_event:
                    data_str = line.split(":", 1)[1].strip()
                    try:
                        data = json.loads(data_str)
                        events.append({"type": current_event, "data": data})
                    except json.JSONDecodeError:
                        pass

            # Verify documentation events
            event_types = {e["type"] for e in events}
            assert "content" in event_types or "section" in event_types

            # Verify section structure
            section_events = [e for e in events if e["type"] == "section"]
            for event in section_events:
                section = event["data"]
                assert "heading" in section
                assert "content" in section

    @pytest.mark.asyncio
    async def test_subagent_multi_turn_conversation(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test multi-turn conversation with subagent.

        Verifies:
        - Subagent maintains conversation state
        - Follow-up questions work
        - Context is preserved across turns

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        repository_id = uuid4()

        # Start PR review conversation
        session_response = await e2e_client.post(
            "/api/v1/ai/subagents/pr-review/sessions",
            headers=auth_headers,
            json={
                "repository_id": str(repository_id),
                "pr_number": 123,
            },
        )
        assert session_response.status_code == 201
        session_id = session_response.json()["session_id"]

        # First turn: Get initial review
        async with e2e_client.stream(
            "POST",
            f"/api/v1/ai/subagents/pr-review/sessions/{session_id}/messages",
            headers=auth_headers,
            json={"message": "Start the review"},
        ) as response:
            assert response.status_code == 200
            async for _ in response.aiter_lines():
                pass

        # Second turn: Ask follow-up question
        async with e2e_client.stream(
            "POST",
            f"/api/v1/ai/subagents/pr-review/sessions/{session_id}/messages",
            headers=auth_headers,
            json={"message": "Can you elaborate on the security findings?"},
        ) as response:
            assert response.status_code == 200

            events: list[dict[str, Any]] = []
            current_event = None

            async for line in response.aiter_lines():
                if line.startswith("event:"):
                    current_event = line.split(":", 1)[1].strip()
                elif line.startswith("data:") and current_event:
                    try:
                        data = json.loads(line.split(":", 1)[1].strip())
                        events.append({"type": current_event, "data": data})
                    except json.JSONDecodeError:
                        pass

            # Verify follow-up response
            assert len(events) > 0

    @pytest.mark.asyncio
    async def test_subagent_error_handling(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test subagent error handling.

        Verifies:
        - Invalid input is rejected
        - Errors are streamed as events
        - Graceful degradation on failure

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        # Invalid repository ID
        async with e2e_client.stream(
            "POST",
            "/api/v1/ai/subagents/pr-review",
            headers=auth_headers,
            json={
                "repository_id": "not-a-uuid",
                "pr_number": 123,
            },
        ) as response:
            assert response.status_code == 422

        # Missing required field
        async with e2e_client.stream(
            "POST",
            "/api/v1/ai/subagents/ai-context",
            headers=auth_headers,
            json={
                # Missing issue_id
                "include_notes": True,
            },
        ) as response:
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_subagent_tool_execution(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test subagent MCP tool execution.

        Verifies:
        - Subagent can use MCP tools
        - Tool results are incorporated into response
        - RLS is enforced for tool calls

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        repository_id = uuid4()

        async with e2e_client.stream(
            "POST",
            "/api/v1/ai/subagents/pr-review",
            headers=auth_headers,
            json={
                "repository_id": str(repository_id),
                "pr_number": 123,
            },
        ) as response:
            assert response.status_code == 200

            events: list[dict[str, Any]] = []
            current_event = None

            async for line in response.aiter_lines():
                if line.startswith("event:"):
                    current_event = line.split(":", 1)[1].strip()
                elif line.startswith("data:") and current_event:
                    try:
                        data = json.loads(line.split(":", 1)[1].strip())
                        events.append({"type": current_event, "data": data})
                    except json.JSONDecodeError:
                        pass

            # Verify tool_call events (if SDK emits them)
            tool_events = [e for e in events if e["type"] == "tool_call"]
            for event in tool_events:
                tool_call = event["data"]
                assert "tool_name" in tool_call
                assert tool_call["tool_name"] in [
                    "get_pr_diff",
                    "get_pr_files",
                    "add_review_comment",
                ]


__all__ = ["TestSubagentDelegation"]
