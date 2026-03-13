"""Unit tests for GraphSearchService.

Tests cover:
- Successful hybrid search returning scored nodes.
- Fallback to text-only search when OpenAI embedding fails.
- Merging user context when user_id is provided.
- Text-only mode when no API key is supplied.
"""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from pilot_space.application.services.memory.graph_search_service import (
    GraphSearchPayload,
    GraphSearchResult,
    GraphSearchService,
)
from pilot_space.domain.graph_edge import EdgeType, GraphEdge
from pilot_space.domain.graph_node import GraphNode, NodeType
from pilot_space.domain.graph_query import ScoredNode

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_node(
    workspace_id: UUID,
    *,
    node_type: NodeType = NodeType.ISSUE,
    label: str = "PS-1",
    user_id: UUID | None = None,
) -> GraphNode:
    return GraphNode.create(
        workspace_id=workspace_id,
        node_type=node_type,
        label=label,
        content="sample content",
        user_id=user_id,
    )


def _make_scored_node(node: GraphNode, score: float = 0.8) -> ScoredNode:
    return ScoredNode(
        node=node,
        score=score,
        embedding_score=score,
        text_score=0.5,
        recency_score=0.5,
        edge_density_score=0.1,
    )


def _make_edge(source_id: UUID, target_id: UUID) -> GraphEdge:
    return GraphEdge(
        source_id=source_id,
        target_id=target_id,
        edge_type=EdgeType.RELATES_TO,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def workspace_id() -> UUID:
    return uuid4()


@pytest.fixture
def user_id() -> UUID:
    return uuid4()


@pytest.fixture
def mock_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.hybrid_search = AsyncMock(return_value=[])
    repo.get_user_context = AsyncMock(return_value=[])
    repo.get_subgraph = AsyncMock(return_value=([], []))
    return repo


@pytest.fixture
def service(mock_repo: AsyncMock) -> GraphSearchService:
    return GraphSearchService(knowledge_graph_repository=mock_repo)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGraphSearchServiceReturnsNodes:
    """Verify that hybrid search results are surfaced correctly."""

    @pytest.mark.asyncio
    async def test_search_returns_scored_nodes(
        self,
        service: GraphSearchService,
        mock_repo: AsyncMock,
        workspace_id: UUID,
    ) -> None:
        """Scored nodes from hybrid_search appear in the result."""
        node = _make_node(workspace_id)
        scored = _make_scored_node(node)
        mock_repo.hybrid_search.return_value = [scored]
        mock_repo.get_subgraph.return_value = ([node], [])

        payload = GraphSearchPayload(
            query="rate limiting",
            workspace_id=workspace_id,
        )
        result = await service.execute(payload)

        assert isinstance(result, GraphSearchResult)
        assert len(result.nodes) == 1
        assert result.nodes[0].node.id == node.id
        assert result.query == "rate limiting"
        mock_repo.hybrid_search.assert_awaited_once_with(
            query_embedding=None,
            query_text="rate limiting",
            workspace_id=workspace_id,
            node_types=None,
            limit=10,
            since=None,
        )

    @pytest.mark.asyncio
    async def test_search_returns_empty_when_no_results(
        self,
        service: GraphSearchService,
        mock_repo: AsyncMock,
        workspace_id: UUID,
    ) -> None:
        """Empty result set is handled gracefully."""
        mock_repo.hybrid_search.return_value = []

        payload = GraphSearchPayload(query="unknown", workspace_id=workspace_id)
        result = await service.execute(payload)

        assert result.nodes == []
        assert result.edges == []
        assert result.embedding_used is False

    @pytest.mark.asyncio
    async def test_search_collects_intra_result_edges(
        self,
        service: GraphSearchService,
        mock_repo: AsyncMock,
        workspace_id: UUID,
    ) -> None:
        """Edges where both endpoints are in the result set are included."""
        node_a = _make_node(workspace_id, label="PS-1")
        node_b = _make_node(workspace_id, label="PS-2")
        edge = _make_edge(node_a.id, node_b.id)

        mock_repo.hybrid_search.return_value = [
            _make_scored_node(node_a),
            _make_scored_node(node_b),
        ]
        mock_repo.get_edges_between.return_value = [edge]

        payload = GraphSearchPayload(query="foo", workspace_id=workspace_id)
        result = await service.execute(payload)

        assert len(result.edges) == 1
        assert result.edges[0].source_id == node_a.id
        assert result.edges[0].target_id == node_b.id


class TestGraphSearchServiceEmbeddingFallback:
    """Verify graceful degradation when embedding is unavailable."""

    @pytest.mark.asyncio
    async def test_search_falls_back_to_text_on_embedding_failure(
        self,
        service: GraphSearchService,
        mock_repo: AsyncMock,
        workspace_id: UUID,
    ) -> None:
        """When no EmbeddingService is configured, text-only search runs and embedding_used is False."""
        node = _make_node(workspace_id)
        mock_repo.hybrid_search.return_value = [_make_scored_node(node)]

        payload = GraphSearchPayload(query="decisions", workspace_id=workspace_id)
        result = await service.execute(payload)

        assert result.embedding_used is False
        assert len(result.nodes) == 1
        # hybrid_search called with no embedding (fallback path)
        mock_repo.hybrid_search.assert_awaited_once_with(
            query_embedding=None,
            query_text="decisions",
            workspace_id=workspace_id,
            node_types=None,
            limit=10,
            since=None,
        )

    @pytest.mark.asyncio
    async def test_search_without_api_key_text_only(
        self,
        service: GraphSearchService,
        mock_repo: AsyncMock,
        workspace_id: UUID,
    ) -> None:
        """No EmbeddingService configured → embedding skipped, embedding_used is False."""
        mock_repo.hybrid_search.return_value = []

        payload = GraphSearchPayload(query="architecture decisions", workspace_id=workspace_id)
        result = await service.execute(payload)

        assert result.embedding_used is False
        mock_repo.hybrid_search.assert_awaited_once_with(
            query_embedding=None,
            query_text="architecture decisions",
            workspace_id=workspace_id,
            node_types=None,
            limit=10,
            since=None,
        )


class TestGraphSearchServiceUserContext:
    """Verify user context merging behaviour."""

    @pytest.mark.asyncio
    async def test_search_includes_user_context(
        self,
        service: GraphSearchService,
        mock_repo: AsyncMock,
        workspace_id: UUID,
        user_id: UUID,
    ) -> None:
        """User-scoped nodes are merged into results when user_id is provided."""
        workspace_node = _make_node(workspace_id, label="PS-10")
        user_node = _make_node(workspace_id, label="pref-1", user_id=user_id)

        mock_repo.hybrid_search.return_value = [_make_scored_node(workspace_node)]
        mock_repo.get_user_context.return_value = [user_node]

        payload = GraphSearchPayload(
            query="preferences",
            workspace_id=workspace_id,
            user_id=user_id,
        )
        result = await service.execute(payload)

        returned_ids = {sn.node.id for sn in result.nodes}
        assert workspace_node.id in returned_ids
        assert user_node.id in returned_ids
        mock_repo.get_user_context.assert_awaited_once_with(
            user_id=user_id,
            workspace_id=workspace_id,
            limit=10,
        )

    @pytest.mark.asyncio
    async def test_search_does_not_duplicate_user_context_nodes(
        self,
        service: GraphSearchService,
        mock_repo: AsyncMock,
        workspace_id: UUID,
        user_id: UUID,
    ) -> None:
        """A node already in hybrid_search results is not added twice from user context."""
        node = _make_node(workspace_id, label="PS-5", user_id=user_id)
        mock_repo.hybrid_search.return_value = [_make_scored_node(node)]
        mock_repo.get_user_context.return_value = [node]  # same node

        payload = GraphSearchPayload(
            query="duplicate check",
            workspace_id=workspace_id,
            user_id=user_id,
        )
        result = await service.execute(payload)

        # Only one occurrence of the node
        node_ids = [sn.node.id for sn in result.nodes]
        assert node_ids.count(node.id) == 1

    @pytest.mark.asyncio
    async def test_search_skips_user_context_when_no_user_id(
        self,
        service: GraphSearchService,
        mock_repo: AsyncMock,
        workspace_id: UUID,
    ) -> None:
        """get_user_context is NOT called when user_id is absent."""
        mock_repo.hybrid_search.return_value = []

        payload = GraphSearchPayload(query="anything", workspace_id=workspace_id)
        await service.execute(payload)

        mock_repo.get_user_context.assert_not_awaited()


class TestGraphSearchServiceReranking:
    """Verify score re-ranking applies the four-component formula."""

    @pytest.mark.asyncio
    async def test_nodes_sorted_by_combined_score(
        self,
        service: GraphSearchService,
        mock_repo: AsyncMock,
        workspace_id: UUID,
    ) -> None:
        """High-score node appears before low-score node after re-ranking."""
        low_node = _make_node(workspace_id, label="low")
        high_node = _make_node(workspace_id, label="high")

        low_scored = ScoredNode(
            node=low_node,
            score=0.1,
            embedding_score=0.1,
            text_score=0.1,
            recency_score=0.1,
            edge_density_score=0.0,
        )
        high_scored = ScoredNode(
            node=high_node,
            score=0.9,
            embedding_score=0.9,
            text_score=0.8,
            recency_score=0.7,
            edge_density_score=0.5,
        )
        # Return in reverse order so re-ranking is observable
        mock_repo.hybrid_search.return_value = [low_scored, high_scored]

        payload = GraphSearchPayload(query="test", workspace_id=workspace_id)
        result = await service.execute(payload)

        assert result.nodes[0].node.id == high_node.id
        assert result.nodes[1].node.id == low_node.id


class TestGetEmbeddingNoService:
    """M-5: Verify _get_embedding returns (None, False) when no service."""

    @pytest.mark.asyncio
    async def test_get_embedding_no_service_returns_none(
        self,
        mock_repo: AsyncMock,
    ) -> None:
        """Service with embedding_service=None returns (None, False)."""
        svc = GraphSearchService(
            knowledge_graph_repository=mock_repo,
            embedding_service=None,
        )
        result = await svc._get_embedding("query")
        assert result == (None, False)


class TestCollectEdgesException:
    """M-6: Verify _collect_edges returns empty list on exception."""

    @pytest.mark.asyncio
    async def test_collect_edges_exception_returns_empty(
        self,
        mock_repo: AsyncMock,
    ) -> None:
        """When get_edges_between raises, _collect_edges returns []."""
        mock_repo.get_edges_between = AsyncMock(side_effect=Exception("DB error"))
        svc = GraphSearchService(
            knowledge_graph_repository=mock_repo,
            embedding_service=None,
        )

        ws = uuid4()
        node = _make_node(ws)
        scored = _make_scored_node(node)

        edges = await svc._collect_edges([scored], workspace_id=ws)
        assert edges == []
