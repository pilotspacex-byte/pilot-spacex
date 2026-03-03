"""Unit tests for GraphQuery value objects.

Tests cover:
- GraphQuery construction and defaults
- ScoredNode construction
- GraphContext construction, properties, and intra_edges()
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest

from pilot_space.domain.graph_edge import EdgeType, GraphEdge
from pilot_space.domain.graph_node import GraphNode, NodeType
from pilot_space.domain.graph_query import GraphContext, GraphQuery, ScoredNode

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_node(**kwargs: Any) -> GraphNode:
    """Factory for GraphNode with sensible defaults."""
    defaults: dict[str, Any] = {
        "workspace_id": uuid4(),
        "node_type": NodeType.NOTE,
        "label": "Node",
        "content": "content",
    }
    defaults.update(kwargs)
    return GraphNode(**defaults)


def make_scored_node(node: GraphNode | None = None, **kwargs: Any) -> ScoredNode:
    """Factory for ScoredNode with sensible defaults."""
    defaults: dict[str, Any] = {
        "node": node or make_node(),
        "score": 0.8,
        "embedding_score": 0.85,
        "text_score": 0.7,
        "recency_score": 0.9,
        "edge_density_score": 0.6,
    }
    defaults.update(kwargs)
    return ScoredNode(**defaults)


def make_edge(source_id: Any = None, target_id: Any = None, **kwargs: Any) -> GraphEdge:
    """Factory for GraphEdge with sensible defaults."""
    defaults: dict[str, Any] = {
        "source_id": source_id or uuid4(),
        "target_id": target_id or uuid4(),
        "edge_type": EdgeType.RELATES_TO,
    }
    defaults.update(kwargs)
    return GraphEdge(**defaults)


def make_query(**kwargs: Any) -> GraphQuery:
    """Factory for GraphQuery with sensible defaults."""
    defaults: dict[str, Any] = {
        "query_text": "find relevant context",
        "workspace_id": uuid4(),
    }
    defaults.update(kwargs)
    return GraphQuery(**defaults)


# ---------------------------------------------------------------------------
# GraphQuery
# ---------------------------------------------------------------------------


class TestGraphQuery:
    """Tests for GraphQuery value object construction and defaults."""

    def test_required_fields_stored_correctly(self) -> None:
        ws = uuid4()
        q = GraphQuery(query_text="hello", workspace_id=ws)
        assert q.query_text == "hello"
        assert q.workspace_id == ws

    def test_defaults(self) -> None:
        q = make_query()
        assert q.user_id is None
        assert q.node_types is None
        assert q.limit == 10
        assert q.max_depth == 2
        assert q.include_user_context is True

    def test_user_id_stored_when_provided(self) -> None:
        uid = uuid4()
        q = make_query(user_id=uid)
        assert q.user_id == uid

    def test_node_types_filter_stored(self) -> None:
        types = [NodeType.ISSUE, NodeType.NOTE]
        q = make_query(node_types=types)
        assert q.node_types == types

    def test_limit_overridden(self) -> None:
        q = make_query(limit=25)
        assert q.limit == 25

    def test_max_depth_overridden(self) -> None:
        q = make_query(max_depth=5)
        assert q.max_depth == 5

    def test_include_user_context_false(self) -> None:
        q = make_query(include_user_context=False)
        assert q.include_user_context is False

    def test_is_frozen(self) -> None:
        """GraphQuery is immutable (frozen=True)."""
        q = make_query()
        with pytest.raises((AttributeError, TypeError)):
            q.query_text = "mutated"  # type: ignore[misc]

    def test_equality_based_on_values(self) -> None:
        ws = uuid4()
        q1 = GraphQuery(query_text="x", workspace_id=ws)
        q2 = GraphQuery(query_text="x", workspace_id=ws)
        assert q1 == q2

    def test_inequality_different_query_text(self) -> None:
        ws = uuid4()
        q1 = GraphQuery(query_text="a", workspace_id=ws)
        q2 = GraphQuery(query_text="b", workspace_id=ws)
        assert q1 != q2


# ---------------------------------------------------------------------------
# ScoredNode
# ---------------------------------------------------------------------------


class TestScoredNode:
    """Tests for ScoredNode construction and field storage."""

    def test_required_fields_stored(self) -> None:
        node = make_node()
        sn = ScoredNode(
            node=node,
            score=0.9,
            embedding_score=0.95,
            text_score=0.85,
            recency_score=0.8,
            edge_density_score=0.7,
        )
        assert sn.node is node
        assert sn.score == 0.9
        assert sn.embedding_score == 0.95
        assert sn.text_score == 0.85
        assert sn.recency_score == 0.8
        assert sn.edge_density_score == 0.7

    def test_node_reference_preserved(self) -> None:
        node = make_node(label="Important Node")
        sn = make_scored_node(node=node)
        assert sn.node.label == "Important Node"

    def test_zero_scores_acceptable(self) -> None:
        sn = make_scored_node(score=0.0, embedding_score=0.0, text_score=0.0)
        assert sn.score == 0.0

    def test_perfect_scores_acceptable(self) -> None:
        sn = make_scored_node(
            score=1.0,
            embedding_score=1.0,
            text_score=1.0,
            recency_score=1.0,
            edge_density_score=1.0,
        )
        assert sn.score == 1.0


# ---------------------------------------------------------------------------
# GraphContext
# ---------------------------------------------------------------------------


class TestGraphContext:
    """Tests for GraphContext container and derived properties."""

    def _make_context(
        self,
        nodes: list[ScoredNode] | None = None,
        edges: list[GraphEdge] | None = None,
        query: GraphQuery | None = None,
        embedding_used: bool = False,
    ) -> GraphContext:
        return GraphContext(
            nodes=nodes or [],
            edges=edges or [],
            query=query or make_query(),
            embedding_used=embedding_used,
        )

    def test_empty_context_defaults(self) -> None:
        ctx = self._make_context()
        assert ctx.nodes == []
        assert ctx.edges == []
        assert ctx.embedding_used is False

    def test_node_count_reflects_nodes_list(self) -> None:
        ctx = self._make_context(nodes=[make_scored_node(), make_scored_node()])
        assert ctx.node_count == 2

    def test_edge_count_reflects_edges_list(self) -> None:
        ctx = self._make_context(edges=[make_edge(), make_edge()])
        assert ctx.edge_count == 2

    def test_top_node_returns_first_scored_node(self) -> None:
        sn1 = make_scored_node(score=0.9)
        sn2 = make_scored_node(score=0.7)
        ctx = self._make_context(nodes=[sn1, sn2])
        assert ctx.top_node is sn1

    def test_top_node_returns_none_when_empty(self) -> None:
        ctx = self._make_context(nodes=[])
        assert ctx.top_node is None

    def test_embedding_used_stored(self) -> None:
        ctx = self._make_context(embedding_used=True)
        assert ctx.embedding_used is True

    def test_query_stored(self) -> None:
        q = make_query(query_text="specific query")
        ctx = self._make_context(query=q)
        assert ctx.query.query_text == "specific query"

    def test_intra_edges_filters_edges_between_result_nodes(self) -> None:
        node_a = make_node()
        node_b = make_node()
        node_c = make_node()  # not in result set

        sn_a = make_scored_node(node=node_a)
        sn_b = make_scored_node(node=node_b)

        # edge between a and b — should be included
        edge_ab = make_edge(source_id=node_a.id, target_id=node_b.id)
        # edge from a to c (outside result) — should be excluded
        edge_ac = make_edge(source_id=node_a.id, target_id=node_c.id)

        ctx = self._make_context(
            nodes=[sn_a, sn_b],
            edges=[edge_ab, edge_ac],
        )
        intra = ctx.intra_edges()
        assert edge_ab in intra
        assert edge_ac not in intra

    def test_intra_edges_empty_when_no_edges(self) -> None:
        ctx = self._make_context(nodes=[make_scored_node()])
        assert ctx.intra_edges() == []

    def test_intra_edges_empty_when_no_nodes(self) -> None:
        edge = make_edge()
        ctx = self._make_context(nodes=[], edges=[edge])
        assert ctx.intra_edges() == []

    def test_intra_edges_all_included_when_all_endpoints_in_result(self) -> None:
        node_a = make_node()
        node_b = make_node()
        sn_a = make_scored_node(node=node_a)
        sn_b = make_scored_node(node=node_b)
        edge = make_edge(source_id=node_a.id, target_id=node_b.id)
        ctx = self._make_context(nodes=[sn_a, sn_b], edges=[edge])
        assert ctx.intra_edges() == [edge]

    def test_node_count_zero_on_empty(self) -> None:
        ctx = self._make_context()
        assert ctx.node_count == 0

    def test_edge_count_zero_on_empty(self) -> None:
        ctx = self._make_context()
        assert ctx.edge_count == 0
