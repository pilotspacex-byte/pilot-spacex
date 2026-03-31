"""Unit tests for MCP note query server tools (note_query_server.py).

Tests the in-process SDK MCP server containing read-only search tools
extracted from note_server.py in a CQRS-lite split.

M-8: search_notes returns structured JSON for AI multi-step reasoning.
"""

from __future__ import annotations

import json
from datetime import UTC
from unittest.mock import patch

import pytest

from pilot_space.ai.mcp.note_query_server import (
    SERVER_NAME,
    TOOL_NAMES,
    create_note_query_server,
)


def _capture_tools(*, tool_context=None):
    """Create note query server and capture the SdkMcpTool objects."""
    captured: dict[str, object] = {}

    import pilot_space.ai.mcp.note_query_server as nqs_module

    original_create = nqs_module.create_sdk_mcp_server

    def _intercept_create(*, name, version, tools):
        captured["tools"] = {t.name: t for t in tools}
        return original_create(name=name, version=version, tools=tools)

    with patch.object(nqs_module, "create_sdk_mcp_server", side_effect=_intercept_create):
        create_note_query_server(tool_context=tool_context)

    return captured["tools"]


class TestToolNamesConstant:
    """Tests for the TOOL_NAMES constant."""

    def test_has_one_tool(self) -> None:
        """TOOL_NAMES has exactly 1 entry (search_notes)."""
        assert len(TOOL_NAMES) == 1

    def test_includes_search_notes(self) -> None:
        """TOOL_NAMES includes the search_notes tool."""
        assert f"mcp__{SERVER_NAME}__search_notes" in TOOL_NAMES

    def test_all_tools_have_server_prefix(self) -> None:
        """All tool names follow the mcp__{SERVER_NAME}__<tool> pattern."""
        prefix = f"mcp__{SERVER_NAME}__"
        for name in TOOL_NAMES:
            assert name.startswith(prefix), f"{name} missing server prefix"

    def test_server_name_is_pilot_notes_query(self) -> None:
        """SERVER_NAME is 'pilot-notes-query'."""
        assert SERVER_NAME == "pilot-notes-query"


class TestSearchNotesWithoutContext:
    """Tests for search_notes when tool_context is not provided."""

    @pytest.mark.asyncio
    async def test_returns_error_without_context(self) -> None:
        """search_notes returns error text when tool_context is not available."""
        tools = _capture_tools(tool_context=None)
        search_tool = tools["search_notes"]

        result = await search_tool.handler({"query": "test"})

        text = result["content"][0]["text"]
        assert "Error" in text
        assert "tool_context not available" in text


# NoteRepository is lazily imported inside search_notes handler; patch at source
_NOTE_REPO_PATH = "pilot_space.infrastructure.database.repositories.note_repository.NoteRepository"


class TestSearchNotesWithContext:
    """Tests for search_notes with a mocked tool_context."""

    @pytest.mark.asyncio
    async def test_returns_matching_notes(self) -> None:
        """search_notes returns structured JSON with matching note metadata (M-8)."""
        from datetime import datetime
        from unittest.mock import AsyncMock, MagicMock
        from uuid import UUID

        mock_context = MagicMock()
        mock_context.workspace_id = "ffffffff-ffff-ffff-ffff-ffffffffffff"
        mock_context.extra = {}
        mock_context.db_session = AsyncMock()

        note1 = MagicMock()
        note1.id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        note1.title = "Sprint Planning Notes"
        note1.project_id = None
        note1.created_at = datetime(2025, 1, 1, tzinfo=UTC)
        note1.content = {}

        mock_repo_instance = AsyncMock()
        mock_repo_instance.list_notes = AsyncMock(return_value=[note1])

        tools = _capture_tools(tool_context=mock_context)
        search_tool = tools["search_notes"]

        with patch(_NOTE_REPO_PATH, return_value=mock_repo_instance):
            result = await search_tool.handler({"query": "sprint"})

        text = result["content"][0]["text"]
        parsed = json.loads(text)
        assert parsed["count"] == 1
        assert parsed["query"] == "sprint"
        assert len(parsed["notes"]) == 1
        assert parsed["notes"][0]["title"] == "Sprint Planning Notes"
        assert parsed["notes"][0]["id"] == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"

    @pytest.mark.asyncio
    async def test_returns_empty_result_message(self) -> None:
        """search_notes returns structured JSON with count=0 when no notes match (M-8)."""
        from unittest.mock import AsyncMock, MagicMock

        mock_context = MagicMock()
        mock_context.workspace_id = "ffffffff-ffff-ffff-ffff-ffffffffffff"
        mock_context.extra = {}
        mock_context.db_session = AsyncMock()

        mock_repo_instance = AsyncMock()
        mock_repo_instance.list_notes = AsyncMock(return_value=[])

        tools = _capture_tools(tool_context=mock_context)
        search_tool = tools["search_notes"]

        with patch(_NOTE_REPO_PATH, return_value=mock_repo_instance):
            result = await search_tool.handler({"query": "nonexistent"})

        text = result["content"][0]["text"]
        parsed = json.loads(text)
        assert parsed["count"] == 0
        assert parsed["query"] == "nonexistent"
        assert parsed["notes"] == []

    @pytest.mark.asyncio
    async def test_respects_limit_cap(self) -> None:
        """search_notes caps limit at 100 regardless of what's passed."""
        from unittest.mock import AsyncMock, MagicMock

        mock_context = MagicMock()
        mock_context.workspace_id = "ffffffff-ffff-ffff-ffff-ffffffffffff"
        mock_context.extra = {}
        mock_context.db_session = AsyncMock()

        mock_repo_instance = AsyncMock()
        mock_repo_instance.list_notes = AsyncMock(return_value=[])

        tools = _capture_tools(tool_context=mock_context)
        search_tool = tools["search_notes"]

        with patch(_NOTE_REPO_PATH, return_value=mock_repo_instance):
            await search_tool.handler({"query": "test", "limit": 999})

        call_kwargs = mock_repo_instance.list_notes.call_args.kwargs
        assert call_kwargs["limit"] <= 100

    @pytest.mark.asyncio
    async def test_json_result_has_required_note_fields(self) -> None:
        """search_notes JSON response includes id, title, projectId, preview, createdAt."""
        from datetime import datetime
        from unittest.mock import AsyncMock, MagicMock
        from uuid import UUID

        mock_context = MagicMock()
        mock_context.workspace_id = "ffffffff-ffff-ffff-ffff-ffffffffffff"
        mock_context.extra = {}
        mock_context.db_session = AsyncMock()

        note1 = MagicMock()
        note1.id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
        note1.title = "Architecture Notes"
        note1.project_id = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
        note1.created_at = datetime(2025, 6, 1, tzinfo=UTC)
        note1.content = {}

        mock_repo_instance = AsyncMock()
        mock_repo_instance.list_notes = AsyncMock(return_value=[note1])

        tools = _capture_tools(tool_context=mock_context)
        search_tool = tools["search_notes"]

        with patch(_NOTE_REPO_PATH, return_value=mock_repo_instance):
            result = await search_tool.handler({"query": "arch"})

        parsed = json.loads(result["content"][0]["text"])
        note = parsed["notes"][0]
        assert "id" in note
        assert "title" in note
        assert "projectId" in note
        assert "preview" in note
        assert "createdAt" in note
