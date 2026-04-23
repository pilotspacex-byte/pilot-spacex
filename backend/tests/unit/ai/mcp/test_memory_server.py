"""Unit tests for MCP memory server tool (memory_server.py).

Tests the recall_memory MCP tool that wraps MemoryRecallService for
on-demand workspace memory retrieval (Phase 81 lazy context).
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pilot_space.ai.mcp.memory_server import (
    SERVER_NAME,
    TOOL_NAMES,
    create_memory_server,
)


def _capture_tools(*, tool_context=None):
    """Create memory server and capture the SdkMcpTool objects."""
    captured: dict[str, object] = {}

    import pilot_space.ai.mcp.memory_server as ms_module

    original_create = ms_module.create_sdk_mcp_server

    def _intercept_create(*, name, version, tools):
        captured["tools"] = {t.name: t for t in tools}
        return original_create(name=name, version=version, tools=tools)

    with patch.object(ms_module, "create_sdk_mcp_server", side_effect=_intercept_create):
        create_memory_server(tool_context=tool_context)

    return captured["tools"]


class TestToolNamesConstant:
    """Tests for the TOOL_NAMES constant."""

    def test_has_one_tool(self) -> None:
        """TOOL_NAMES has exactly 1 entry (recall_memory)."""
        assert len(TOOL_NAMES) == 1

    def test_includes_recall_memory(self) -> None:
        """TOOL_NAMES includes the recall_memory tool."""
        assert f"mcp__{SERVER_NAME}__recall_memory" in TOOL_NAMES

    def test_all_tools_have_server_prefix(self) -> None:
        """All tool names follow the mcp__{SERVER_NAME}__<tool> pattern."""
        prefix = f"mcp__{SERVER_NAME}__"
        for name in TOOL_NAMES:
            assert name.startswith(prefix), f"{name} missing server prefix"

    def test_server_name_is_pilot_memory(self) -> None:
        """SERVER_NAME is 'pilot-memory'."""
        assert SERVER_NAME == "pilot-memory"


class TestRecallMemoryWithoutContext:
    """Tests for recall_memory when tool_context is not provided."""

    @pytest.mark.asyncio
    async def test_returns_error_without_context(self) -> None:
        """recall_memory returns error text when tool_context is not available."""
        tools = _capture_tools(tool_context=None)
        recall_tool = tools["recall_memory"]

        result = await recall_tool.handler({"query": "test"})

        text = result["content"][0]["text"]
        assert "Error" in text
        assert "tool_context not available" in text


_GET_CONTAINER_PATH = "pilot_space.container.container.get_container"


class TestRecallMemoryWithContext:
    """Tests for recall_memory with a mocked tool_context."""

    @pytest.mark.asyncio
    async def test_returns_matching_memories(self) -> None:
        """recall_memory returns structured JSON with matching memory items."""
        mock_context = MagicMock()
        mock_context.workspace_id = "ffffffff-ffff-ffff-ffff-ffffffffffff"
        mock_context.user_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        mock_context.db_session = AsyncMock()

        item1 = MagicMock()
        item1.source_type = "note_summary"
        item1.source_id = "11111111-1111-1111-1111-111111111111"
        item1.score = 0.8765
        item1.snippet = "Sprint planning decisions from Q1"
        item1.created_at = "2025-01-15T10:00:00"

        item2 = MagicMock()
        item2.source_type = "user_correction"
        item2.source_id = "22222222-2222-2222-2222-222222222222"
        item2.score = 0.654
        item2.snippet = "User corrected naming convention"
        item2.created_at = "2025-02-20T14:30:00"

        mock_recall_result = MagicMock()
        mock_recall_result.items = [item1, item2]
        mock_recall_result.cache_hit = False
        mock_recall_result.elapsed_ms = 42.5

        mock_service = AsyncMock()
        mock_service.recall = AsyncMock(return_value=mock_recall_result)

        mock_container = MagicMock()
        mock_container.memory_recall_service.return_value = mock_service

        tools = _capture_tools(tool_context=mock_context)
        recall_tool = tools["recall_memory"]

        with patch(_GET_CONTAINER_PATH, return_value=mock_container):
            result = await recall_tool.handler({"query": "sprint planning"})

        text = result["content"][0]["text"]
        parsed = json.loads(text)

        assert parsed["count"] == 2
        assert parsed["query"] == "sprint planning"
        assert parsed["cache_hit"] is False
        assert parsed["elapsed_ms"] == 42.5
        assert len(parsed["memories"]) == 2

        mem0 = parsed["memories"][0]
        assert mem0["source_type"] == "note_summary"
        assert mem0["source_id"] == "11111111-1111-1111-1111-111111111111"
        assert mem0["score"] == 0.876  # rounded to 3 decimals
        assert mem0["snippet"] == "Sprint planning decisions from Q1"
        assert mem0["created_at"] == "2025-01-15T10:00:00"

        mem1 = parsed["memories"][1]
        assert mem1["source_type"] == "user_correction"
        assert mem1["score"] == 0.654

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_matches(self) -> None:
        """recall_memory returns count=0 when no memories match."""
        mock_context = MagicMock()
        mock_context.workspace_id = "ffffffff-ffff-ffff-ffff-ffffffffffff"
        mock_context.user_id = None
        mock_context.db_session = AsyncMock()

        mock_recall_result = MagicMock()
        mock_recall_result.items = []
        mock_recall_result.cache_hit = False
        mock_recall_result.elapsed_ms = 12.0

        mock_service = AsyncMock()
        mock_service.recall = AsyncMock(return_value=mock_recall_result)

        mock_container = MagicMock()
        mock_container.memory_recall_service.return_value = mock_service

        tools = _capture_tools(tool_context=mock_context)
        recall_tool = tools["recall_memory"]

        with patch(_GET_CONTAINER_PATH, return_value=mock_container):
            result = await recall_tool.handler({"query": "nonexistent topic"})

        parsed = json.loads(result["content"][0]["text"])
        assert parsed["count"] == 0
        assert parsed["memories"] == []

    @pytest.mark.asyncio
    async def test_container_resolution_failure(self) -> None:
        """recall_memory returns error when container cannot resolve service."""
        mock_context = MagicMock()
        mock_context.workspace_id = "ffffffff-ffff-ffff-ffff-ffffffffffff"
        mock_context.user_id = None
        mock_context.db_session = AsyncMock()

        tools = _capture_tools(tool_context=mock_context)
        recall_tool = tools["recall_memory"]

        with patch(_GET_CONTAINER_PATH, side_effect=RuntimeError("container not ready")):
            result = await recall_tool.handler({"query": "test"})

        text = result["content"][0]["text"]
        assert "Error" in text
        assert "MemoryRecallService not available" in text


class TestRecallMemoryLimitCap:
    """Tests for recall_memory limit parameter capping."""

    @pytest.mark.asyncio
    async def test_limit_capped_at_10(self) -> None:
        """recall_memory caps limit at 10 regardless of what's passed."""
        mock_context = MagicMock()
        mock_context.workspace_id = "ffffffff-ffff-ffff-ffff-ffffffffffff"
        mock_context.user_id = None
        mock_context.db_session = AsyncMock()

        mock_recall_result = MagicMock()
        mock_recall_result.items = []
        mock_recall_result.cache_hit = False
        mock_recall_result.elapsed_ms = 5.0

        mock_service = AsyncMock()
        mock_service.recall = AsyncMock(return_value=mock_recall_result)

        mock_container = MagicMock()
        mock_container.memory_recall_service.return_value = mock_service

        tools = _capture_tools(tool_context=mock_context)
        recall_tool = tools["recall_memory"]

        with patch(_GET_CONTAINER_PATH, return_value=mock_container):
            await recall_tool.handler({"query": "test", "limit": 999})

        call_args = mock_service.recall.call_args[0][0]
        assert call_args.k <= 10


class TestRecallMemoryWithTypes:
    """Tests for recall_memory types filter parameter."""

    @pytest.mark.asyncio
    async def test_passes_types_to_payload(self) -> None:
        """recall_memory passes types filter to RecallPayload when provided."""
        mock_context = MagicMock()
        mock_context.workspace_id = "ffffffff-ffff-ffff-ffff-ffffffffffff"
        mock_context.user_id = None
        mock_context.db_session = AsyncMock()

        mock_recall_result = MagicMock()
        mock_recall_result.items = []
        mock_recall_result.cache_hit = False
        mock_recall_result.elapsed_ms = 3.0

        mock_service = AsyncMock()
        mock_service.recall = AsyncMock(return_value=mock_recall_result)

        mock_container = MagicMock()
        mock_container.memory_recall_service.return_value = mock_service

        tools = _capture_tools(tool_context=mock_context)
        recall_tool = tools["recall_memory"]

        with patch(_GET_CONTAINER_PATH, return_value=mock_container):
            await recall_tool.handler({
                "query": "decisions",
                "types": ["issue_decision", "user_correction"],
            })

        call_args = mock_service.recall.call_args[0][0]
        assert call_args.types == ("issue_decision", "user_correction")

    @pytest.mark.asyncio
    async def test_omitted_types_passes_none(self) -> None:
        """recall_memory passes types=None when types parameter is omitted."""
        mock_context = MagicMock()
        mock_context.workspace_id = "ffffffff-ffff-ffff-ffff-ffffffffffff"
        mock_context.user_id = None
        mock_context.db_session = AsyncMock()

        mock_recall_result = MagicMock()
        mock_recall_result.items = []
        mock_recall_result.cache_hit = False
        mock_recall_result.elapsed_ms = 3.0

        mock_service = AsyncMock()
        mock_service.recall = AsyncMock(return_value=mock_recall_result)

        mock_container = MagicMock()
        mock_container.memory_recall_service.return_value = mock_service

        tools = _capture_tools(tool_context=mock_context)
        recall_tool = tools["recall_memory"]

        with patch(_GET_CONTAINER_PATH, return_value=mock_container):
            await recall_tool.handler({"query": "anything"})

        call_args = mock_service.recall.call_args[0][0]
        assert call_args.types is None
