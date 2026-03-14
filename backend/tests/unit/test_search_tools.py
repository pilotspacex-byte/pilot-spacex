"""Unit tests for search MCP tools (semantic_search, search_codebase).

Covers:
- semantic_search with GraphSearchService (hybrid path)
- semantic_search fallback to ILIKE when no GraphSearchService
- semantic_search content_types mapping to NodeType
- search_codebase returns not_implemented status
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from pilot_space.domain.graph_node import GraphNode, NodeType
from pilot_space.domain.graph_query import ScoredNode

pytestmark = pytest.mark.asyncio

_WORKSPACE_ID = uuid4()
_USER_ID = uuid4()


@dataclass
class FakeToolContext:
    """Minimal ToolContext stand-in for tests."""

    db_session: Any
    workspace_id: str
    user_id: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)
    user_role: Any = None


def _make_scored_node(
    node_type: NodeType = NodeType.ISSUE,
    label: str = "Test Issue",
    content: str = "test content",
    score: float = 0.85,
) -> ScoredNode:
    node = GraphNode.create(
        workspace_id=_WORKSPACE_ID,
        node_type=node_type,
        label=label,
        content=content,
    )
    return ScoredNode(
        node=node,
        score=score,
        embedding_score=score * 0.6,
        text_score=score * 0.2,
        recency_score=score * 0.15,
        edge_density_score=score * 0.05,
    )


# ---------------------------------------------------------------------------
# Tests for semantic_search — GraphSearchService hybrid path
# ---------------------------------------------------------------------------


class TestSemanticSearchHybridPath:
    """When GraphSearchService is available in ctx.extra, use hybrid search."""

    async def test_delegates_to_graph_search_service(self) -> None:
        from pilot_space.ai.tools.search_tools import semantic_search

        scored = _make_scored_node(label="Auth bug fix", score=0.92)
        mock_result = MagicMock()
        mock_result.nodes = [scored]
        mock_result.edges = []
        mock_result.query = "auth bug"
        mock_result.embedding_used = True

        mock_service = AsyncMock()
        mock_service.execute = AsyncMock(return_value=mock_result)

        ctx = FakeToolContext(
            db_session=AsyncMock(),
            workspace_id=str(_WORKSPACE_ID),
            extra={"graph_search_service": mock_service},
        )

        result = await semantic_search(query="auth bug", ctx=ctx)

        mock_service.execute.assert_awaited_once()
        assert result["search_method"] == "hybrid"
        assert len(result["results"]) == 1
        assert result["results"][0]["title"] == "Auth bug fix"
        assert result["results"][0]["score"] == 0.92

    async def test_search_method_text_similarity_when_no_embedding(self) -> None:
        from pilot_space.ai.tools.search_tools import semantic_search

        scored = _make_scored_node()
        mock_result = MagicMock()
        mock_result.nodes = [scored]
        mock_result.edges = []
        mock_result.query = "test"
        mock_result.embedding_used = False

        mock_service = AsyncMock()
        mock_service.execute = AsyncMock(return_value=mock_result)

        ctx = FakeToolContext(
            db_session=AsyncMock(),
            workspace_id=str(_WORKSPACE_ID),
            extra={"graph_search_service": mock_service},
        )

        result = await semantic_search(query="test", ctx=ctx)

        assert result["search_method"] == "text_similarity"

    async def test_content_types_issue_maps_to_nodetype_issue(self) -> None:
        from pilot_space.ai.tools.search_tools import semantic_search

        mock_result = MagicMock()
        mock_result.nodes = []
        mock_result.edges = []
        mock_result.query = "test"
        mock_result.embedding_used = True

        mock_service = AsyncMock()
        mock_service.execute = AsyncMock(return_value=mock_result)

        ctx = FakeToolContext(
            db_session=AsyncMock(),
            workspace_id=str(_WORKSPACE_ID),
            extra={"graph_search_service": mock_service},
        )

        await semantic_search(query="test", ctx=ctx, content_types=["issue"])

        call_args = mock_service.execute.call_args[0][0]
        assert call_args.node_types == [NodeType.ISSUE]

    async def test_content_types_note_maps_to_note_and_note_chunk(self) -> None:
        from pilot_space.ai.tools.search_tools import semantic_search

        mock_result = MagicMock()
        mock_result.nodes = []
        mock_result.edges = []
        mock_result.query = "test"
        mock_result.embedding_used = True

        mock_service = AsyncMock()
        mock_service.execute = AsyncMock(return_value=mock_result)

        ctx = FakeToolContext(
            db_session=AsyncMock(),
            workspace_id=str(_WORKSPACE_ID),
            extra={"graph_search_service": mock_service},
        )

        await semantic_search(query="test", ctx=ctx, content_types=["note"])

        call_args = mock_service.execute.call_args[0][0]
        assert set(call_args.node_types) == {NodeType.NOTE, NodeType.NOTE_CHUNK}

    async def test_no_content_types_passes_none(self) -> None:
        from pilot_space.ai.tools.search_tools import semantic_search

        mock_result = MagicMock()
        mock_result.nodes = []
        mock_result.edges = []
        mock_result.query = "test"
        mock_result.embedding_used = True

        mock_service = AsyncMock()
        mock_service.execute = AsyncMock(return_value=mock_result)

        ctx = FakeToolContext(
            db_session=AsyncMock(),
            workspace_id=str(_WORKSPACE_ID),
            extra={"graph_search_service": mock_service},
        )

        await semantic_search(query="test", ctx=ctx, content_types=None)

        call_args = mock_service.execute.call_args[0][0]
        assert call_args.node_types is None

    async def test_limit_capped_at_50(self) -> None:
        from pilot_space.ai.tools.search_tools import semantic_search

        mock_result = MagicMock()
        mock_result.nodes = []
        mock_result.edges = []
        mock_result.query = "test"
        mock_result.embedding_used = True

        mock_service = AsyncMock()
        mock_service.execute = AsyncMock(return_value=mock_result)

        ctx = FakeToolContext(
            db_session=AsyncMock(),
            workspace_id=str(_WORKSPACE_ID),
            extra={"graph_search_service": mock_service},
        )

        await semantic_search(query="test", ctx=ctx, limit=100)

        call_args = mock_service.execute.call_args[0][0]
        assert call_args.limit == 50


# ---------------------------------------------------------------------------
# Tests for semantic_search — ILIKE fallback path
# ---------------------------------------------------------------------------


class TestSemanticSearchFallback:
    """When no GraphSearchService in ctx.extra, fall back to ILIKE text search."""

    async def test_fallback_when_no_graph_search_service(self) -> None:
        from pilot_space.ai.tools.search_tools import semantic_search

        session = AsyncMock()
        # Mock issue query result
        mock_issue_result = MagicMock()
        mock_issue_result.scalars.return_value.all.return_value = []
        # Mock note query result
        mock_note_result = MagicMock()
        mock_note_result.scalars.return_value.all.return_value = []

        session.execute = AsyncMock(side_effect=[mock_issue_result, mock_note_result])

        ctx = FakeToolContext(
            db_session=session,
            workspace_id=str(_WORKSPACE_ID),
            extra={},  # No graph_search_service
        )

        result = await semantic_search(query="test", ctx=ctx)

        assert result["search_method"] == "text_similarity"
        session.execute.assert_called()


# ---------------------------------------------------------------------------
# Tests for _map_content_types — filter semantics
# ---------------------------------------------------------------------------


class TestMapContentTypes:
    """_map_content_types must distinguish None (all) from empty (no matches)."""

    def test_none_returns_none(self) -> None:
        from pilot_space.ai.tools.search_tools import _map_content_types

        assert _map_content_types(None) is None

    def test_valid_types_return_node_types(self) -> None:
        from pilot_space.ai.tools.search_tools import _map_content_types

        result = _map_content_types(["issue"])
        assert result is not None
        assert len(result) > 0

    def test_unmapped_types_return_empty_list(self) -> None:
        """Unmapped types return [] (no matches), not None (all types)."""
        from pilot_space.ai.tools.search_tools import _map_content_types

        result = _map_content_types(["page", "unknown"])
        assert result is not None
        assert result == []

    def test_mixed_mapped_and_unmapped(self) -> None:
        from pilot_space.ai.tools.search_tools import _map_content_types

        result = _map_content_types(["issue", "page"])
        assert result is not None
        assert len(result) > 0  # Only "issue" maps

    def test_empty_list_returns_empty_list(self) -> None:
        from pilot_space.ai.tools.search_tools import _map_content_types

        result = _map_content_types([])
        assert result == []


# ---------------------------------------------------------------------------
# Tests for search_codebase — not_implemented stub
# ---------------------------------------------------------------------------


class TestSearchCodebase:
    """search_codebase should return honest not_implemented status without DB query."""

    async def test_returns_not_implemented_without_db_query(self) -> None:
        from pilot_space.ai.tools.search_tools import search_codebase

        session = AsyncMock()
        ctx = FakeToolContext(
            db_session=session,
            workspace_id=str(_WORKSPACE_ID),
        )

        result = await search_codebase(query="async def", ctx=ctx)

        assert result["found"] is False
        assert result["status"] == "not_implemented"
        assert "not yet available" in result["message"].lower()
        assert result["query"] == "async def"
        # Should NOT have queried the database
        session.execute.assert_not_awaited()
