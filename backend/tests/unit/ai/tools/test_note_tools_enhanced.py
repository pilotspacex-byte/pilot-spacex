"""Unit tests for enhanced note MCP tools (T007-T008).

Tests for 8 new note tools covering CRUD operations and content manipulation.
Tests follow SDK MCP server pattern - intercept tools from server creation
and call handler functions directly with args dict.

Mutation tools (insert_block, remove_block, remove_content, replace_content)
emit SSE events via EventPublisher and return short text confirmations.
Metadata tools (create_note, update_note) still return JSON payloads.

Reference: spec 010-enhanced-mcp-tools Phase 2
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Generator
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from pilot_space.ai.mcp.event_publisher import EventPublisher
from pilot_space.ai.tools.mcp_server import ToolContext


@pytest.fixture
def mock_tool_context() -> ToolContext:
    """Mock ToolContext for content mutation tests requiring workspace verification."""
    return ToolContext(
        db_session=MagicMock(),
        workspace_id=str(uuid4()),
        user_id=str(uuid4()),
    )


@contextmanager
def _mock_note_repo(workspace_id: str) -> Generator[None, None, None]:
    """Mock NoteRepository for workspace verification in note content tools."""
    mock_note = MagicMock()
    mock_note.workspace_id = UUID(workspace_id)
    mock_repo = AsyncMock()
    mock_repo.get_by_id.return_value = mock_note
    with patch(
        "pilot_space.infrastructure.database.repositories.note_repository.NoteRepository",
        return_value=mock_repo,
    ):
        yield


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
            EventPublisher(event_queue),
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
            EventPublisher(event_queue),
            tool_context=tool_context,
        )

    return captured["tools"]


def _parse_sse(raw: str) -> dict:
    """Parse an SSE event string into {event, data} dict."""
    lines = raw.strip().split("\n")
    event_type = ""
    data_str = ""
    for line in lines:
        if line.startswith("event: "):
            event_type = line[7:]
        elif line.startswith("data: "):
            data_str = line[6:]
    return {"event": event_type, "data": json.loads(data_str)}


def _drain_content_update(queue: asyncio.Queue[str]) -> dict:
    """Drain queue and return the content_update event data."""
    while not queue.empty():
        raw = queue.get_nowait()
        parsed = _parse_sse(raw)
        if parsed["event"] == "content_update":
            return parsed["data"]
    msg = "No content_update event found in queue"
    raise AssertionError(msg)


class TestSearchNotes:
    """Test suite for search_notes tool (NT-001).

    search_notes is now in note_query_server (CQRS-lite split).
    These unit tests verify tool registration in the new location.
    """

    def test_search_notes_tool_registered_in_query_server(self) -> None:
        """Verify search_notes tool is registered in note_query_server."""
        from unittest.mock import patch

        import pilot_space.ai.mcp.note_query_server as nqs_module

        captured: dict[str, object] = {}
        original_create = nqs_module.create_sdk_mcp_server

        def _intercept(*, name, version, tools):
            captured["tools"] = {t.name: t for t in tools}
            return original_create(name=name, version=version, tools=tools)

        with patch.object(nqs_module, "create_sdk_mcp_server", side_effect=_intercept):
            nqs_module.create_note_query_server(tool_context=None)

        assert "search_notes" in captured["tools"]

    @pytest.mark.asyncio
    async def test_search_notes_without_context_returns_error(self) -> None:
        """Verify search_notes returns error when tool_context is missing."""
        from unittest.mock import patch

        import pilot_space.ai.mcp.note_query_server as nqs_module

        captured: dict[str, object] = {}
        original_create = nqs_module.create_sdk_mcp_server

        def _intercept(*, name, version, tools):
            captured["tools"] = {t.name: t for t in tools}
            return original_create(name=name, version=version, tools=tools)

        with patch.object(nqs_module, "create_sdk_mcp_server", side_effect=_intercept):
            nqs_module.create_note_query_server(tool_context=None)

        search_tool = captured["tools"]["search_notes"]
        result = await search_tool.handler({"query": "test"})

        assert "content" in result
        assert "Error" in result["content"][0]["text"]
        assert "tool_context not available" in result["content"][0]["text"]


class TestCreateNote:
    """Test suite for create_note tool (NT-002).

    create_note is a metadata-only tool that still returns JSON payload
    in the tool result (not emitted via SSE).
    """

    @pytest.mark.asyncio
    async def test_create_note_with_content(self) -> None:
        """Verify create_note returns operation payload with content."""
        queue = asyncio.Queue()
        tools = _capture_note_tools(queue)
        create_tool = tools["create_note"]

        result = await create_tool.handler(
            {
                "title": "New Note",
                "content_markdown": "# Heading\n\nContent here.",
            }
        )

        data = json.loads(result["content"][0]["text"])
        assert data["operation"] == "create_note"
        assert data["payload"]["title"] == "New Note"
        assert "content_markdown" in data["payload"]

    @pytest.mark.asyncio
    async def test_create_note_without_content(self) -> None:
        """Verify create_note works without content_markdown."""
        queue = asyncio.Queue()
        tools = _capture_note_tools(queue)
        create_tool = tools["create_note"]

        result = await create_tool.handler({"title": "Empty Note"})

        data = json.loads(result["content"][0]["text"])
        assert data["payload"]["title"] == "Empty Note"
        assert "content_markdown" not in data["payload"]

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
    """Test suite for update_note tool (NT-003).

    update_note is a metadata-only tool that still returns JSON payload
    in the tool result (not emitted via SSE).
    """

    @pytest.mark.asyncio
    async def test_update_note_partial_update(self, mock_tool_context: ToolContext) -> None:
        """Verify update_note applies partial updates."""
        queue = asyncio.Queue()
        tools = _capture_note_tools(queue, tool_context=mock_tool_context)
        update_tool = tools["update_note"]

        note_id = str(uuid4())
        with _mock_note_repo(mock_tool_context.workspace_id):
            result = await update_tool.handler(
                {
                    "note_id": note_id,
                    "title": "Updated Title",
                }
            )

        data = json.loads(result["content"][0]["text"])
        assert data["operation"] == "update_note"
        assert data["payload"]["note_id"] == note_id
        assert "title" in data["payload"]["changes"]
        assert "is_pinned" not in data["payload"]["changes"]

    @pytest.mark.asyncio
    async def test_update_note_pin_toggle(self, mock_tool_context: ToolContext) -> None:
        """Verify update_note can toggle pinned status."""
        queue = asyncio.Queue()
        tools = _capture_note_tools(queue, tool_context=mock_tool_context)
        update_tool = tools["update_note"]

        with _mock_note_repo(mock_tool_context.workspace_id):
            result = await update_tool.handler(
                {
                    "note_id": str(uuid4()),
                    "is_pinned": True,
                }
            )

        data = json.loads(result["content"][0]["text"])
        assert data["payload"]["changes"]["is_pinned"] is True

    @pytest.mark.asyncio
    async def test_update_note_project_association(self, mock_tool_context: ToolContext) -> None:
        """Verify update_note can set project_id to null."""
        queue = asyncio.Queue()
        tools = _capture_note_tools(queue, tool_context=mock_tool_context)
        update_tool = tools["update_note"]

        with _mock_note_repo(mock_tool_context.workspace_id):
            result = await update_tool.handler(
                {
                    "note_id": str(uuid4()),
                    "project_id": None,
                }
            )

        data = json.loads(result["content"][0]["text"])
        assert data["payload"]["changes"]["project_id"] is None


class TestSearchNoteContent:
    """Test suite for search_note_content tool (NT-004)."""

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
    """Test suite for insert_block tool (NT-005).

    insert_block emits SSE events via EventPublisher — verify queue events.
    """

    @pytest.mark.asyncio
    async def test_insert_block_after_position(self, mock_tool_context: ToolContext) -> None:
        """Verify insert_block emits content_update with after_block_id."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        tools = _capture_content_tools(queue, tool_context=mock_tool_context)
        insert_tool = tools["insert_block"]

        with _mock_note_repo(mock_tool_context.workspace_id):
            result = await insert_tool.handler(
                {
                    "note_id": str(uuid4()),
                    "content_markdown": "New content",
                    "after_block_id": "block-123",
                }
            )

        assert "inserted" in result["content"][0]["text"].lower()
        data = _drain_content_update(queue)
        assert data["operation"] == "insert_blocks"
        assert data["afterBlockId"] == "block-123"
        assert data["beforeBlockId"] is None

    @pytest.mark.asyncio
    async def test_insert_block_before_position(self, mock_tool_context: ToolContext) -> None:
        """Verify insert_block emits content_update with before_block_id."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        tools = _capture_content_tools(queue, tool_context=mock_tool_context)
        insert_tool = tools["insert_block"]

        with _mock_note_repo(mock_tool_context.workspace_id):
            result = await insert_tool.handler(
                {
                    "note_id": str(uuid4()),
                    "content_markdown": "New content",
                    "before_block_id": "block-456",
                }
            )

        assert "inserted" in result["content"][0]["text"].lower()
        data = _drain_content_update(queue)
        assert data["beforeBlockId"] == "block-456"
        assert data["afterBlockId"] is None

    @pytest.mark.asyncio
    async def test_insert_block_append(self, mock_tool_context: ToolContext) -> None:
        """Verify insert_block appends when no position specified."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        tools = _capture_content_tools(queue, tool_context=mock_tool_context)
        insert_tool = tools["insert_block"]

        with _mock_note_repo(mock_tool_context.workspace_id):
            result = await insert_tool.handler(
                {
                    "note_id": str(uuid4()),
                    "content_markdown": "Appended content",
                }
            )

        assert "inserted" in result["content"][0]["text"].lower()
        data = _drain_content_update(queue)
        assert data["afterBlockId"] is None
        assert data["beforeBlockId"] is None


class TestRemoveBlock:
    """Test suite for remove_block tool (NT-006)."""

    @pytest.mark.asyncio
    async def test_remove_block_valid_block(self, mock_tool_context: ToolContext) -> None:
        """Verify remove_block emits content_update SSE event."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        tools = _capture_content_tools(queue, tool_context=mock_tool_context)
        remove_tool = tools["remove_block"]

        with _mock_note_repo(mock_tool_context.workspace_id):
            result = await remove_tool.handler(
                {
                    "note_id": str(uuid4()),
                    "block_id": "block-789",
                }
            )

        assert "removed" in result["content"][0]["text"].lower()
        data = _drain_content_update(queue)
        assert data["operation"] == "remove_block"
        assert data["blockId"] == "block-789"

    @pytest.mark.asyncio
    async def test_remove_block_invalid_block(self, mock_tool_context: ToolContext) -> None:
        """Verify remove_block validates block_id presence."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        tools = _capture_content_tools(queue, tool_context=mock_tool_context)
        remove_tool = tools["remove_block"]

        with _mock_note_repo(mock_tool_context.workspace_id):
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
    async def test_remove_content_pattern_match(self, mock_tool_context: ToolContext) -> None:
        """Verify remove_content emits content_update with pattern."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        tools = _capture_content_tools(queue, tool_context=mock_tool_context)
        remove_tool = tools["remove_content"]

        with _mock_note_repo(mock_tool_context.workspace_id):
            result = await remove_tool.handler(
                {
                    "note_id": str(uuid4()),
                    "pattern": "deprecated",
                }
            )

        assert "removed" in result["content"][0]["text"].lower()
        data = _drain_content_update(queue)
        assert data["operation"] == "remove_content"
        assert data["pattern"] == "deprecated"

    @pytest.mark.asyncio
    async def test_remove_content_scoped_blocks(self, mock_tool_context: ToolContext) -> None:
        """Verify remove_content can target specific blocks."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        tools = _capture_content_tools(queue, tool_context=mock_tool_context)
        remove_tool = tools["remove_content"]

        with _mock_note_repo(mock_tool_context.workspace_id):
            result = await remove_tool.handler(
                {
                    "note_id": str(uuid4()),
                    "pattern": "old",
                    "block_ids": ["block-1", "block-2"],
                }
            )

        data = _drain_content_update(queue)
        assert data["blockIds"] == ["block-1", "block-2"]


class TestReplaceContent:
    """Test suite for replace_content tool (NT-008)."""

    @pytest.mark.asyncio
    async def test_replace_content_simple_replace(self, mock_tool_context: ToolContext) -> None:
        """Verify replace_content emits content_update for simple find/replace."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        tools = _capture_content_tools(queue, tool_context=mock_tool_context)
        replace_tool = tools["replace_content"]

        with _mock_note_repo(mock_tool_context.workspace_id):
            result = await replace_tool.handler(
                {
                    "note_id": str(uuid4()),
                    "old_pattern": "foo",
                    "new_content": "bar",
                }
            )

        assert "replaced" in result["content"][0]["text"].lower()
        data = _drain_content_update(queue)
        assert data["operation"] == "replace_content"
        assert data["oldPattern"] == "foo"
        assert data["newContent"] == "bar"

    @pytest.mark.asyncio
    async def test_replace_content_regex_with_capture_groups(
        self, mock_tool_context: ToolContext
    ) -> None:
        """Verify replace_content supports regex mode."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        tools = _capture_content_tools(queue, tool_context=mock_tool_context)
        replace_tool = tools["replace_content"]

        with _mock_note_repo(mock_tool_context.workspace_id):
            result = await replace_tool.handler(
                {
                    "note_id": str(uuid4()),
                    "old_pattern": r"(\w+)@example\.com",
                    "new_content": r"$1@newdomain.com",
                    "regex": True,
                }
            )

        data = _drain_content_update(queue)
        assert data["regex"] is True

    @pytest.mark.asyncio
    async def test_replace_content_replace_all_flag(self, mock_tool_context: ToolContext) -> None:
        """Verify replace_content respects replace_all flag."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        tools = _capture_content_tools(queue, tool_context=mock_tool_context)
        replace_tool = tools["replace_content"]

        with _mock_note_repo(mock_tool_context.workspace_id):
            result = await replace_tool.handler(
                {
                    "note_id": str(uuid4()),
                    "old_pattern": "old",
                    "new_content": "new",
                    "replace_all": False,
                }
            )

        data = _drain_content_update(queue)
        assert data["replaceAll"] is False


class TestToolNamesConstant:
    """Test suite for TOOL_NAMES constants."""

    def test_note_server_has_9_tools(self) -> None:
        """Verify note_server TOOL_NAMES has 9 entries (summarize_note removed)."""
        from pilot_space.ai.mcp.note_server import TOOL_NAMES

        assert len(TOOL_NAMES) == 9

    def test_note_server_includes_new_tools(self) -> None:
        """Verify note_server TOOL_NAMES includes insert_pm_block and CRUD tools."""
        from pilot_space.ai.mcp.note_server import SERVER_NAME, TOOL_NAMES

        expected = [
            f"mcp__{SERVER_NAME}__insert_pm_block",
            f"mcp__{SERVER_NAME}__create_note",
            f"mcp__{SERVER_NAME}__update_note",
        ]
        for name in expected:
            assert name in TOOL_NAMES

    def test_note_content_server_has_7_tools(self) -> None:
        """Verify note_content_server TOOL_NAMES has 7 entries."""
        from pilot_space.ai.mcp.note_content_server import TOOL_NAMES

        assert len(TOOL_NAMES) == 7

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
