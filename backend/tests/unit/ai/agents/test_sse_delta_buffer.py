"""Unit tests for SSE Delta Buffer (water pumping).

Tests buffer accumulation, flush thresholds, and event formatting.
"""

from __future__ import annotations

import json
import time
from unittest.mock import patch

from pilot_space.ai.agents.sse_delta_buffer import (
    FLUSH_INTERVAL_SEC,
    MAX_BUFFER_SIZE,
    DeltaBuffer,
)


class TestDeltaBufferBasics:
    """Test basic buffer operations."""

    def test_buffer_initializes_empty(self) -> None:
        """Buffer starts with no content."""
        buffer = DeltaBuffer()
        assert not buffer._has_buffered_content()
        assert buffer.flush() is None

    def test_set_message_context(self) -> None:
        """Message context sets ID and parent tool use ID."""
        buffer = DeltaBuffer()
        buffer.set_message_context("msg-123", "tool-456")

        assert buffer._message_id == "msg-123"
        assert buffer._parent_tool_use_id == "tool-456"

    def test_reset_clears_all_state(self) -> None:
        """Reset clears buffers and metadata."""
        buffer = DeltaBuffer()
        buffer.set_message_context("msg-123", "tool-456")
        buffer.add_thinking_delta(0, "test")

        buffer.reset()

        assert buffer._message_id == ""
        assert buffer._parent_tool_use_id is None
        assert not buffer._has_buffered_content()
        assert buffer._buffer_size == 0


class TestThinkingDeltaBuffer:
    """Test thinking delta accumulation."""

    def test_accumulates_thinking_deltas(self) -> None:
        """Multiple thinking deltas accumulate in buffer."""
        buffer = DeltaBuffer()
        buffer.set_message_context("msg-1")

        # Add multiple deltas (under flush threshold)
        result1 = buffer.add_thinking_delta(0, "Hello ")
        result2 = buffer.add_thinking_delta(0, "world")

        # Should not flush yet (under time/size threshold)
        assert result1 is None
        assert result2 is None

        # Buffer has content
        assert buffer._has_buffered_content()
        assert buffer._thinking_buffer[0] == "Hello world"

    def test_flush_emits_thinking_delta_event(self) -> None:
        """Flush produces properly formatted SSE event."""
        buffer = DeltaBuffer()
        buffer.set_message_context("msg-1")
        buffer.add_thinking_delta(0, "Thinking content")

        events = buffer.flush()

        assert events is not None
        assert "event: thinking_delta\n" in events
        assert "Hello" not in events  # Not the test content
        assert "Thinking content" in events

        # Parse the event data
        lines = events.strip().split("\n")
        data_line = next(line for line in lines if line.startswith("data:"))
        data = json.loads(data_line[5:].strip())

        assert data["messageId"] == "msg-1"
        assert data["delta"] == "Thinking content"
        assert data["blockIndex"] == 0

    def test_preserves_block_indices(self) -> None:
        """Different block indices create separate events."""
        buffer = DeltaBuffer()
        buffer.set_message_context("msg-1")

        buffer.add_thinking_delta(0, "Block 0 content")
        buffer.add_thinking_delta(1, "Block 1 content")

        events = buffer.flush()

        assert events is not None
        # Should have two separate events
        assert events.count("event: thinking_delta\n") == 2
        assert '"blockIndex": 0' in events
        assert '"blockIndex": 1' in events


class TestTextDeltaBuffer:
    """Test text delta accumulation."""

    def test_accumulates_text_deltas(self) -> None:
        """Multiple text deltas accumulate in buffer."""
        buffer = DeltaBuffer()
        buffer.set_message_context("msg-1")

        buffer.add_text_delta(0, "First ")
        buffer.add_text_delta(0, "second")

        assert buffer._text_buffer[0] == "First second"

    def test_flush_emits_text_delta_event(self) -> None:
        """Flush produces properly formatted text_delta SSE event."""
        buffer = DeltaBuffer()
        buffer.set_message_context("msg-1")
        buffer.add_text_delta(0, "Text content")

        events = buffer.flush()

        assert events is not None
        assert "event: text_delta\n" in events

        lines = events.strip().split("\n")
        data_line = next(line for line in lines if line.startswith("data:"))
        data = json.loads(data_line[5:].strip())

        assert data["delta"] == "Text content"


class TestToolInputDeltaBuffer:
    """Test tool input delta accumulation."""

    def test_accumulates_tool_input_deltas(self) -> None:
        """Multiple tool input deltas accumulate in buffer."""
        buffer = DeltaBuffer()
        buffer.set_message_context("msg-1")

        buffer.add_tool_input_delta(0, '{"key": ')
        buffer.add_tool_input_delta(0, '"value"}')

        assert buffer._tool_input_buffer[0] == '{"key": "value"}'

    def test_flush_emits_tool_input_delta_event(self) -> None:
        """Flush produces properly formatted tool_input_delta SSE event."""
        buffer = DeltaBuffer()
        buffer.set_message_context("msg-1")
        buffer.add_tool_input_delta(0, '{"partial": true}')

        events = buffer.flush()

        assert events is not None
        assert "event: tool_input_delta\n" in events


class TestFlushThresholds:
    """Test time and size-based flush triggers."""

    def test_flush_on_size_threshold(self) -> None:
        """Buffer flushes when size exceeds MAX_BUFFER_SIZE."""
        buffer = DeltaBuffer()
        buffer.set_message_context("msg-1")

        # Create content larger than MAX_BUFFER_SIZE
        large_delta = "x" * (MAX_BUFFER_SIZE + 100)
        result = buffer.add_text_delta(0, large_delta)

        # Should trigger immediate flush
        assert result is not None
        assert "event: text_delta\n" in result
        assert large_delta in result

        # Buffer should be empty after flush
        assert not buffer._has_buffered_content()

    def test_should_flush_checks_time_threshold(self) -> None:
        """should_flush returns True when time threshold exceeded."""
        buffer = DeltaBuffer()
        buffer.set_message_context("msg-1")
        buffer.add_thinking_delta(0, "content")

        # Initially should not flush (just added)
        assert not buffer.should_flush()

        # Mock time to exceed threshold
        with patch.object(
            time,
            "monotonic",
            return_value=buffer._last_flush_time + FLUSH_INTERVAL_SEC + 0.01,
        ):
            assert buffer.should_flush()

    def test_empty_buffer_never_flushes(self) -> None:
        """Empty buffer returns None and should_flush is False."""
        buffer = DeltaBuffer()
        buffer.set_message_context("msg-1")

        assert buffer.flush() is None
        assert not buffer.should_flush()


class TestParentToolUseId:
    """Test parent tool use ID correlation."""

    def test_includes_parent_tool_use_id_when_set(self) -> None:
        """Events include parentToolUseId for subagent correlation."""
        buffer = DeltaBuffer()
        buffer.set_message_context("msg-1", "parent-tool-123")
        buffer.add_thinking_delta(0, "thinking")
        buffer.add_text_delta(1, "text")

        events = buffer.flush()

        assert events is not None
        # Both events should have parentToolUseId
        assert events.count('"parentToolUseId": "parent-tool-123"') == 2

    def test_omits_parent_tool_use_id_when_not_set(self) -> None:
        """Events omit parentToolUseId when not set."""
        buffer = DeltaBuffer()
        buffer.set_message_context("msg-1", None)
        buffer.add_thinking_delta(0, "thinking")

        events = buffer.flush()

        assert events is not None
        assert "parentToolUseId" not in events


class TestMixedDeltaTypes:
    """Test handling of multiple delta types in one flush."""

    def test_flush_emits_all_delta_types(self) -> None:
        """Single flush emits thinking, text, and tool_input events."""
        buffer = DeltaBuffer()
        buffer.set_message_context("msg-1")

        buffer.add_thinking_delta(0, "thinking")
        buffer.add_text_delta(1, "text")
        buffer.add_tool_input_delta(2, '{"tool": true}')

        events = buffer.flush()

        assert events is not None
        assert "event: thinking_delta\n" in events
        assert "event: text_delta\n" in events
        assert "event: tool_input_delta\n" in events

    def test_events_ordered_by_type_then_block_index(self) -> None:
        """Events are ordered: thinking → text → tool_input, then by block index."""
        buffer = DeltaBuffer()
        buffer.set_message_context("msg-1")

        # Add in random order
        buffer.add_text_delta(1, "text1")
        buffer.add_thinking_delta(2, "thinking2")
        buffer.add_tool_input_delta(0, "tool0")
        buffer.add_thinking_delta(0, "thinking0")
        buffer.add_text_delta(0, "text0")

        events = buffer.flush()

        assert events is not None
        # Check order: thinking events first
        thinking_pos = events.index("event: thinking_delta\n")
        text_pos = events.index("event: text_delta\n")
        tool_pos = events.index("event: tool_input_delta\n")

        assert thinking_pos < text_pos < tool_pos


class TestEmptyDeltaHandling:
    """Test handling of empty or None deltas."""

    def test_ignores_empty_thinking_delta(self) -> None:
        """Empty string deltas are ignored."""
        buffer = DeltaBuffer()
        buffer.set_message_context("msg-1")

        result = buffer.add_thinking_delta(0, "")

        assert result is None
        assert not buffer._has_buffered_content()

    def test_ignores_empty_text_delta(self) -> None:
        """Empty text deltas are ignored."""
        buffer = DeltaBuffer()
        buffer.set_message_context("msg-1")

        result = buffer.add_text_delta(0, "")

        assert result is None
        assert not buffer._has_buffered_content()

    def test_ignores_empty_tool_input_delta(self) -> None:
        """Empty tool input deltas are ignored."""
        buffer = DeltaBuffer()
        buffer.set_message_context("msg-1")

        result = buffer.add_tool_input_delta(0, "")

        assert result is None
        assert not buffer._has_buffered_content()
