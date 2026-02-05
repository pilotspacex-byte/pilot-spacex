"""StreamEvent transformer for real-time SSE forwarding.

Maps raw Anthropic API stream events (content_block_start, content_block_delta,
content_block_stop) from Claude Agent SDK StreamEvent objects to frontend SSE events
(thinking_delta, tool_use, tool_input_delta, text_delta, content_block_start).

Supports optional delta buffering (water pumping) to reduce SSE event count by
batching consecutive deltas of the same type.

Extracted from pilotspace_agent_helpers.py to keep both files under 700 lines.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pilot_space.ai.agents.sse_delta_buffer import DeltaBuffer

logger = logging.getLogger(__name__)

# Anthropic stream event types that should be forwarded
_FORWARDED_EVENT_TYPES = frozenset(
    {
        "content_block_start",
        "content_block_delta",
    }
)

# Anthropic stream event types to silently ignore
_IGNORED_EVENT_TYPES = frozenset(
    {
        "content_block_stop",
        "message_start",
        "message_delta",
        "message_stop",
        "ping",
    }
)


def transform_stream_event(
    event_data: dict[str, Any],
    parent_tool_use_id: str | None,
    current_message_id_holder: dict[str, Any],
    delta_buffer: DeltaBuffer | None = None,
) -> str | None:
    """Transform a raw Anthropic API stream event to frontend SSE event(s).

    Args:
        event_data: The raw Anthropic API event dict from StreamEvent.event
        parent_tool_use_id: Optional parent tool use ID for subagent correlation
        current_message_id_holder: Mutable dict for tracking state across messages
        delta_buffer: Optional buffer for batching delta events (water pumping)

    Returns:
        SSE-formatted string with one or more events, or None if ignored
    """
    event_type = event_data.get("type", "")

    if event_type not in _FORWARDED_EVENT_TYPES:
        if event_type not in _IGNORED_EVENT_TYPES:
            logger.debug("Unknown stream event type: %s", event_type)
        return None

    # Track that stream events were sent for dedup with AssistantMessage
    current_message_id_holder["_stream_events_sent"] = True

    if event_type == "content_block_start":
        return _handle_content_block_start(
            event_data,
            parent_tool_use_id,
            current_message_id_holder,
        )

    if event_type == "content_block_delta":
        return _handle_content_block_delta(
            event_data,
            parent_tool_use_id,
            current_message_id_holder,
            delta_buffer,
        )

    return None


def _handle_content_block_start(
    event_data: dict[str, Any],
    parent_tool_use_id: str | None,
    current_message_id_holder: dict[str, Any],
) -> str | None:
    """Handle content_block_start event."""
    content_block = event_data.get("content_block", {})
    block_type = content_block.get("type", "text")
    block_index = event_data.get("index", 0)

    # Track streamed block indices for dedup
    streamed_indices: set[int] = current_message_id_holder.setdefault(
        "_streamed_block_indices",
        set(),
    )
    streamed_indices.add(block_index)

    events: list[str] = []

    # Map block type to frontend content type
    if block_type == "thinking":
        content_type = "thinking"
    elif block_type == "tool_use":
        content_type = "tool_use"
    else:
        content_type = "text"

    block_start_data: dict[str, Any] = {
        "index": block_index,
        "contentType": content_type,
    }
    if parent_tool_use_id:
        block_start_data["parentToolUseId"] = str(parent_tool_use_id)

    events.append(
        f"event: content_block_start\ndata: {json.dumps(block_start_data)}\n\n",
    )

    # For tool_use blocks, also emit a tool_use event with initial data
    if block_type == "tool_use":
        tool_data: dict[str, Any] = {
            "toolCallId": content_block.get("id", ""),
            "toolName": content_block.get("name", ""),
            "toolInput": {},
        }
        events.append(
            f"event: tool_use\ndata: {json.dumps(tool_data)}\n\n",
        )

    return "".join(events) if events else None


def _handle_content_block_delta(
    event_data: dict[str, Any],
    parent_tool_use_id: str | None,
    current_message_id_holder: dict[str, Any],
    delta_buffer: DeltaBuffer | None = None,
) -> str | None:
    """Handle content_block_delta event.

    When delta_buffer is provided, deltas are accumulated and batched
    rather than emitted immediately (water pumping for event reduction).
    """
    delta = event_data.get("delta", {})
    delta_type = delta.get("type", "")
    message_id = current_message_id_holder.get("_current_message_id", "")
    block_index = event_data.get("index", 0)

    # Map delta type → (SSE event name, delta text field key)
    delta_map: dict[str, tuple[str, str]] = {
        "thinking_delta": ("thinking_delta", "thinking"),
        "input_json_delta": ("tool_input_delta", "partial_json"),
        "text_delta": ("text_delta", "text"),
    }

    mapping = delta_map.get(delta_type)
    if mapping is None:
        # signature_delta and unknown types are silently ignored
        if delta_type not in ("signature_delta", ""):
            logger.debug("Unknown content_block_delta type: %s", delta_type)
        return None

    sse_event_name, text_key = mapping
    text = delta.get(text_key, "")
    if not text:
        return None

    # If buffer provided, use water pumping (batch deltas)
    if delta_buffer:
        # Ensure buffer has current message context
        delta_buffer.set_message_context(message_id, parent_tool_use_id)

        if sse_event_name == "thinking_delta":
            return delta_buffer.add_thinking_delta(block_index, text)
        if sse_event_name == "text_delta":
            return delta_buffer.add_text_delta(block_index, text)
        if sse_event_name == "tool_input_delta":
            return delta_buffer.add_tool_input_delta(block_index, text)

    # Fallback: immediate emit (backward compatible, no buffer)
    data: dict[str, Any] = {
        "messageId": message_id,
        "delta": text,
        "blockIndex": block_index,
    }
    if parent_tool_use_id:
        data["parentToolUseId"] = str(parent_tool_use_id)
    return f"event: {sse_event_name}\ndata: {json.dumps(data)}\n\n"
