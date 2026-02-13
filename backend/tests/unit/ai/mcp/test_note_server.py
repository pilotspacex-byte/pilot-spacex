"""Unit tests for MCP note server tools (note_server.py).

Tests the in-process SDK MCP server tools that emit SSE events via
EventPublisher and return short text confirmations. Focuses on the
write_to_note tool and TOOL_NAMES constant.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import patch

import pytest

from pilot_space.ai.mcp.event_publisher import EventPublisher
from pilot_space.ai.mcp.note_server import (
    SERVER_NAME,
    TOOL_NAMES,
    create_note_tools_server,
)


def _parse_sse_event(raw: str) -> dict:
    """Parse an SSE event string into event type and JSON data."""
    lines = raw.strip().split("\n")
    event_type = ""
    data_str = ""
    for line in lines:
        if line.startswith("event: "):
            event_type = line[7:]
        elif line.startswith("data: "):
            data_str = line[6:]
    return {"event": event_type, "data": json.loads(data_str)}


def _capture_tools(publisher: EventPublisher, context_note_id: str | None = None):
    """Create note server and capture the SdkMcpTool objects.

    Patches create_sdk_mcp_server in the note_server module to intercept
    the tools list before it gets wrapped into the MCP server instance.
    """
    captured: dict[str, object] = {}

    import pilot_space.ai.mcp.note_server as ns_module

    original_create = ns_module.create_sdk_mcp_server

    def _intercept_create(*, name, version, tools):
        captured["tools"] = {t.name: t for t in tools}
        return original_create(name=name, version=version, tools=tools)

    with patch.object(ns_module, "create_sdk_mcp_server", side_effect=_intercept_create):
        create_note_tools_server(publisher, context_note_id=context_note_id)

    return captured["tools"]


def _drain_queue(queue: asyncio.Queue[str]) -> list[dict]:
    """Drain all SSE events from queue and parse them."""
    events = []
    while not queue.empty():
        raw = queue.get_nowait()
        events.append(_parse_sse_event(raw))
    return events


class TestWriteToNoteTool:
    """Tests for the write_to_note MCP tool."""

    @pytest.mark.asyncio
    async def test_emits_content_update_and_returns_confirmation(self) -> None:
        """write_to_note emits content_update SSE and returns short confirmation."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        publisher = EventPublisher(queue)
        tools = _capture_tools(publisher, context_note_id="note-abc")
        write_tool = tools["write_to_note"]

        result = await write_tool.handler({"note_id": "ignored", "markdown": "# Hello World"})

        # Tool result is a short confirmation (not the full payload)
        text = result["content"][0]["text"]
        assert "Content appended" in text

        # SSE events emitted to queue
        events = _drain_queue(queue)
        event_types = [e["event"] for e in events]
        assert "focus_block" in event_types
        assert "content_update" in event_types

        # Verify content_update payload
        cu = next(e for e in events if e["event"] == "content_update")
        assert cu["data"]["status"] in ("pending_apply", "approval_required")
        assert cu["data"]["operation"] == "append_blocks"
        assert cu["data"]["markdown"] == "# Hello World"
        assert cu["data"]["noteId"] == "note-abc"

    @pytest.mark.asyncio
    async def test_uses_context_note_id(self) -> None:
        """write_to_note uses context_note_id instead of model-provided note_id."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        publisher = EventPublisher(queue)
        tools = _capture_tools(publisher, context_note_id="real-note-uuid")
        write_tool = tools["write_to_note"]

        await write_tool.handler({"note_id": "model-hallucinated-id", "markdown": "Content"})

        events = _drain_queue(queue)
        cu = next(e for e in events if e["event"] == "content_update")
        assert cu["data"]["noteId"] == "real-note-uuid"

    @pytest.mark.asyncio
    async def test_rejects_empty_markdown(self) -> None:
        """write_to_note returns error text for empty markdown content."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        publisher = EventPublisher(queue)
        tools = _capture_tools(publisher, context_note_id="note-abc")
        write_tool = tools["write_to_note"]

        result = await write_tool.handler({"note_id": "note-abc", "markdown": ""})

        assert "Error" in result["content"][0]["text"]
        assert "empty" in result["content"][0]["text"].lower()
        assert queue.empty()

    @pytest.mark.asyncio
    async def test_rejects_whitespace_only_markdown(self) -> None:
        """write_to_note rejects whitespace-only markdown."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        publisher = EventPublisher(queue)
        tools = _capture_tools(publisher, context_note_id="note-abc")
        write_tool = tools["write_to_note"]

        result = await write_tool.handler({"note_id": "note-abc", "markdown": "   \n\t  "})

        assert "Error" in result["content"][0]["text"]
        assert queue.empty()

    @pytest.mark.asyncio
    async def test_payload_has_null_after_block_id(self) -> None:
        """write_to_note payload has null after_block_id for end-of-doc append."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        publisher = EventPublisher(queue)
        tools = _capture_tools(publisher, context_note_id="note-abc")
        write_tool = tools["write_to_note"]

        await write_tool.handler({"note_id": "note-abc", "markdown": "Some content"})

        events = _drain_queue(queue)
        cu = next(e for e in events if e["event"] == "content_update")
        assert cu["data"]["afterBlockId"] is None

    @pytest.mark.asyncio
    async def test_focus_block_emitted_with_scroll_to_end(self) -> None:
        """write_to_note emits focus_block with scrollToEnd=True."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        publisher = EventPublisher(queue)
        tools = _capture_tools(publisher, context_note_id="note-abc")
        write_tool = tools["write_to_note"]

        await write_tool.handler({"note_id": "note-abc", "markdown": "Content"})

        events = _drain_queue(queue)
        fb = next(e for e in events if e["event"] == "focus_block")
        assert fb["data"]["scrollToEnd"] is True
        assert fb["data"]["noteId"] == "note-abc"


class TestToolNamesConstant:
    """Tests for the TOOL_NAMES constant."""

    def test_includes_write_to_note(self) -> None:
        """TOOL_NAMES includes the write_to_note tool."""
        expected = f"mcp__{SERVER_NAME}__write_to_note"
        assert expected in TOOL_NAMES

    def test_has_nine_tools(self) -> None:
        """TOOL_NAMES has 9 entries (original - summarize_note + CRUD tools)."""
        assert len(TOOL_NAMES) == 9

    def test_all_tools_have_server_prefix(self) -> None:
        """All tool names follow the mcp__{SERVER_NAME}__<tool> pattern."""
        prefix = f"mcp__{SERVER_NAME}__"
        for name in TOOL_NAMES:
            assert name.startswith(prefix), f"{name} missing server prefix"
