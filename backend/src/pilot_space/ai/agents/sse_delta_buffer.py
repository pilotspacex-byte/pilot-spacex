"""SSE Delta Buffer - Water pumping for streaming events.

Batches consecutive deltas of the same type to reduce SSE event count.
Flushes on time threshold, type change, or explicit flush call.

Design:
- FLUSH_INTERVAL_MS (50ms) balances responsiveness with event reduction
- MAX_BUFFER_SIZE (4KB) prevents memory growth from long deltas
- Per-blockIndex accumulation preserves interleaved content ordering
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

# Flush interval in seconds (50ms for responsive feel)
FLUSH_INTERVAL_MS = 50
FLUSH_INTERVAL_SEC = FLUSH_INTERVAL_MS / 1000.0

# Maximum buffer size before forced flush (4KB)
MAX_BUFFER_SIZE = 4096


@dataclass
class DeltaBuffer:
    """Buffers deltas by type with time-window flush.

    Accumulates thinking_delta, text_delta, and tool_input_delta events,
    flushing them as batched SSE events when thresholds are reached.
    """

    # Accumulated deltas per event type (blockIndex → content)
    _thinking_buffer: dict[int, str] = field(default_factory=dict)
    _text_buffer: dict[int, str] = field(default_factory=dict)
    _tool_input_buffer: dict[int, str] = field(default_factory=dict)

    # Metadata for events
    _message_id: str = ""
    _parent_tool_use_id: str | None = None

    # Timing
    _last_flush_time: float = field(default_factory=time.monotonic)
    _buffer_size: int = 0

    def set_message_context(
        self,
        message_id: str,
        parent_tool_use_id: str | None = None,
    ) -> None:
        """Set context for current message.

        Args:
            message_id: Current message ID for SSE event metadata
            parent_tool_use_id: Optional parent tool use ID for subagent correlation
        """
        self._message_id = message_id
        self._parent_tool_use_id = parent_tool_use_id

    def add_thinking_delta(self, block_index: int, delta: str) -> str | None:
        """Buffer thinking delta, return flush if threshold reached.

        Args:
            block_index: Content block index from SDK stream event
            delta: Text content to buffer

        Returns:
            SSE events string if threshold reached, None otherwise
        """
        if not delta:
            return None
        self._thinking_buffer[block_index] = self._thinking_buffer.get(block_index, "") + delta
        self._buffer_size += len(delta)
        return self._check_flush()

    def add_text_delta(self, block_index: int, delta: str) -> str | None:
        """Buffer text delta, return flush if threshold reached.

        Args:
            block_index: Content block index from SDK stream event
            delta: Text content to buffer

        Returns:
            SSE events string if threshold reached, None otherwise
        """
        if not delta:
            return None
        self._text_buffer[block_index] = self._text_buffer.get(block_index, "") + delta
        self._buffer_size += len(delta)
        return self._check_flush()

    def add_tool_input_delta(self, block_index: int, delta: str) -> str | None:
        """Buffer tool input delta, return flush if threshold reached.

        Args:
            block_index: Content block index from SDK stream event
            delta: Partial JSON text to buffer

        Returns:
            SSE events string if threshold reached, None otherwise
        """
        if not delta:
            return None
        self._tool_input_buffer[block_index] = self._tool_input_buffer.get(block_index, "") + delta
        self._buffer_size += len(delta)
        return self._check_flush()

    def _check_flush(self) -> str | None:
        """Check if flush threshold reached, return events if so."""
        now = time.monotonic()
        elapsed = now - self._last_flush_time

        if elapsed >= FLUSH_INTERVAL_SEC or self._buffer_size >= MAX_BUFFER_SIZE:
            return self.flush()
        return None

    def should_flush(self) -> bool:
        """Check if flush is needed (time or size threshold)."""
        now = time.monotonic()
        elapsed = now - self._last_flush_time
        return (
            elapsed >= FLUSH_INTERVAL_SEC or self._buffer_size >= MAX_BUFFER_SIZE
        ) and self._has_buffered_content()

    def flush(self) -> str | None:
        """Flush all buffered deltas to SSE events.

        Returns:
            Concatenated SSE event strings, or None if buffer empty
        """
        if not self._has_buffered_content():
            return None

        events: list[str] = []

        # Flush thinking deltas (one event per block index)
        for block_index in sorted(self._thinking_buffer.keys()):
            content = self._thinking_buffer[block_index]
            if content:
                data: dict[str, object] = {
                    "messageId": self._message_id,
                    "delta": content,
                    "blockIndex": block_index,
                }
                if self._parent_tool_use_id:
                    data["parentToolUseId"] = self._parent_tool_use_id
                events.append(f"event: thinking_delta\ndata: {json.dumps(data)}\n\n")

        # Flush text deltas
        for block_index in sorted(self._text_buffer.keys()):
            content = self._text_buffer[block_index]
            if content:
                data = {
                    "messageId": self._message_id,
                    "delta": content,
                    "blockIndex": block_index,
                }
                if self._parent_tool_use_id:
                    data["parentToolUseId"] = self._parent_tool_use_id
                events.append(f"event: text_delta\ndata: {json.dumps(data)}\n\n")

        # Flush tool input deltas
        for block_index in sorted(self._tool_input_buffer.keys()):
            content = self._tool_input_buffer[block_index]
            if content:
                data = {
                    "messageId": self._message_id,
                    "delta": content,
                    "blockIndex": block_index,
                }
                if self._parent_tool_use_id:
                    data["parentToolUseId"] = self._parent_tool_use_id
                events.append(f"event: tool_input_delta\ndata: {json.dumps(data)}\n\n")

        # Reset buffers
        self._thinking_buffer.clear()
        self._text_buffer.clear()
        self._tool_input_buffer.clear()
        self._buffer_size = 0
        self._last_flush_time = time.monotonic()

        return "".join(events) if events else None

    def _has_buffered_content(self) -> bool:
        """Check if any buffer has content."""
        return bool(self._thinking_buffer or self._text_buffer or self._tool_input_buffer)

    def reset(self) -> None:
        """Reset all buffers for new message."""
        self._thinking_buffer.clear()
        self._text_buffer.clear()
        self._tool_input_buffer.clear()
        self._message_id = ""
        self._parent_tool_use_id = None
        self._buffer_size = 0
        self._last_flush_time = time.monotonic()
