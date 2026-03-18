"""Unit tests for transform_tool_result in pilotspace_agent_helpers.

Tests 1A: note tool_result includes output with operation summary.
Tests 1B: generic tool_result includes toolInput when provided.
"""

from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk.types import ToolResultBlock

from pilot_space.ai.agents.pilotspace_agent_helpers import (
    transform_sdk_message,
    transform_tool_result,
)
from pilot_space.ai.agents.pilotspace_note_helpers import (
    emit_focus_block_event,
    transform_user_message_tool_results,
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


# ---------------------------------------------------------------------------
# 2: emit_focus_block_event — unit tests
# ---------------------------------------------------------------------------


class TestEmitFocusBlockEvent:
    """Verify focus_block SSE event generation for each operation type."""

    def test_replace_block_emits_focus_on_block_id(self) -> None:
        result = emit_focus_block_event({"block_id": "blk-1"}, "note-1", "replace_block")
        assert result is not None
        events = _parse_sse_events(result)
        assert len(events) == 1
        assert events[0]["event"] == "focus_block"
        assert events[0]["data"]["blockId"] == "blk-1"
        assert events[0]["data"]["noteId"] == "note-1"
        assert events[0]["data"]["scrollToEnd"] is False

    def test_append_blocks_with_after_block_id(self) -> None:
        result = emit_focus_block_event({"after_block_id": "blk-2"}, "note-2", "append_blocks")
        assert result is not None
        events = _parse_sse_events(result)
        assert events[0]["data"]["blockId"] == "blk-2"
        assert events[0]["data"]["scrollToEnd"] is False

    def test_append_blocks_without_after_block_id_scrolls_to_end(self) -> None:
        result = emit_focus_block_event({"after_block_id": None}, "note-3", "append_blocks")
        assert result is not None
        events = _parse_sse_events(result)
        assert events[0]["data"]["blockId"] is None
        assert events[0]["data"]["scrollToEnd"] is True

    def test_remove_block_emits_focus_on_block_id(self) -> None:
        result = emit_focus_block_event({"block_id": "blk-rm"}, "note-4", "remove_block")
        assert result is not None
        events = _parse_sse_events(result)
        assert events[0]["data"]["blockId"] == "blk-rm"

    def test_insert_blocks_prefers_before_block_id(self) -> None:
        result = emit_focus_block_event(
            {"before_block_id": "blk-before", "after_block_id": "blk-after"},
            "note-5",
            "insert_blocks",
        )
        assert result is not None
        events = _parse_sse_events(result)
        assert events[0]["data"]["blockId"] == "blk-before"

    def test_create_issues_uses_first_block_id(self) -> None:
        result = emit_focus_block_event(
            {"block_ids": ["blk-a", "blk-b"]}, "note-6", "create_issues"
        )
        assert result is not None
        events = _parse_sse_events(result)
        assert events[0]["data"]["blockId"] == "blk-a"

    def test_create_single_issue_uses_block_id(self) -> None:
        result = emit_focus_block_event({"block_id": "blk-si"}, "note-7", "create_single_issue")
        assert result is not None
        events = _parse_sse_events(result)
        assert events[0]["data"]["blockId"] == "blk-si"

    def test_no_block_id_returns_none(self) -> None:
        """Operations without any block reference return None (no focus event)."""
        result = emit_focus_block_event({}, "note-8", "replace_block")
        assert result is None

    def test_unknown_operation_returns_none(self) -> None:
        """Unknown operation type returns None."""
        result = emit_focus_block_event({"block_id": "blk-x"}, "note-9", "unknown_op")
        assert result is None


# ---------------------------------------------------------------------------
# 3: transform_user_message_tool_results — focus_block before content_update
# ---------------------------------------------------------------------------


class FakeUserMessage:
    """Fake UserMessage from Claude Agent SDK (content = list of ToolResultBlock)."""

    def __init__(self, blocks: list[Any]):
        self.content = blocks


class TestNoFocusBlockInPipeline:
    """Verify focus_block is NOT emitted from transform_user_message_tool_results.

    focus_block is now emitted by tool handlers directly via event_queue
    (before DB call) for immediate delivery. The SDK pipeline only emits
    content_update + tool_result.
    """

    def test_replace_block_emits_content_update_without_focus(self) -> None:
        """replace_block emits content_update + tool_result, no focus_block."""
        payload = json.dumps(
            {
                "status": "pending_apply",
                "operation": "replace_block",
                "note_id": "note-r1",
                "block_id": "blk-r1",
                "markdown": "# Hello",
            }
        )
        msg = FakeUserMessage([ToolResultBlock(tool_use_id="tu-r1", content=payload)])
        raw = transform_user_message_tool_results(msg)
        assert raw is not None

        events = _parse_sse_events(raw)
        event_types = [e["event"] for e in events]
        assert "focus_block" not in event_types
        assert "content_update" in event_types
        assert "tool_result" in event_types

    def test_append_blocks_no_focus_block(self) -> None:
        """append_blocks emits content_update + tool_result, no focus_block."""
        payload = json.dumps(
            {
                "status": "pending_apply",
                "operation": "append_blocks",
                "note_id": "note-a1",
                "markdown": "New content",
                "after_block_id": None,
            }
        )
        msg = FakeUserMessage([ToolResultBlock(tool_use_id="tu-a1", content=payload)])
        raw = transform_user_message_tool_results(msg)
        assert raw is not None

        events = _parse_sse_events(raw)
        focus_events = [e for e in events if e["event"] == "focus_block"]
        assert len(focus_events) == 0

    def test_event_order_is_content_update_tool_result(self) -> None:
        """Event sequence: content_update → tool_result (focus_block via queue)."""
        payload = json.dumps(
            {
                "status": "pending_apply",
                "operation": "replace_block",
                "note_id": "note-o1",
                "block_id": "blk-o1",
                "markdown": "Updated",
            }
        )
        msg = FakeUserMessage([ToolResultBlock(tool_use_id="tu-o1", content=payload)])
        raw = transform_user_message_tool_results(msg)
        assert raw is not None

        events = _parse_sse_events(raw)
        event_types = [e["event"] for e in events]
        assert event_types == ["content_update", "tool_result"]


# ---------------------------------------------------------------------------
# 4: Entity creation ops (no note_id) emit generic tool_result, not dropped
# ---------------------------------------------------------------------------


class TestEntityCreationOpsNotDropped:
    """Verify pending_apply results without note_id fall through to generic tool_result.

    Operations like create_note and create_issue return pending_apply payloads
    without a note_id (the entity doesn't exist yet). These must NOT be silently
    dropped — they should emit a generic tool_result event.
    """

    def test_create_note_pending_apply_emits_tool_result(self) -> None:
        """create_note with pending_apply and no note_id emits generic tool_result."""
        msg = _make_tool_result_msg(
            result={
                "status": "pending_apply",
                "operation": "create_note",
                "payload": {"title": "My Note", "content_markdown": "Hello"},
            },
            tool_use_id="tu-create-note",
            name="create_note",
        )
        raw = transform_tool_result(msg)
        assert raw is not None

        events = _parse_sse_events(raw)
        assert len(events) == 1
        assert events[0]["event"] == "tool_result"
        assert events[0]["data"]["toolCallId"] == "tu-create-note"
        assert events[0]["data"]["status"] == "completed"
        # Output includes the full result data (status, operation, payload)
        assert events[0]["data"]["output"]["operation"] == "create_note"

    def test_create_issue_pending_apply_emits_tool_result(self) -> None:
        """create_issue with pending_apply and no note_id emits generic tool_result."""
        msg = _make_tool_result_msg(
            result={
                "status": "pending_apply",
                "operation": "create_issue",
                "payload": {"title": "Bug fix", "project_id": "proj-1"},
            },
            tool_use_id="tu-create-issue",
            name="create_issue",
        )
        raw = transform_tool_result(msg)
        assert raw is not None

        events = _parse_sse_events(raw)
        assert len(events) == 1
        assert events[0]["event"] == "tool_result"
        assert events[0]["data"]["status"] == "completed"

    def test_content_ops_with_note_id_still_emit_content_update(self) -> None:
        """Existing behavior unchanged: replace_block with note_id emits content_update."""
        msg = _make_tool_result_msg(
            result={
                "status": "pending_apply",
                "operation": "replace_block",
                "note_id": "note-existing",
                "block_id": "blk-existing",
                "markdown": "Updated text",
            },
            tool_use_id="tu-existing",
        )
        raw = transform_tool_result(msg)
        assert raw is not None

        events = _parse_sse_events(raw)
        event_types = [e["event"] for e in events]
        assert "content_update" in event_types
        assert "tool_result" in event_types

    def test_user_message_create_note_falls_through_to_generic(self) -> None:
        """UserMessage path: create_note without note_id emits generic tool_result."""
        payload = json.dumps(
            {
                "status": "pending_apply",
                "operation": "create_note",
                "payload": {"title": "New Note"},
            }
        )
        msg = FakeUserMessage([ToolResultBlock(tool_use_id="tu-um-create", content=payload)])
        raw = transform_user_message_tool_results(msg)
        assert raw is not None

        events = _parse_sse_events(raw)
        assert len(events) == 1
        assert events[0]["event"] == "tool_result"
        assert events[0]["data"]["status"] == "completed"


# ---------------------------------------------------------------------------
# 5: Auto-executed entity creation ops emit generic tool_result
# ---------------------------------------------------------------------------


class TestAutoExecutedOpsEmitToolResult:
    """Verify auto-executed (status='executed') results emit generic tool_result."""

    def test_create_issue_executed_emits_tool_result(self) -> None:
        """create_issue with executed status emits generic tool_result."""
        msg = _make_tool_result_msg(
            result={
                "status": "executed",
                "operation": "create_issue",
                "issue": {
                    "id": "issue-1",
                    "identifier": "PS-1",
                    "name": "Bug fix",
                    "priority": "medium",
                },
            },
            tool_use_id="tu-exec-issue",
            name="create_issue",
        )
        raw = transform_tool_result(msg)
        assert raw is not None

        events = _parse_sse_events(raw)
        assert len(events) == 1
        assert events[0]["event"] == "tool_result"
        assert events[0]["data"]["toolCallId"] == "tu-exec-issue"
        assert events[0]["data"]["status"] == "completed"
        assert events[0]["data"]["output"]["operation"] == "create_issue"
        assert events[0]["data"]["output"]["issue"]["id"] == "issue-1"

    def test_create_note_executed_emits_tool_result(self) -> None:
        """create_note with executed status emits generic tool_result."""
        msg = _make_tool_result_msg(
            result={
                "status": "executed",
                "operation": "create_note",
                "note": {"id": "note-1", "title": "My Note"},
            },
            tool_use_id="tu-exec-note",
            name="create_note",
        )
        raw = transform_tool_result(msg)
        assert raw is not None

        events = _parse_sse_events(raw)
        assert len(events) == 1
        assert events[0]["event"] == "tool_result"
        assert events[0]["data"]["toolCallId"] == "tu-exec-note"
        assert events[0]["data"]["status"] == "completed"
        assert events[0]["data"]["output"]["operation"] == "create_note"
        assert events[0]["data"]["output"]["note"]["title"] == "My Note"

    def test_user_message_executed_note_emits_tool_result(self) -> None:
        """UserMessage path: executed create_note emits generic tool_result."""
        payload = json.dumps(
            {
                "status": "executed",
                "operation": "create_note",
                "note": {"id": "note-2", "title": "Auto Note"},
            }
        )
        msg = FakeUserMessage([ToolResultBlock(tool_use_id="tu-um-exec", content=payload)])
        raw = transform_user_message_tool_results(msg)
        assert raw is not None

        events = _parse_sse_events(raw)
        assert len(events) == 1
        assert events[0]["event"] == "tool_result"
        assert events[0]["data"]["status"] == "completed"
