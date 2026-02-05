"""Unit tests for StreamEvent transformation and deduplication.

Tests the transform_stream_event() function and its integration with
transform_sdk_message() for real-time SSE forwarding of thinking blocks,
tool calls, and text deltas from Claude Agent SDK StreamEvent objects.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from pilot_space.ai.agents.pilotspace_agent_helpers import (
    transform_sdk_message,
    transform_tool_result,
)
from pilot_space.ai.agents.stream_event_transformer import transform_stream_event


class MockStreamEvent:
    """Mock SDK StreamEvent with raw Anthropic API event data."""

    def __init__(
        self,
        event: dict[str, Any],
        parent_tool_use_id: str | None = None,
        uuid: str | None = None,
        session_id: str = "test-session",
    ) -> None:
        self.event = event
        self.parent_tool_use_id = parent_tool_use_id
        self.uuid = uuid or str(uuid4())
        self.session_id = session_id
        self.__class__ = type(
            "StreamEvent",
            (),
            {
                "__name__": "StreamEvent",
            },
        )
        self.__class__.__name__ = "StreamEvent"


class MockAssistantMessage:
    """Mock SDK AssistantMessage."""

    def __init__(self, content: list[Any]) -> None:
        self.content = content
        self.__class__ = type(
            "AssistantMessage",
            (),
            {
                "__name__": "AssistantMessage",
            },
        )
        self.__class__.__name__ = "AssistantMessage"


def _make_holder(message_id: str = "msg-123") -> dict[str, Any]:
    """Create a fresh current_message_id_holder."""
    return {"_current_message_id": message_id}


class TestTransformStreamEventThinking:
    """Test thinking block streaming."""

    def test_thinking_content_block_start(self) -> None:
        """StreamEvent with thinking content_block_start emits content_block_start."""
        holder = _make_holder()
        result = transform_stream_event(
            event_data={
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "thinking"},
            },
            parent_tool_use_id=None,
            current_message_id_holder=holder,
        )

        assert result is not None
        assert "event: content_block_start" in result
        data = json.loads(result.split("data: ")[1].split("\n")[0])
        assert data["contentType"] == "thinking"
        assert data["index"] == 0

    def test_thinking_delta(self) -> None:
        """StreamEvent with thinking_delta emits thinking_delta SSE."""
        holder = _make_holder()
        result = transform_stream_event(
            event_data={
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "thinking_delta", "thinking": "Let me analyze..."},
            },
            parent_tool_use_id=None,
            current_message_id_holder=holder,
        )

        assert result is not None
        assert "event: thinking_delta" in result
        data = json.loads(result.split("data: ")[1].split("\n")[0])
        assert data["delta"] == "Let me analyze..."
        assert data["messageId"] == "msg-123"
        assert data["blockIndex"] == 0

    def test_thinking_delta_with_parent_tool_use_id(self) -> None:
        """Thinking delta includes parentToolUseId when present."""
        holder = _make_holder()
        result = transform_stream_event(
            event_data={
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "thinking_delta", "thinking": "Thinking..."},
            },
            parent_tool_use_id="toolu_abc",
            current_message_id_holder=holder,
        )

        assert result is not None
        data = json.loads(result.split("data: ")[1].split("\n")[0])
        assert data["parentToolUseId"] == "toolu_abc"


class TestTransformStreamEventToolUse:
    """Test tool_use block streaming."""

    def test_tool_use_content_block_start(self) -> None:
        """StreamEvent with tool_use content_block_start emits both events."""
        holder = _make_holder()
        result = transform_stream_event(
            event_data={
                "type": "content_block_start",
                "index": 1,
                "content_block": {
                    "type": "tool_use",
                    "id": "toolu_123",
                    "name": "update_note_block",
                },
            },
            parent_tool_use_id=None,
            current_message_id_holder=holder,
        )

        assert result is not None
        # Should have both content_block_start and tool_use
        assert "event: content_block_start" in result
        assert "event: tool_use" in result

        # Parse the tool_use event
        events = result.strip().split("\n\n")
        tool_use_event = next(e for e in events if e.startswith("event: tool_use"))
        data = json.loads(tool_use_event.split("data: ")[1])
        assert data["toolCallId"] == "toolu_123"
        assert data["toolName"] == "update_note_block"
        assert data["toolInput"] == {}

    def test_input_json_delta(self) -> None:
        """StreamEvent with input_json_delta emits tool_input_delta SSE."""
        holder = _make_holder()
        result = transform_stream_event(
            event_data={
                "type": "content_block_delta",
                "index": 1,
                "delta": {
                    "type": "input_json_delta",
                    "partial_json": '{"note_id": "abc',
                },
            },
            parent_tool_use_id=None,
            current_message_id_holder=holder,
        )

        assert result is not None
        assert "event: tool_input_delta" in result
        data = json.loads(result.split("data: ")[1].split("\n")[0])
        assert data["delta"] == '{"note_id": "abc'
        assert data["blockIndex"] == 1


class TestTransformStreamEventText:
    """Test text block streaming."""

    def test_text_content_block_start(self) -> None:
        """StreamEvent with text content_block_start emits content_block_start."""
        holder = _make_holder()
        result = transform_stream_event(
            event_data={
                "type": "content_block_start",
                "index": 2,
                "content_block": {"type": "text", "text": ""},
            },
            parent_tool_use_id=None,
            current_message_id_holder=holder,
        )

        assert result is not None
        assert "event: content_block_start" in result
        data = json.loads(result.split("data: ")[1].split("\n")[0])
        assert data["contentType"] == "text"

    def test_text_delta(self) -> None:
        """StreamEvent with text_delta emits text_delta SSE."""
        holder = _make_holder()
        result = transform_stream_event(
            event_data={
                "type": "content_block_delta",
                "index": 2,
                "delta": {"type": "text_delta", "text": "Hello, I'll help you"},
            },
            parent_tool_use_id=None,
            current_message_id_holder=holder,
        )

        assert result is not None
        assert "event: text_delta" in result
        data = json.loads(result.split("data: ")[1].split("\n")[0])
        assert data["delta"] == "Hello, I'll help you"
        assert data["messageId"] == "msg-123"


class TestTransformStreamEventIgnored:
    """Test ignored event types."""

    @pytest.mark.parametrize(
        "event_type",
        [
            "content_block_stop",
            "message_start",
            "message_delta",
            "message_stop",
            "ping",
        ],
    )
    def test_ignored_event_types(self, event_type: str) -> None:
        """Ignored Anthropic event types return None."""
        holder = _make_holder()
        result = transform_stream_event(
            event_data={"type": event_type},
            parent_tool_use_id=None,
            current_message_id_holder=holder,
        )
        assert result is None

    def test_empty_thinking_delta_returns_none(self) -> None:
        """Thinking delta with empty text returns None."""
        holder = _make_holder()
        result = transform_stream_event(
            event_data={
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "thinking_delta", "thinking": ""},
            },
            parent_tool_use_id=None,
            current_message_id_holder=holder,
        )
        assert result is None

    def test_empty_text_delta_returns_none(self) -> None:
        """Text delta with empty text returns None."""
        holder = _make_holder()
        result = transform_stream_event(
            event_data={
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": ""},
            },
            parent_tool_use_id=None,
            current_message_id_holder=holder,
        )
        assert result is None


class TestStreamEventDedup:
    """Test AssistantMessage deduplication after StreamEvent forwarding."""

    def test_assistant_message_skips_streamed_blocks(self) -> None:
        """AssistantMessage blocks already sent via StreamEvent are skipped."""
        holder = _make_holder()

        # Simulate StreamEvents being sent for blocks 0 and 1
        holder["_stream_events_sent"] = True
        holder["_streamed_block_indices"] = {0, 1}

        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "Already streamed text"
        text_block.citations = []

        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.name = "update_note_block"
        tool_block.input = {}
        tool_block.id = "toolu_123"

        msg = MockAssistantMessage([text_block, tool_block])

        result = transform_sdk_message(msg, holder)

        # All blocks were streamed, so no events should be emitted
        assert result is None or result == ""

        # Tracking state should be cleaned up
        assert "_stream_events_sent" not in holder
        assert "_streamed_block_indices" not in holder

    def test_assistant_message_processes_new_blocks(self) -> None:
        """AssistantMessage processes blocks NOT sent via StreamEvent."""
        holder = _make_holder()

        # Only block 0 was streamed
        holder["_stream_events_sent"] = True
        holder["_streamed_block_indices"] = {0}

        streamed_block = MagicMock()
        streamed_block.type = "text"
        streamed_block.text = "Already streamed"
        streamed_block.citations = []

        new_block = MagicMock()
        new_block.type = "text"
        new_block.text = "New content not streamed"
        new_block.citations = []
        new_block.parent_tool_use_id = None

        msg = MockAssistantMessage([streamed_block, new_block])

        result = transform_sdk_message(msg, holder)

        assert result is not None
        assert "New content not streamed" in result
        assert "Already streamed" not in result

    def test_no_stream_events_processes_normally(self) -> None:
        """Without stream events, AssistantMessage processes all blocks."""
        holder = _make_holder()

        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "Normal response"
        text_block.citations = []
        text_block.parent_tool_use_id = None

        msg = MockAssistantMessage([text_block])

        result = transform_sdk_message(msg, holder)

        assert result is not None
        assert "Normal response" in result


class TestStreamEventViaTransformSdkMessage:
    """Test StreamEvent handling through the main transform_sdk_message entry point."""

    def test_stream_event_routed_correctly(self) -> None:
        """StreamEvent type is detected and routed to transform_stream_event."""
        holder = _make_holder()
        msg = MockStreamEvent(
            event={
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": "Hello"},
            },
        )

        result = transform_sdk_message(msg, holder)

        assert result is not None
        assert "event: text_delta" in result
        assert holder.get("_stream_events_sent") is True


class TestToolResultCompletion:
    """Test tool_result event emission alongside content_update."""

    def test_pending_apply_emits_tool_result(self) -> None:
        """ToolResultMessage with pending_apply emits both content_update and tool_result."""
        msg = MagicMock()
        msg.__class__.__name__ = "ToolResultMessage"
        msg.result = {
            "status": "pending_apply",
            "operation": "replace_block",
            "note_id": str(uuid4()),
            "block_id": "block-1",
            "markdown": "## Updated",
        }
        msg.tool_use_id = "toolu_456"
        msg.name = "update_note_block"
        msg.tool_name = "update_note_block"

        result = transform_tool_result(msg)

        assert result is not None
        assert "event: content_update" in result
        assert "event: tool_result" in result

        # Parse the tool_result event
        events = result.strip().split("\n\n")
        tool_result_events = [e for e in events if e.startswith("event: tool_result")]
        assert len(tool_result_events) == 1
        data = json.loads(tool_result_events[0].split("data: ")[1])
        assert data["toolCallId"] == "toolu_456"
        assert data["status"] == "completed"

    def test_non_pending_apply_no_double_tool_result(self) -> None:
        """Non-pending_apply tool results emit only one tool_result (existing behavior)."""
        msg = MagicMock()
        msg.__class__.__name__ = "ToolResultMessage"
        msg.result = {"output": "some result"}
        msg.tool_use_id = "toolu_789"
        msg.name = "Read"
        msg.tool_name = "Read"

        result = transform_tool_result(msg)

        assert result is not None
        assert "event: tool_result" in result
        # Should have exactly one tool_result event
        events = result.strip().split("\n\n")
        tool_result_events = [e for e in events if e.startswith("event: tool_result")]
        assert len(tool_result_events) == 1


class TestDedupStateResetOnInit:
    """Test that dedup state is cleared when a new session starts."""

    def test_init_clears_stale_dedup_state(self) -> None:
        """SystemMessage init resets dedup state from previous failed request."""
        holder = _make_holder()

        # Simulate stale state from a previous request that failed
        holder["_stream_events_sent"] = True
        holder["_streamed_block_indices"] = {0, 1, 2}

        # New session init should clear stale dedup state
        init_msg = MagicMock()
        init_msg.__class__.__name__ = "SystemMessage"
        init_msg.data = {
            "type": "system",
            "subtype": "init",
            "session_id": "new-session-id",
        }

        result = transform_sdk_message(init_msg, holder)

        assert result is not None
        assert "event: message_start" in result
        # Dedup state must be cleared
        assert "_stream_events_sent" not in holder
        assert "_streamed_block_indices" not in holder

    def test_init_reset_prevents_false_dedup(self) -> None:
        """After init reset, AssistantMessage blocks are NOT incorrectly skipped."""
        holder = _make_holder()

        # Stale state from previous request
        holder["_stream_events_sent"] = True
        holder["_streamed_block_indices"] = {0, 1}

        # New session init clears state
        init_msg = MagicMock()
        init_msg.__class__.__name__ = "SystemMessage"
        init_msg.data = {
            "type": "system",
            "subtype": "init",
            "session_id": "new-session",
        }
        transform_sdk_message(init_msg, holder)

        # New AssistantMessage arrives (no StreamEvents in this request)
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "Fresh response"
        text_block.citations = []
        text_block.parent_tool_use_id = None

        msg = MockAssistantMessage([text_block])
        result = transform_sdk_message(msg, holder)

        # Block should NOT be skipped
        assert result is not None
        assert "Fresh response" in result


class TestStreamEventTracking:
    """Test that stream event tracking state is managed correctly."""

    def test_stream_events_set_tracking_flag(self) -> None:
        """Processing a StreamEvent sets _stream_events_sent flag."""
        holder = _make_holder()
        transform_stream_event(
            event_data={
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "text"},
            },
            parent_tool_use_id=None,
            current_message_id_holder=holder,
        )
        assert holder["_stream_events_sent"] is True

    def test_stream_events_track_block_indices(self) -> None:
        """Processing StreamEvents tracks which block indices were sent."""
        holder = _make_holder()
        transform_stream_event(
            event_data={
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "text"},
            },
            parent_tool_use_id=None,
            current_message_id_holder=holder,
        )
        transform_stream_event(
            event_data={
                "type": "content_block_start",
                "index": 2,
                "content_block": {"type": "tool_use", "id": "t1", "name": "Read"},
            },
            parent_tool_use_id=None,
            current_message_id_holder=holder,
        )
        assert holder["_streamed_block_indices"] == {0, 2}

    def test_ignored_events_dont_set_tracking(self) -> None:
        """Ignored events (message_stop etc.) don't set tracking flags."""
        holder = _make_holder()
        transform_stream_event(
            event_data={"type": "message_stop"},
            parent_tool_use_id=None,
            current_message_id_holder=holder,
        )
        assert "_stream_events_sent" not in holder
