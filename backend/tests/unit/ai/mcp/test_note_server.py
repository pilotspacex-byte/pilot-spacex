"""Unit tests for MCP note server tools (note_server.py).

Tests the in-process SDK MCP server tools that push content_update
SSE events to a shared asyncio.Queue. Focuses on the write_to_note
tool and TOOL_NAMES constant.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import patch

import pytest

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


def _capture_tools(event_queue: asyncio.Queue[str], context_note_id: str | None = None):
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
        create_note_tools_server(event_queue, context_note_id=context_note_id)

    return captured["tools"]


class TestWriteToNoteTool:
    """Tests for the write_to_note MCP tool."""

    @pytest.mark.asyncio
    async def test_pushes_append_blocks_event(self) -> None:
        """write_to_note pushes a content_update event with append_blocks operation."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        tools = _capture_tools(queue, context_note_id="note-abc")
        write_tool = tools["write_to_note"]

        result = await write_tool.handler({"note_id": "ignored", "markdown": "# Hello World"})

        assert "Content written" in result["content"][0]["text"]

        raw_event = queue.get_nowait()
        parsed = _parse_sse_event(raw_event)

        assert parsed["event"] == "content_update"
        assert parsed["data"]["operation"] == "append_blocks"
        assert parsed["data"]["markdown"] == "# Hello World"

    @pytest.mark.asyncio
    async def test_uses_context_note_id(self) -> None:
        """write_to_note uses context_note_id instead of model-provided note_id."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        tools = _capture_tools(queue, context_note_id="real-note-uuid")
        write_tool = tools["write_to_note"]

        await write_tool.handler({"note_id": "model-hallucinated-id", "markdown": "Content"})

        raw_event = queue.get_nowait()
        parsed = _parse_sse_event(raw_event)

        assert parsed["data"]["noteId"] == "real-note-uuid"

    @pytest.mark.asyncio
    async def test_rejects_empty_markdown(self) -> None:
        """write_to_note returns error text for empty markdown content."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        tools = _capture_tools(queue, context_note_id="note-abc")
        write_tool = tools["write_to_note"]

        result = await write_tool.handler({"note_id": "note-abc", "markdown": ""})

        assert "Error" in result["content"][0]["text"]
        assert "empty" in result["content"][0]["text"].lower()
        assert queue.empty()

    @pytest.mark.asyncio
    async def test_rejects_whitespace_only_markdown(self) -> None:
        """write_to_note rejects whitespace-only markdown."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        tools = _capture_tools(queue, context_note_id="note-abc")
        write_tool = tools["write_to_note"]

        result = await write_tool.handler({"note_id": "note-abc", "markdown": "   \n\t  "})

        assert "Error" in result["content"][0]["text"]
        assert queue.empty()

    @pytest.mark.asyncio
    async def test_event_has_null_block_ids(self) -> None:
        """write_to_note event has null blockId and afterBlockId for end-of-doc append."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        tools = _capture_tools(queue, context_note_id="note-abc")
        write_tool = tools["write_to_note"]

        await write_tool.handler({"note_id": "note-abc", "markdown": "Some content"})

        raw_event = queue.get_nowait()
        parsed = _parse_sse_event(raw_event)

        assert parsed["data"]["blockId"] is None
        assert parsed["data"]["afterBlockId"] is None

    @pytest.mark.asyncio
    async def test_event_has_null_issue_data(self) -> None:
        """write_to_note event has null issueData and content fields."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        tools = _capture_tools(queue, context_note_id="note-abc")
        write_tool = tools["write_to_note"]

        await write_tool.handler({"note_id": "note-abc", "markdown": "Content"})

        raw_event = queue.get_nowait()
        parsed = _parse_sse_event(raw_event)

        assert parsed["data"]["issueData"] is None
        assert parsed["data"]["content"] is None


class TestToolNamesConstant:
    """Tests for the TOOL_NAMES constant."""

    def test_includes_write_to_note(self) -> None:
        """TOOL_NAMES includes the write_to_note tool."""
        expected = f"mcp__{SERVER_NAME}__write_to_note"
        assert expected in TOOL_NAMES

    def test_has_seven_tools(self) -> None:
        """TOOL_NAMES has 7 entries (6 original + write_to_note)."""
        assert len(TOOL_NAMES) == 7

    def test_all_tools_have_server_prefix(self) -> None:
        """All tool names follow the mcp__{SERVER_NAME}__<tool> pattern."""
        prefix = f"mcp__{SERVER_NAME}__"
        for name in TOOL_NAMES:
            assert name.startswith(prefix), f"{name} missing server prefix"
