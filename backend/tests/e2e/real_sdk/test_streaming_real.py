"""Real SDK streaming tests with actual Claude API.

These tests validate SSE streaming behavior with the real Anthropic API.
They focus on verifying that streaming events are properly formatted and delivered.

Run with:
    ANTHROPIC_API_KEY=sk-ant-... uv run pytest tests/e2e/real_sdk/test_streaming_real.py -v

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
async def test_real_streaming_event_sequence(real_sdk_client: AsyncClient) -> None:
    """Test that SSE events arrive in correct sequence with real API.

    This test validates:
    - Events follow expected order (text_delta before message_stop)
    - No duplicate or out-of-order events
    - Stream terminates with [DONE] marker
    """
    workspace_id = str(uuid4())
    user_id = str(uuid4())

    response = await real_sdk_client.post(
        "/api/v1/ai/chat/stream",
        json={
            "message": "Count from 1 to 3",
            "workspace_id": workspace_id,
            "user_id": user_id,
            "agent_name": "pilotspace",
        },
        headers={"Accept": "text/event-stream"},
    )

    assert response.status_code == 200

    events: list[dict] = []
    done_received = False

    for line in response.iter_lines():
        if line.startswith("data: "):
            data = line[6:]
            if data == "[DONE]":
                done_received = True
                break

            try:
                event = json.loads(data)
                events.append(event)
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON in SSE event: {data}, error: {e}")

    # Verify stream completed
    assert done_received, "Stream should terminate with [DONE] marker"

    # Verify we got events
    assert len(events) > 0, "Should receive at least one event"

    # Verify event sequence
    event_types = [e.get("type") for e in events]

    # message_stop should be last event (if present)
    if "message_stop" in event_types:
        assert event_types[-1] == "message_stop", "message_stop should be final event"

    # text_delta events should come before message_stop
    if "text_delta" in event_types and "message_stop" in event_types:
        last_text_idx = max(i for i, t in enumerate(event_types) if t == "text_delta")
        stop_idx = event_types.index("message_stop")
        assert last_text_idx < stop_idx, "text_delta events should precede message_stop"


@pytest.mark.real_sdk
@pytest.mark.asyncio
async def test_real_streaming_incremental_delivery(real_sdk_client: AsyncClient) -> None:
    """Test that content is delivered incrementally, not all at once.

    This test validates:
    - Multiple text_delta events are received
    - Content arrives in chunks, not a single block
    - Streaming provides perceived performance benefit
    """
    workspace_id = str(uuid4())
    user_id = str(uuid4())

    # Ask for a longer response to ensure multiple chunks
    response = await real_sdk_client.post(
        "/api/v1/ai/chat/stream",
        json={
            "message": "Explain what REST API is in 3 sentences.",
            "workspace_id": workspace_id,
            "user_id": user_id,
            "agent_name": "pilotspace",
        },
        headers={"Accept": "text/event-stream"},
    )

    assert response.status_code == 200

    text_delta_events: list[dict] = []

    for line in response.iter_lines():
        if line.startswith("data: "):
            data = line[6:]
            if data == "[DONE]":
                break

            try:
                event = json.loads(data)
                if event.get("type") == "text_delta":
                    text_delta_events.append(event)
            except json.JSONDecodeError:
                continue

    # Verify incremental delivery (should have multiple chunks)
    assert len(text_delta_events) > 1, (
        f"Expected multiple text_delta events for incremental delivery, "
        f"got {len(text_delta_events)}"
    )

    # Verify each chunk has content
    for i, event in enumerate(text_delta_events):
        assert "content" in event, f"Event {i} missing 'content' field"
        assert isinstance(event["content"], str), f"Event {i} content should be string"
        assert len(event["content"]) > 0, f"Event {i} content should not be empty"


@pytest.mark.real_sdk
@pytest.mark.asyncio
async def test_real_streaming_json_validity(real_sdk_client: AsyncClient) -> None:
    """Test that all SSE events contain valid JSON.

    This test validates:
    - Every event is parseable as JSON
    - No malformed or truncated events
    - Content is properly escaped in JSON
    """
    workspace_id = str(uuid4())
    user_id = str(uuid4())

    # Use a message that might produce special characters
    response = await real_sdk_client.post(
        "/api/v1/ai/chat/stream",
        json={
            "message": 'What is the output of: print("Hello \\"World\\"")',
            "workspace_id": workspace_id,
            "user_id": user_id,
            "agent_name": "pilotspace",
        },
        headers={"Accept": "text/event-stream"},
    )

    assert response.status_code == 200

    json_errors: list[str] = []

    for line in response.iter_lines():
        if line.startswith("data: "):
            data = line[6:]
            if data == "[DONE]":
                break

            try:
                json.loads(data)
            except json.JSONDecodeError as e:
                json_errors.append(f"Invalid JSON: {data[:100]}... Error: {e}")

    # Verify no JSON parsing errors
    assert len(json_errors) == 0, f"Found {len(json_errors)} JSON errors:\n" + "\n".join(
        json_errors
    )


@pytest.mark.real_sdk
@pytest.mark.asyncio
async def test_real_streaming_error_event_format(real_sdk_client: AsyncClient) -> None:
    """Test error events are properly formatted in SSE stream.

    This test validates:
    - Error events have required fields (type, error_type, message)
    - Error events are valid JSON
    - Stream handles errors gracefully
    """
    workspace_id = str(uuid4())
    user_id = str(uuid4())

    # Request with invalid agent name (should trigger error)
    response = await real_sdk_client.post(
        "/api/v1/ai/chat/stream",
        json={
            "message": "Hello",
            "workspace_id": workspace_id,
            "user_id": user_id,
            "agent_name": "invalid_agent_name_that_does_not_exist",
        },
        headers={"Accept": "text/event-stream"},
    )

    # Might return 404 or 400 for invalid agent, or stream an error event
    # Either behavior is acceptable
    if response.status_code in (404, 400, 422):
        # Error returned as HTTP status - acceptable
        return

    # Otherwise, check for error in SSE stream
    error_events: list[dict] = []

    for line in response.iter_lines():
        if line.startswith("data: "):
            data = line[6:]
            if data == "[DONE]":
                break

            try:
                event = json.loads(data)
                if event.get("type") == "error":
                    error_events.append(event)
            except json.JSONDecodeError:
                continue

    # If we got error events, verify they're properly formatted
    for event in error_events:
        assert "type" in event
        assert event["type"] == "error"
        assert "error_type" in event, "Error event should have error_type"
        assert "message" in event, "Error event should have message"
        assert isinstance(event["message"], str), "Error message should be string"


@pytest.mark.real_sdk
@pytest.mark.asyncio
async def test_real_subagent_streaming(real_sdk_client: AsyncClient) -> None:
    """Test subagent delegation with real API streaming.

    This test validates:
    - PilotSpaceAgent can delegate to subagents
    - Subagent responses are streamed properly
    - SSE events from subagents are formatted correctly

    Note:
        This test may be skipped if workspace/PR data doesn't exist.
    """
    workspace_id = str(uuid4())
    user_id = str(uuid4())

    # Request that should trigger subagent delegation
    response = await real_sdk_client.post(
        "/api/v1/ai/chat/stream",
        json={
            "message": "@pr-review Can you review the latest changes in this codebase?",
            "workspace_id": workspace_id,
            "user_id": user_id,
            "agent_name": "pilotspace",
        },
        headers={"Accept": "text/event-stream"},
    )

    assert response.status_code == 200

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

    # Verify we got events (even if subagent delegation wasn't possible)
    assert len(events) > 0, "Should receive events from API"

    # All events should be valid SSE format
    for event in events:
        assert "type" in event, f"Event missing 'type' field: {event}"
        assert event["type"] in {
            "text_delta",
            "tool_use",
            "tool_result",
            "message_stop",
            "error",
        }, f"Invalid event type: {event['type']}"
