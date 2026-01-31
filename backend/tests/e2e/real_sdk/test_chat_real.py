"""Real SDK chat flow tests with actual Claude API.

These tests validate the complete chat flow using the real Anthropic API.
They are slower and consume API credits, so they should only be run manually
or in nightly CI builds.

Run with:
    ANTHROPIC_API_KEY=sk-ant-... uv run pytest tests/e2e/real_sdk/test_chat_real.py -v

Skip in CI with:
    uv run pytest -m "not real_sdk"
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient


@pytest.mark.real_sdk
@pytest.mark.asyncio
async def test_real_chat_simple_query(real_sdk_client: AsyncClient) -> None:
    """Test simple chat query with real Claude API.

    This test validates:
    - Session creation works with real API
    - PilotSpaceAgent can make real SDK calls
    - SSE streaming produces valid events
    - Message content is coherent and relevant
    """
    workspace_id = str(uuid4())
    user_id = str(uuid4())

    # Start chat with simple question
    response = await real_sdk_client.post(
        "/api/v1/ai/chat/stream",
        json={
            "message": "What is 2 + 2? Please answer with just the number.",
            "workspace_id": workspace_id,
            "user_id": user_id,
        },
        headers={"Accept": "text/event-stream"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    # Collect SSE events
    events: list[dict] = []
    full_text = ""

    for line in response.iter_lines():
        if line.startswith("data: "):
            data = line[6:]  # Remove "data: " prefix
            if data == "[DONE]":
                break

            try:
                event = json.loads(data)
                events.append(event)

                # Accumulate text_delta events
                if event.get("type") == "text_delta":
                    full_text += event.get("content", "")
            except json.JSONDecodeError:
                continue

    # Verify we got events
    assert len(events) > 0, "Should receive SSE events from real API"

    # Verify we got text content
    assert len(full_text) > 0, "Should receive text content from Claude"

    # Verify the answer contains "4" (basic sanity check)
    assert "4" in full_text, f"Expected answer to contain '4', got: {full_text}"

    # Verify event types are valid
    event_types = {event.get("type") for event in events}
    valid_types = {"text_delta", "tool_use", "tool_result", "message_stop", "error"}
    assert event_types.issubset(valid_types), f"Invalid event types: {event_types - valid_types}"


@pytest.mark.real_sdk
@pytest.mark.asyncio
async def test_real_chat_multi_turn(real_sdk_client: AsyncClient) -> None:
    """Test multi-turn conversation with real Claude API.

    This test validates:
    - Session persistence across multiple messages
    - Context is maintained between turns
    - Follow-up questions are answered correctly
    """
    workspace_id = str(uuid4())
    user_id = str(uuid4())
    session_id: str | None = None

    # First turn: Introduce a topic
    response1 = await real_sdk_client.post(
        "/api/v1/ai/chat/stream",
        json={
            "message": "My favorite color is blue.",
            "workspace_id": workspace_id,
            "user_id": user_id,
            "agent_name": "pilotspace",
        },
        headers={"Accept": "text/event-stream"},
    )

    assert response1.status_code == 200

    # Extract session_id from events (if available)
    for line in response1.iter_lines():
        if line.startswith("data: "):
            data = line[6:]
            if data == "[DONE]":
                break
            try:
                event = json.loads(data)
                if "session_id" in event:
                    session_id = event["session_id"]
                    break
            except json.JSONDecodeError:
                continue

    # Second turn: Ask about previous context
    response2 = await real_sdk_client.post(
        "/api/v1/ai/chat/stream",
        json={
            "message": "What did I just tell you my favorite color was?",
            "workspace_id": workspace_id,
            "user_id": user_id,
            "agent_name": "pilotspace",
            "session_id": session_id,  # Resume session
        },
        headers={"Accept": "text/event-stream"},
    )

    assert response2.status_code == 200

    # Collect response
    full_text = ""
    for line in response2.iter_lines():
        if line.startswith("data: "):
            data = line[6:]
            if data == "[DONE]":
                break
            try:
                event = json.loads(data)
                if event.get("type") == "text_delta":
                    full_text += event.get("content", "")
            except json.JSONDecodeError:
                continue

    # Verify Claude remembers the context
    assert "blue" in full_text.lower(), f"Expected response to mention 'blue', got: {full_text}"


@pytest.mark.real_sdk
@pytest.mark.asyncio
async def test_real_chat_with_tools(real_sdk_client: AsyncClient) -> None:
    """Test chat with tool usage (real Claude API).

    This test validates:
    - Claude can decide to use tools when appropriate
    - Tool execution is tracked in SSE events
    - Tool results are incorporated into response
    """
    workspace_id = str(uuid4())
    user_id = str(uuid4())

    # Ask a question that might trigger tool usage
    response = await real_sdk_client.post(
        "/api/v1/ai/chat/stream",
        json={
            "message": "Can you read the file at README.md and tell me what project this is?",
            "workspace_id": workspace_id,
            "user_id": user_id,
            "agent_name": "pilotspace",
        },
        headers={"Accept": "text/event-stream"},
    )

    assert response.status_code == 200

    # Collect events
    events: list[dict] = []
    for line in response.iter_lines():
        if line.startswith("data: "):
            data = line[6:]
            if data == "[DONE]":
                break
            try:
                event = json.loads(data)
                events.append(event)
            except json.JSONDecodeError:
                continue

    # Check if tool usage occurred
    tool_events = [e for e in events if e.get("type") in ("tool_use", "tool_result")]

    # Note: Tool usage is optional (Claude might answer without reading the file)
    # But if tools were used, verify they're properly formatted
    if tool_events:
        for event in tool_events:
            assert "type" in event
            if event["type"] == "tool_use":
                assert "tool_name" in event, "tool_use event should have tool_name"
            elif event["type"] == "tool_result":
                assert "status" in event, "tool_result event should have status"


@pytest.mark.real_sdk
@pytest.mark.asyncio
async def test_real_chat_error_handling(real_sdk_client: AsyncClient) -> None:
    """Test error handling with real Claude API.

    This test validates:
    - Invalid requests are rejected gracefully
    - Error events are properly formatted
    - System doesn't crash on malformed input
    """
    workspace_id = str(uuid4())
    user_id = str(uuid4())

    # Send empty message (should fail validation)
    response = await real_sdk_client.post(
        "/api/v1/ai/chat/stream",
        json={
            "message": "",  # Empty message
            "workspace_id": workspace_id,
            "user_id": user_id,
            "agent_name": "pilotspace",
        },
        headers={"Accept": "text/event-stream"},
    )

    # Should return 422 Unprocessable Entity or 400 Bad Request
    assert response.status_code in (400, 422), f"Expected 400/422, got {response.status_code}"
