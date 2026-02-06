"""Unit tests for enhanced note MCP tools (T007-T008).

Tests for 8 new note tools covering CRUD operations and content manipulation.
Tests follow SDK MCP server pattern - intercept tools from server creation
and call handler functions directly with args dict.

Reference: spec 010-enhanced-mcp-tools Phase 2
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import patch
from uuid import uuid4

import pytest

from pilot_space.ai.tools.mcp_server import ToolContext


def _capture_note_tools(
    event_queue: asyncio.Queue[str],
    tool_context: ToolContext | None = None,
):
    """Create note server and capture the SdkMcpTool objects."""
    from pilot_space.ai.mcp import note_server as ns_module

    captured: dict[str, object] = {}
    original_create = ns_module.create_sdk_mcp_server

    def _intercept_create(*, name, version, tools):
        captured["tools"] = {t.name: t for t in tools}
        return original_create(name=name, version=version, tools=tools)

    with patch.object(ns_module, "create_sdk_mcp_server", side_effect=_intercept_create):
        ns_module.create_note_tools_server(
            event_queue,
            context_note_id=None,
            tool_context=tool_context,
        )

    return captured["tools"]


def _capture_content_tools(
    event_queue: asyncio.Queue[str],
    tool_context: ToolContext | None = None,
):
    """Create note content server and capture the SdkMcpTool objects."""
    from pilot_space.ai.mcp import note_content_server as ncs_module

    captured: dict[str, object] = {}
    original_create = ncs_module.create_sdk_mcp_server

    def _intercept_create(*, name, version, tools):
        captured["tools"] = {t.name: t for t in tools}
        return original_create(name=name, version=version, tools=tools)

    with patch.object(ncs_module, "create_sdk_mcp_server", side_effect=_intercept_create):
        ncs_module.create_note_content_server(
            event_queue,
            tool_context=tool_context,
        )

    return captured["tools"]


class TestSearchNotes:
    """Test suite for search_notes tool (NT-001).

    Database-dependent search_notes functionality will be covered by integration tests.
    These unit tests verify tool registration and basic structure.
    """

    def test_search_notes_tool_registered(self) -> None:
        """Verify search_notes tool is registered in note server."""
        queue = asyncio.Queue()
        tools = _capture_note_tools(queue)
        assert "search_notes" in tools

    @pytest.mark.asyncio
    async def test_search_notes_without_context_returns_error(self) -> None:
        """Verify search_notes returns error when tool_context is missing."""
        queue = asyncio.Queue()
        tools = _capture_note_tools(queue, tool_context=None)
        search_tool = tools["search_notes"]

        result = await search_tool.handler({"query": "test"})

        assert "content" in result
        assert "Error" in result["content"][0]["text"]
        assert "tool_context not available" in result["content"][0]["text"]


class TestCreateNote:
    """Test suite for create_note tool (NT-002)."""

    @pytest.mark.asyncio
    async def test_create_note_with_content(self) -> None:
        """Verify create_note returns approval_required payload with content."""
        queue = asyncio.Queue()
        tools = _capture_note_tools(queue)
        create_tool = tools["create_note"]

        result = await create_tool.handler(
            {
                "title": "New Note",
                "content_markdown": "# Heading\n\nContent here.",
            }
        )

        assert result["status"] == "approval_required"
        assert result["operation"] == "create_note"
        assert result["payload"]["title"] == "New Note"
        assert "content_markdown" in result["payload"]

    @pytest.mark.asyncio
    async def test_create_note_without_content(self) -> None:
        """Verify create_note works without content_markdown."""
        queue = asyncio.Queue()
        tools = _capture_note_tools(queue)
        create_tool = tools["create_note"]

        result = await create_tool.handler({"title": "Empty Note"})

        assert result["status"] == "approval_required"
        assert result["payload"]["title"] == "Empty Note"
        assert "content_markdown" not in result["payload"]

    @pytest.mark.asyncio
    async def test_create_note_title_validation(self) -> None:
        """Verify create_note validates title length."""
        queue = asyncio.Queue()
        tools = _capture_note_tools(queue)
        create_tool = tools["create_note"]

        # Empty title
        result = await create_tool.handler({"title": ""})
        assert "content" in result
        assert "Error" in result["content"][0]["text"]

        # Title too long
        result = await create_tool.handler({"title": "x" * 300})
        assert "content" in result
        assert "Error" in result["content"][0]["text"]


class TestUpdateNote:
    """Test suite for update_note tool (NT-003)."""

    @pytest.mark.asyncio
    async def test_update_note_partial_update(self) -> None:
        """Verify update_note applies partial updates."""
        queue = asyncio.Queue()
        tools = _capture_note_tools(queue)
        update_tool = tools["update_note"]

        note_id = str(uuid4())
        result = await update_tool.handler(
            {
                "note_id": note_id,
                "title": "Updated Title",
            }
        )

        assert result["status"] == "approval_required"
        assert result["operation"] == "update_note"
        assert result["payload"]["note_id"] == note_id
        assert "title" in result["payload"]["changes"]
        assert "is_pinned" not in result["payload"]["changes"]

    @pytest.mark.asyncio
    async def test_update_note_pin_toggle(self) -> None:
        """Verify update_note can toggle pinned status."""
        queue = asyncio.Queue()
        tools = _capture_note_tools(queue)
        update_tool = tools["update_note"]

        result = await update_tool.handler(
            {
                "note_id": str(uuid4()),
                "is_pinned": True,
            }
        )

        assert result["payload"]["changes"]["is_pinned"] is True

    @pytest.mark.asyncio
    async def test_update_note_project_association(self) -> None:
        """Verify update_note can set project_id to null."""
        queue = asyncio.Queue()
        tools = _capture_note_tools(queue)
        update_tool = tools["update_note"]

        result = await update_tool.handler(
            {
                "note_id": str(uuid4()),
                "project_id": None,
            }
        )

        assert result["payload"]["changes"]["project_id"] is None


class TestSearchNoteContent:
    """Test suite for search_note_content tool (NT-004).

    Database-dependent search_note_content functionality will be covered by integration tests.
    These unit tests verify tool registration and basic structure.
    """

    def test_search_note_content_tool_registered(self) -> None:
        """Verify search_note_content tool is registered in content server."""
        queue = asyncio.Queue()
        tools = _capture_content_tools(queue)
        assert "search_note_content" in tools

    @pytest.mark.asyncio
    async def test_search_note_content_without_context_returns_error(self) -> None:
        """Verify search_note_content returns error when tool_context is missing."""
        queue = asyncio.Queue()
        tools = _capture_content_tools(queue, tool_context=None)
        search_tool = tools["search_note_content"]

        result = await search_tool.handler(
            {
                "note_id": str(uuid4()),
                "pattern": "test",
            }
        )

        assert "content" in result
        assert "Error" in result["content"][0]["text"]
        assert "tool_context not available" in result["content"][0]["text"]


class TestInsertBlock:
    """Test suite for insert_block tool (NT-005)."""

    @pytest.mark.asyncio
    async def test_insert_block_after_position(self) -> None:
        """Verify insert_block creates payload with after_block_id."""
        queue = asyncio.Queue()
        tools = _capture_content_tools(queue)
        insert_tool = tools["insert_block"]

        result = await insert_tool.handler(
            {
                "note_id": str(uuid4()),
                "content_markdown": "New content",
                "after_block_id": "block-123",
            }
        )

        data = json.loads(result["content"][0]["text"])
        assert data["status"] == "approval_required"
        assert data["operation"] == "insert_block"
        assert data["payload"]["after_block_id"] == "block-123"
        assert data["payload"]["before_block_id"] is None

    @pytest.mark.asyncio
    async def test_insert_block_before_position(self) -> None:
        """Verify insert_block creates payload with before_block_id."""
        queue = asyncio.Queue()
        tools = _capture_content_tools(queue)
        insert_tool = tools["insert_block"]

        result = await insert_tool.handler(
            {
                "note_id": str(uuid4()),
                "content_markdown": "New content",
                "before_block_id": "block-456",
            }
        )

        data = json.loads(result["content"][0]["text"])
        assert data["payload"]["before_block_id"] == "block-456"
        assert data["payload"]["after_block_id"] is None

    @pytest.mark.asyncio
    async def test_insert_block_append(self) -> None:
        """Verify insert_block appends when no position specified."""
        queue = asyncio.Queue()
        tools = _capture_content_tools(queue)
        insert_tool = tools["insert_block"]

        result = await insert_tool.handler(
            {
                "note_id": str(uuid4()),
                "content_markdown": "Appended content",
            }
        )

        data = json.loads(result["content"][0]["text"])
        assert data["payload"]["after_block_id"] is None
        assert data["payload"]["before_block_id"] is None


class TestRemoveBlock:
    """Test suite for remove_block tool (NT-006)."""

    @pytest.mark.asyncio
    async def test_remove_block_valid_block(self) -> None:
        """Verify remove_block returns approval_required payload."""
        queue = asyncio.Queue()
        tools = _capture_content_tools(queue)
        remove_tool = tools["remove_block"]

        result = await remove_tool.handler(
            {
                "note_id": str(uuid4()),
                "block_id": "block-789",
            }
        )

        data = json.loads(result["content"][0]["text"])
        assert data["status"] == "approval_required"
        assert data["operation"] == "remove_block"
        assert data["payload"]["block_id"] == "block-789"

    @pytest.mark.asyncio
    async def test_remove_block_invalid_block(self) -> None:
        """Verify remove_block validates block_id presence."""
        queue = asyncio.Queue()
        tools = _capture_content_tools(queue)
        remove_tool = tools["remove_block"]

        result = await remove_tool.handler(
            {
                "note_id": str(uuid4()),
                "block_id": "",
            }
        )

        assert "Error" in result["content"][0]["text"]


class TestRemoveContent:
    """Test suite for remove_content tool (NT-007)."""

    @pytest.mark.asyncio
    async def test_remove_content_pattern_match(self) -> None:
        """Verify remove_content creates payload with pattern."""
        queue = asyncio.Queue()
        tools = _capture_content_tools(queue)
        remove_tool = tools["remove_content"]

        result = await remove_tool.handler(
            {
                "note_id": str(uuid4()),
                "pattern": "deprecated",
            }
        )

        data = json.loads(result["content"][0]["text"])
        assert data["status"] == "approval_required"
        assert data["operation"] == "remove_content"
        assert data["payload"]["pattern"] == "deprecated"
        assert "preview" in data

    @pytest.mark.asyncio
    async def test_remove_content_scoped_blocks(self) -> None:
        """Verify remove_content can target specific blocks."""
        queue = asyncio.Queue()
        tools = _capture_content_tools(queue)
        remove_tool = tools["remove_content"]

        result = await remove_tool.handler(
            {
                "note_id": str(uuid4()),
                "pattern": "old",
                "block_ids": ["block-1", "block-2"],
            }
        )

        data = json.loads(result["content"][0]["text"])
        assert data["payload"]["block_ids"] == ["block-1", "block-2"]


class TestReplaceContent:
    """Test suite for replace_content tool (NT-008)."""

    @pytest.mark.asyncio
    async def test_replace_content_simple_replace(self) -> None:
        """Verify replace_content creates payload for simple find/replace."""
        queue = asyncio.Queue()
        tools = _capture_content_tools(queue)
        replace_tool = tools["replace_content"]

        result = await replace_tool.handler(
            {
                "note_id": str(uuid4()),
                "old_pattern": "foo",
                "new_content": "bar",
            }
        )

        data = json.loads(result["content"][0]["text"])
        assert data["status"] == "approval_required"
        assert data["operation"] == "replace_content"
        assert data["payload"]["old_pattern"] == "foo"
        assert data["payload"]["new_content"] == "bar"

    @pytest.mark.asyncio
    async def test_replace_content_regex_with_capture_groups(self) -> None:
        """Verify replace_content supports regex mode."""
        queue = asyncio.Queue()
        tools = _capture_content_tools(queue)
        replace_tool = tools["replace_content"]

        result = await replace_tool.handler(
            {
                "note_id": str(uuid4()),
                "old_pattern": r"(\w+)@example\.com",
                "new_content": r"$1@newdomain.com",
                "regex": True,
            }
        )

        data = json.loads(result["content"][0]["text"])
        assert data["payload"]["regex"] is True

    @pytest.mark.asyncio
    async def test_replace_content_replace_all_flag(self) -> None:
        """Verify replace_content respects replace_all flag."""
        queue = asyncio.Queue()
        tools = _capture_content_tools(queue)
        replace_tool = tools["replace_content"]

        result = await replace_tool.handler(
            {
                "note_id": str(uuid4()),
                "old_pattern": "old",
                "new_content": "new",
                "replace_all": False,
            }
        )

        data = json.loads(result["content"][0]["text"])
        assert data["payload"]["replace_all"] is False


class TestToolNamesConstant:
    """Test suite for TOOL_NAMES constants."""

    def test_note_server_has_9_tools(self) -> None:
        """Verify note_server TOOL_NAMES has 9 entries (summarize_note removed)."""
        from pilot_space.ai.mcp.note_server import TOOL_NAMES

        assert len(TOOL_NAMES) == 9

    def test_note_server_includes_new_tools(self) -> None:
        """Verify note_server TOOL_NAMES includes 3 new CRUD tools."""
        from pilot_space.ai.mcp.note_server import SERVER_NAME, TOOL_NAMES

        expected = [
            f"mcp__{SERVER_NAME}__search_notes",
            f"mcp__{SERVER_NAME}__create_note",
            f"mcp__{SERVER_NAME}__update_note",
        ]
        for name in expected:
            assert name in TOOL_NAMES

    def test_note_content_server_has_5_tools(self) -> None:
        """Verify note_content_server TOOL_NAMES has 5 entries."""
        from pilot_space.ai.mcp.note_content_server import TOOL_NAMES

        assert len(TOOL_NAMES) == 5

    def test_note_content_server_tool_names(self) -> None:
        """Verify note_content_server TOOL_NAMES includes all 5 content tools."""
        from pilot_space.ai.mcp.note_content_server import SERVER_NAME, TOOL_NAMES

        expected = [
            f"mcp__{SERVER_NAME}__search_note_content",
            f"mcp__{SERVER_NAME}__insert_block",
            f"mcp__{SERVER_NAME}__remove_block",
            f"mcp__{SERVER_NAME}__remove_content",
            f"mcp__{SERVER_NAME}__replace_content",
        ]
        for name in expected:
            assert name in TOOL_NAMES
