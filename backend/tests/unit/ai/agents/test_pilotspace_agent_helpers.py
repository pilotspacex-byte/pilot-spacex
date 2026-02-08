"""Unit tests for transform_tool_result in pilotspace_agent_helpers.

Tests 1A: note tool_result includes output with operation summary.
Tests 1B: generic tool_result includes toolInput when provided.
"""

from __future__ import annotations

import json
from typing import Any

from pilot_space.ai.agents.pilotspace_agent_helpers import (
    transform_sdk_message,
    transform_tool_result,
)


class ToolResultMessage:
    """Fake SDK ToolResultMessage for testing (matches type().__name__ check)."""

    def __init__(self, result: Any, tool_use_id: str = "tu-1", name: str = "", **extra: Any):
        self.result = result
        self.tool_use_id = tool_use_id
        self.name = name
        for k, v in extra.items():
            setattr(self, k, v)


def _make_tool_result_msg(
    result: Any,
    tool_use_id: str = "tu-1",
    name: str = "",
    **extra: Any,
) -> ToolResultMessage:
    """Build a fake SDK ToolResultMessage-like object."""
    return ToolResultMessage(result=result, tool_use_id=tool_use_id, name=name, **extra)


def _parse_sse_events(raw: str) -> list[dict[str, Any]]:
    """Parse multi-event SSE string into list of {event, data} dicts."""
    events: list[dict[str, Any]] = []
    current_event = ""
    current_data = ""
    for line in raw.split("\n"):
        if line.startswith("event: "):
            current_event = line[len("event: ") :]
        elif line.startswith("data: "):
            current_data = line[len("data: ") :]
        elif line == "" and current_event:
            events.append({"event": current_event, "data": json.loads(current_data)})
            current_event = ""
            current_data = ""
    return events


# ---------------------------------------------------------------------------
# 1A: Note tool tool_result includes output with operation summary
# ---------------------------------------------------------------------------


class TestNoteToolResultOutput:
    """Verify note tool_result events include operation summary in output."""

    def test_replace_block_tool_result_has_output(self) -> None:
        """tool_result for replace_block includes operation, noteId, blockId."""
        msg = _make_tool_result_msg(
            result={
                "status": "pending_apply",
                "operation": "replace_block",
                "note_id": "note-123",
                "block_id": "block-456",
                "content": {"type": "paragraph", "content": [{"type": "text", "text": "new"}]},
            },
            tool_use_id="tu-replace",
        )
        raw = transform_tool_result(msg)
        assert raw is not None

        events = _parse_sse_events(raw)
        tool_result_events = [e for e in events if e["event"] == "tool_result"]
        assert len(tool_result_events) == 1

        data = tool_result_events[0]["data"]
        assert data["status"] == "completed"
        assert data["toolCallId"] == "tu-replace"
        assert data["output"]["operation"] == "replace_block"
        assert data["output"]["noteId"] == "note-123"
        assert data["output"]["blockId"] == "block-456"

    def test_append_blocks_tool_result_no_block_id(self) -> None:
        """tool_result for append_blocks omits blockId when not in result_data."""
        msg = _make_tool_result_msg(
            result={
                "status": "pending_apply",
                "operation": "append_blocks",
                "note_id": "note-789",
                "blocks": [{"type": "paragraph", "content": [{"type": "text", "text": "added"}]}],
            },
            tool_use_id="tu-append",
        )
        raw = transform_tool_result(msg)
        assert raw is not None

        events = _parse_sse_events(raw)
        tool_result_events = [e for e in events if e["event"] == "tool_result"]
        assert len(tool_result_events) == 1

        data = tool_result_events[0]["data"]
        assert data["output"]["operation"] == "append_blocks"
        assert data["output"]["noteId"] == "note-789"
        assert "blockId" not in data["output"]

    def test_content_update_event_still_emitted(self) -> None:
        """content_update event is still emitted alongside tool_result."""
        msg = _make_tool_result_msg(
            result={
                "status": "pending_apply",
                "operation": "replace_block",
                "note_id": "note-abc",
                "block_id": "block-def",
                "content": {"type": "paragraph", "content": [{"type": "text", "text": "x"}]},
            },
        )
        raw = transform_tool_result(msg)
        assert raw is not None

        events = _parse_sse_events(raw)
        event_types = [e["event"] for e in events]
        assert "content_update" in event_types
        assert "tool_result" in event_types


# ---------------------------------------------------------------------------
# 1B: Generic tool_result includes toolInput when provided
# ---------------------------------------------------------------------------


class TestGenericToolResultInput:
    """Verify generic (non-note) tool_result events pass through toolInput."""

    def test_tool_input_included_when_provided(self) -> None:
        """toolInput field appears in tool_result data when tool_input arg is set."""
        msg = _make_tool_result_msg(
            result={"summary": "File read successfully"},
            tool_use_id="tu-read",
            name="read_file",
        )
        raw = transform_tool_result(msg, tool_input={"path": "/src/main.py"})
        assert raw is not None

        events = _parse_sse_events(raw)
        assert len(events) == 1
        data = events[0]["data"]
        assert data["toolInput"] == {"path": "/src/main.py"}
        assert data["status"] == "completed"

    def test_tool_input_omitted_when_none(self) -> None:
        """toolInput field is absent when tool_input arg is None."""
        msg = _make_tool_result_msg(
            result={"summary": "Done"},
            tool_use_id="tu-other",
            name="some_tool",
        )
        raw = transform_tool_result(msg, tool_input=None)
        assert raw is not None

        events = _parse_sse_events(raw)
        data = events[0]["data"]
        assert "toolInput" not in data

    def test_error_tool_result_excludes_tool_input(self) -> None:
        """Failed tool results do not include toolInput (irrelevant for errors)."""
        msg = _make_tool_result_msg(
            result={"is_error": True, "error": "Permission denied"},
            tool_use_id="tu-err",
            name="write_file",
        )
        raw = transform_tool_result(msg, tool_input={"path": "/etc/secret"})
        assert raw is not None

        events = _parse_sse_events(raw)
        data = events[0]["data"]
        assert data["status"] == "failed"
        # toolInput is still included even on error (frontend may need it for display)
        assert data["toolInput"] == {"path": "/etc/secret"}


# ---------------------------------------------------------------------------
# 1B: transform_sdk_message passes tool_input from message attributes
# ---------------------------------------------------------------------------


class TestTransformSdkMessageToolInput:
    """Verify transform_sdk_message extracts and passes tool_input."""

    def test_passes_input_attr_as_tool_input(self) -> None:
        """Message with 'input' dict attribute passes it as tool_input."""
        msg = _make_tool_result_msg(
            result={"data": "ok"},
            tool_use_id="tu-sdk",
            name="read_file",
        )
        msg.input = {"path": "/README.md"}  # type: ignore[attr-defined]

        holder: dict[str, Any] = {"_current_message_id": "msg-1"}
        raw = transform_sdk_message(msg, holder)
        assert raw is not None

        events = _parse_sse_events(raw)
        data = events[0]["data"]
        assert data["toolInput"] == {"path": "/README.md"}

    def test_passes_tool_input_attr_as_fallback(self) -> None:
        """Message with 'tool_input' attribute uses it when 'input' is absent."""
        msg = _make_tool_result_msg(
            result={"data": "ok"},
            tool_use_id="tu-sdk2",
            name="search",
        )
        msg.tool_input = {"query": "find bugs"}  # type: ignore[attr-defined]

        holder: dict[str, Any] = {"_current_message_id": "msg-2"}
        raw = transform_sdk_message(msg, holder)
        assert raw is not None

        events = _parse_sse_events(raw)
        data = events[0]["data"]
        assert data["toolInput"] == {"query": "find bugs"}

    def test_no_tool_input_when_not_dict(self) -> None:
        """Non-dict input attribute is ignored (not passed as toolInput)."""
        msg = _make_tool_result_msg(
            result={"data": "ok"},
            tool_use_id="tu-sdk3",
            name="echo",
        )
        msg.input = "not-a-dict"  # type: ignore[attr-defined]

        holder: dict[str, Any] = {"_current_message_id": "msg-3"}
        raw = transform_sdk_message(msg, holder)
        assert raw is not None

        events = _parse_sse_events(raw)
        data = events[0]["data"]
        assert "toolInput" not in data
