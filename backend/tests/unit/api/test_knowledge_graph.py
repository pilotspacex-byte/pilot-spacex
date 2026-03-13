"""Unit tests for the Knowledge Graph REST API handler functions.

Tests cover hybrid search, neighbor traversal, subgraph extraction,
user context, and the issue-scoped endpoint with GitHub synthesis.

Router-level tests mock KnowledgeGraphQueryService (injected via kg_service param)
for endpoints that use DI. Search endpoint still patches KnowledgeGraphRepository
directly since it constructs the service internally (embedding key lookup).

Feature 016: Knowledge Graph — Unit 7 REST API
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from pilot_space.api.v1.routers.knowledge_graph import (
    _EDGE_LABELS,
    _edge_to_dto,
    _node_to_dto,
    get_issue_knowledge_graph,
    get_node_neighbors,
    get_subgraph,
    get_user_context,
    search_knowledge_graph,
)
from pilot_space.api.v1.schemas.knowledge_graph import GraphResponse
from pilot_space.application.services.memory.knowledge_graph_query_service import (
    EntityNotFoundError,
    EntitySubgraphResult,
    NeighborResult,
    RootNodeNotFoundError,
    SubgraphResult,
    UserContextResult,
)
from pilot_space.domain.graph_edge import EdgeType, GraphEdge
from tests.fixtures.knowledge_graph import (
    RLS_PATCH as _RLS_PATCH,
    make_ephemeral_node as _make_ephemeral_node,
    make_graph_edge as _make_graph_edge,
    make_graph_node as _make_graph_node,
    make_kg_repo as _make_repo,
    make_kg_service as _make_kg_service,
    make_session as _make_session,
)

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Fixed test identifiers
# ---------------------------------------------------------------------------

TEST_USER_ID = UUID("aaaaaaaa-0000-0000-0000-000000000001")
TEST_WORKSPACE_ID = UUID("bbbbbbbb-0000-0000-0000-000000000002")
TEST_NODE_ID = UUID("cccccccc-0000-0000-0000-000000000003")
TEST_ISSUE_ID = UUID("dddddddd-0000-0000-0000-000000000004")

# ---------------------------------------------------------------------------
# Helper factories (test-specific)
# ---------------------------------------------------------------------------


def _make_scored_node(score: float = 0.9, **kwargs: Any) -> MagicMock:
    """Build a mock ScoredNode."""
    scored = MagicMock()
    scored.node = _make_graph_node(**kwargs)
    scored.score = score
    return scored


# ---------------------------------------------------------------------------
# Test: _node_to_dto helper
# ---------------------------------------------------------------------------


class TestNodeToDto:
    """Unit tests for the _node_to_dto mapping helper."""

    def test_maps_node_fields_correctly(self) -> None:
        """GraphNode domain object is correctly mapped to GraphNodeDTO."""
        node = _make_graph_node(node_id=TEST_NODE_ID, label="PS-1", content="Bug fix")
        dto = _node_to_dto(node, score=0.9)

        assert dto.id == str(TEST_NODE_ID)
        assert dto.node_type == "issue"
        assert dto.label == "PS-1"
        assert dto.summary == "Bug fix"
        assert dto.score == 0.9

    def test_maps_updated_at_from_node(self) -> None:
        """updated_at is propagated from the domain node to the DTO."""
        fixed_ts = datetime(2025, 6, 1, 12, 0, 0, tzinfo=UTC)
        node = _make_graph_node()
        node.updated_at = fixed_ts
        dto = _node_to_dto(node)

        assert dto.updated_at == fixed_ts

    def test_truncates_summary_at_120_chars(self) -> None:
        """Content longer than 120 chars is truncated for summary."""
        long_content = "x" * 200
        node = _make_graph_node(content=long_content)
        dto = _node_to_dto(node)

        assert dto.summary is not None
        assert len(dto.summary) == 120

    def test_none_score_when_not_provided(self) -> None:
        """score defaults to None when not passed."""
        node = _make_graph_node()
        dto = _node_to_dto(node)
        assert dto.score is None


class TestEdgeToDto:
    """Unit tests for the _edge_to_dto mapping helper."""

    def test_known_edge_type_uses_human_readable_label(self) -> None:
        """A known edge_type maps to its human-readable label via _EDGE_LABELS."""
        edge = GraphEdge(
            source_id=uuid4(), target_id=uuid4(), edge_type=EdgeType.RELATES_TO, weight=0.8
        )
        dto = _edge_to_dto(edge)
        assert dto.label == "related to"
        assert dto.edge_type == "relates_to"

    def test_unknown_edge_type_falls_back_to_raw_value(self) -> None:
        """An unrecognised edge_type string falls back to the raw value."""
        edge = GraphEdge(
            source_id=uuid4(), target_id=uuid4(), edge_type=EdgeType.RELATES_TO, weight=0.5
        )
        import pilot_space.api.v1.routers.knowledge_graph as kg_module

        original = kg_module._EDGE_LABELS.copy()
        del kg_module._EDGE_LABELS[EdgeType.RELATES_TO]
        try:
            dto = _edge_to_dto(edge)
            assert dto.label == "relates_to"
        finally:
            kg_module._EDGE_LABELS.update(original)

    def test_all_known_edge_labels_present(self) -> None:
        """Every entry in _EDGE_LABELS round-trips through _edge_to_dto correctly."""
        for edge_type, expected_label in _EDGE_LABELS.items():
            edge = GraphEdge(source_id=uuid4(), target_id=uuid4(), edge_type=edge_type, weight=1.0)
            dto = _edge_to_dto(edge)
            assert dto.label == expected_label, f"Failed for edge_type={edge_type}"


# ---------------------------------------------------------------------------
# Test: search_knowledge_graph
# ---------------------------------------------------------------------------


class TestSearchKnowledgeGraph:
    """GET /workspaces/{workspace_id}/knowledge-graph/search"""

    async def test_search_returns_graph_response(self) -> None:
        """Valid search query returns a GraphResponse with nodes."""
        scored = [_make_scored_node(score=0.95, label="PS-1")]
        repo = _make_repo(hybrid_search=AsyncMock(return_value=scored))
        session = _make_session()

        with (
            patch(_RLS_PATCH, new_callable=AsyncMock),
            patch(
                "pilot_space.api.v1.routers.knowledge_graph.KnowledgeGraphRepository",
                return_value=repo,
            ),
        ):
            result = await search_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                q="auth bug",
                node_types=None,
                limit=10,
            )

        assert isinstance(result, GraphResponse)
        assert len(result.nodes) == 1
        assert result.nodes[0].node_type == "issue"
        assert result.nodes[0].score is not None

    async def test_search_with_node_type_filter(self) -> None:
        """node_types param is forwarded as parsed NodeType list to the repo."""
        from pilot_space.domain.graph_node import NodeType

        scored = [_make_scored_node(node_type="note", label="Meeting notes")]
        repo = _make_repo(hybrid_search=AsyncMock(return_value=scored))
        session = _make_session()

        with (
            patch(_RLS_PATCH, new_callable=AsyncMock),
            patch(
                "pilot_space.api.v1.routers.knowledge_graph.KnowledgeGraphRepository",
                return_value=repo,
            ),
        ):
            result = await search_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                q="notes",
                node_types="note",
                limit=10,
            )

        assert isinstance(result, GraphResponse)
        call_kwargs = repo.hybrid_search.call_args.kwargs
        assert call_kwargs["node_types"] == [NodeType.NOTE]

    async def test_search_calls_rls_context(self) -> None:
        """set_rls_context is called before querying."""
        repo = _make_repo()
        session = _make_session()

        with (
            patch(_RLS_PATCH, new_callable=AsyncMock) as mock_rls,
            patch(
                "pilot_space.api.v1.routers.knowledge_graph.KnowledgeGraphRepository",
                return_value=repo,
            ),
        ):
            await search_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                q="test",
                node_types=None,
                limit=10,
            )

        mock_rls.assert_awaited_once_with(session, TEST_USER_ID, TEST_WORKSPACE_ID)

    async def test_search_raises_422_on_invalid_node_type(self) -> None:
        """Invalid node_type value raises HTTPException with status 422."""
        repo = _make_repo()
        session = _make_session()

        with (
            patch(_RLS_PATCH, new_callable=AsyncMock),
            patch(
                "pilot_space.api.v1.routers.knowledge_graph.KnowledgeGraphRepository",
                return_value=repo,
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await search_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                q="test",
                node_types="not_a_valid_type",
                limit=10,
            )

        assert exc_info.value.status_code == 422
        assert "Invalid node_type" in exc_info.value.detail


# ---------------------------------------------------------------------------
# Test: get_node_neighbors
# ---------------------------------------------------------------------------


class TestGetNodeNeighbors:
    """GET /workspaces/{workspace_id}/knowledge-graph/nodes/{node_id}/neighbors"""

    async def test_neighbors_returns_subgraph(self) -> None:
        """Valid node_id returns GraphResponse with center node + neighbor nodes."""
        center_node = _make_graph_node(node_id=TEST_NODE_ID, label="Center issue")
        neighbor = _make_graph_node(label="Neighbor note", node_type="note")

        kg_service = _make_kg_service()
        kg_service.get_neighbors.return_value = NeighborResult(
            nodes=[center_node, neighbor], edges=[], center_node_id=TEST_NODE_ID
        )
        session = _make_session()

        with patch(_RLS_PATCH, new_callable=AsyncMock):
            result = await get_node_neighbors(
                workspace_id=TEST_WORKSPACE_ID,
                node_id=TEST_NODE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                kg_service=kg_service,
                depth=1,
                edge_types=None,
            )

        assert isinstance(result, GraphResponse)
        assert len(result.nodes) == 2
        assert result.center_node_id == TEST_NODE_ID
        node_types = {str(n.node_type) for n in result.nodes}
        assert "note" in node_types
        assert "issue" in node_types

    async def test_neighbors_passes_edge_type_filter(self) -> None:
        """edge_types param is parsed and forwarded to the service."""
        kg_service = _make_kg_service()
        kg_service.get_neighbors.return_value = NeighborResult(
            nodes=[], edges=[], center_node_id=TEST_NODE_ID
        )
        session = _make_session()

        with patch(_RLS_PATCH, new_callable=AsyncMock):
            await get_node_neighbors(
                workspace_id=TEST_WORKSPACE_ID,
                node_id=TEST_NODE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                kg_service=kg_service,
                depth=1,
                edge_types="relates_to",
            )

        call_kwargs = kg_service.get_neighbors.call_args.kwargs
        assert call_kwargs["edge_types"] == [EdgeType.RELATES_TO]

    async def test_neighbors_raises_422_on_invalid_edge_type(self) -> None:
        """Invalid edge_type value raises HTTPException with status 422."""
        kg_service = _make_kg_service()
        session = _make_session()

        with (
            patch(_RLS_PATCH, new_callable=AsyncMock),
            pytest.raises(HTTPException) as exc_info,
        ):
            await get_node_neighbors(
                workspace_id=TEST_WORKSPACE_ID,
                node_id=TEST_NODE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                kg_service=kg_service,
                depth=1,
                edge_types="totally_invalid_edge",
            )

        assert exc_info.value.status_code == 422
        assert "Invalid edge_type" in exc_info.value.detail


# ---------------------------------------------------------------------------
# Test: get_subgraph
# ---------------------------------------------------------------------------


class TestGetSubgraph:
    """GET /workspaces/{workspace_id}/knowledge-graph/subgraph"""

    async def test_subgraph_returns_nodes_and_edges(self) -> None:
        """Subgraph extraction returns nodes + edges with center_node_id."""
        node1 = _make_graph_node(node_id=TEST_NODE_ID, label="Root issue")
        node2 = _make_graph_node(label="Related note", node_type="note")
        edge = _make_graph_edge(source_id=TEST_NODE_ID, target_id=node2.id)

        kg_service = _make_kg_service()
        kg_service.get_subgraph.return_value = SubgraphResult(
            nodes=[node1, node2], edges=[edge], center_node_id=TEST_NODE_ID
        )
        session = _make_session()

        with patch(_RLS_PATCH, new_callable=AsyncMock):
            result = await get_subgraph(
                workspace_id=TEST_WORKSPACE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                kg_service=kg_service,
                root_id=TEST_NODE_ID,
                max_depth=2,
                max_nodes=50,
            )

        assert isinstance(result, GraphResponse)
        assert len(result.nodes) == 2
        assert len(result.edges) == 1
        assert result.center_node_id == TEST_NODE_ID
        assert result.edges[0].edge_type == "relates_to"

    async def test_subgraph_returns_404_when_root_not_found(self) -> None:
        """RootNodeNotFoundError from service is translated to 404."""
        kg_service = _make_kg_service()
        kg_service.get_subgraph.side_effect = RootNodeNotFoundError(TEST_NODE_ID)
        session = _make_session()

        with (
            patch(_RLS_PATCH, new_callable=AsyncMock),
            pytest.raises(HTTPException) as exc_info,
        ):
            await get_subgraph(
                workspace_id=TEST_WORKSPACE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                kg_service=kg_service,
                root_id=TEST_NODE_ID,
                max_depth=2,
                max_nodes=50,
            )

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Test: get_user_context
# ---------------------------------------------------------------------------


class TestGetUserContext:
    """GET /workspaces/{workspace_id}/knowledge-graph/user-context"""

    async def test_user_context_returns_personal_nodes(self) -> None:
        """User context endpoint returns nodes scoped to the current user."""
        personal_nodes = [
            _make_graph_node(node_type="user_preference", label="My preferences"),
            _make_graph_node(node_type="learned_pattern", label="PR workflow"),
        ]

        kg_service = _make_kg_service()
        kg_service.get_user_context.return_value = UserContextResult(nodes=personal_nodes)
        session = _make_session()

        with patch(_RLS_PATCH, new_callable=AsyncMock):
            result = await get_user_context(
                workspace_id=TEST_WORKSPACE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                kg_service=kg_service,
                limit=10,
            )

        assert isinstance(result, GraphResponse)
        assert len(result.nodes) == 2
        node_types = {n.node_type for n in result.nodes}
        assert "user_preference" in node_types
        assert "learned_pattern" in node_types

    async def test_user_context_passes_user_id_to_service(self) -> None:
        """get_user_context service call receives the correct params."""
        kg_service = _make_kg_service()
        kg_service.get_user_context.return_value = UserContextResult(nodes=[])
        session = _make_session()

        with patch(_RLS_PATCH, new_callable=AsyncMock):
            await get_user_context(
                workspace_id=TEST_WORKSPACE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                kg_service=kg_service,
                limit=5,
            )

        call_kwargs = kg_service.get_user_context.call_args.kwargs
        assert call_kwargs["user_id"] == TEST_USER_ID
        assert call_kwargs["workspace_id"] == TEST_WORKSPACE_ID
        assert call_kwargs["limit"] == 5


# ---------------------------------------------------------------------------
# Test: get_issue_knowledge_graph
# ---------------------------------------------------------------------------


class TestIssueKnowledgeGraph:
    """GET /workspaces/{workspace_id}/issues/{issue_id}/knowledge-graph"""

    async def test_issue_graph_returns_404_when_issue_not_found(self) -> None:
        """EntityNotFoundError from service is translated to 404."""
        kg_service = _make_kg_service()
        kg_service.get_issue_knowledge_graph.side_effect = EntityNotFoundError(
            "Issue", TEST_ISSUE_ID
        )
        session = _make_session()

        with (
            patch(_RLS_PATCH, new_callable=AsyncMock),
            pytest.raises(HTTPException) as exc_info,
        ):
            await get_issue_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                issue_id=TEST_ISSUE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                kg_service=kg_service,
                depth=2,
                node_types=None,
                max_nodes=50,
                include_github=False,
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Issue not found"

    async def test_issue_graph_returns_empty_when_no_graph_node(self) -> None:
        """Issue exists but has no graph node — empty response."""
        kg_service = _make_kg_service()
        kg_service.get_issue_knowledge_graph.return_value = EntitySubgraphResult(
            nodes=[], edges=[], ephemeral_nodes=[], center_node_id=None
        )
        session = _make_session()

        with patch(_RLS_PATCH, new_callable=AsyncMock):
            result = await get_issue_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                issue_id=TEST_ISSUE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                kg_service=kg_service,
                depth=2,
                node_types=None,
                max_nodes=50,
                include_github=False,
            )

        assert isinstance(result, GraphResponse)
        assert result.nodes == []
        assert result.edges == []
        assert result.center_node_id is None

    async def test_issue_graph_synthesizes_github_nodes(self) -> None:
        """include_github=true with integration links appends ephemeral PR nodes."""
        graph_node = _make_graph_node(node_id=TEST_NODE_ID, label="PS-1")
        ephemeral = _make_ephemeral_node()

        kg_service = _make_kg_service()
        kg_service.get_issue_knowledge_graph.return_value = EntitySubgraphResult(
            nodes=[graph_node],
            edges=[],
            ephemeral_nodes=[ephemeral],
            center_node_id=TEST_NODE_ID,
        )
        session = _make_session()

        with patch(_RLS_PATCH, new_callable=AsyncMock):
            result = await get_issue_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                issue_id=TEST_ISSUE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                kg_service=kg_service,
                depth=2,
                node_types=None,
                max_nodes=50,
                include_github=True,
            )

        assert isinstance(result, GraphResponse)
        assert len(result.nodes) >= 2
        node_types = [n.node_type for n in result.nodes]
        assert "pull_request" in node_types
        gh_nodes = [n for n in result.nodes if n.node_type == "pull_request"]
        assert gh_nodes[0].properties.get("ephemeral") is True
        call_kwargs = kg_service.get_issue_knowledge_graph.call_args.kwargs
        assert call_kwargs["include_github"] is True

    async def test_issue_graph_applies_node_type_filter(self) -> None:
        """node_types param is forwarded to the service."""
        issue_node = _make_graph_node(node_type="issue", label="PS-1")

        kg_service = _make_kg_service()
        kg_service.get_issue_knowledge_graph.return_value = EntitySubgraphResult(
            nodes=[issue_node],
            edges=[],
            ephemeral_nodes=[],
            center_node_id=TEST_NODE_ID,
        )
        session = _make_session()

        with patch(_RLS_PATCH, new_callable=AsyncMock):
            result = await get_issue_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                issue_id=TEST_ISSUE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                kg_service=kg_service,
                depth=2,
                node_types="issue",
                max_nodes=50,
                include_github=False,
            )

        assert all(n.node_type == "issue" for n in result.nodes)
        call_kwargs = kg_service.get_issue_knowledge_graph.call_args.kwargs
        assert call_kwargs["node_types"] == "issue"

    async def test_issue_graph_rejects_invalid_node_types(self) -> None:
        """Invalid node_types value raises HTTPException with status 422."""
        kg_service = _make_kg_service()
        session = _make_session()

        with (
            patch(_RLS_PATCH, new_callable=AsyncMock),
            pytest.raises(HTTPException) as exc_info,
        ):
            await get_issue_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                issue_id=TEST_ISSUE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                kg_service=kg_service,
                depth=2,
                node_types="not_a_valid_type",
                max_nodes=50,
                include_github=False,
            )

        assert exc_info.value.status_code == 422
        assert "Invalid node_type" in exc_info.value.detail

    async def test_issue_graph_sorts_by_importance_tier(self) -> None:
        """Service returns sorted nodes; verify order preserved in response."""
        issue_node = _make_graph_node(node_type="issue", label="Issue")
        pr_node = _make_graph_node(node_type="pull_request", label="PR")
        skill_node = _make_graph_node(node_type="skill_outcome", label="Skill")

        kg_service = _make_kg_service()
        kg_service.get_issue_knowledge_graph.return_value = EntitySubgraphResult(
            nodes=[issue_node, pr_node, skill_node],
            edges=[],
            ephemeral_nodes=[],
            center_node_id=TEST_NODE_ID,
        )
        session = _make_session()

        with patch(_RLS_PATCH, new_callable=AsyncMock):
            result = await get_issue_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                issue_id=TEST_ISSUE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                kg_service=kg_service,
                depth=2,
                node_types=None,
                max_nodes=50,
                include_github=False,
            )

        assert result.nodes[0].node_type == "issue"
        assert result.nodes[-1].node_type == "skill_outcome"

    async def test_issue_graph_include_github_false_skips_link_query(self) -> None:
        """include_github=False is forwarded to the service."""
        graph_node = _make_graph_node(node_id=TEST_NODE_ID, label="PS-1")

        kg_service = _make_kg_service()
        kg_service.get_issue_knowledge_graph.return_value = EntitySubgraphResult(
            nodes=[graph_node],
            edges=[],
            ephemeral_nodes=[],
            center_node_id=TEST_NODE_ID,
        )
        session = _make_session()

        with patch(_RLS_PATCH, new_callable=AsyncMock):
            result = await get_issue_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                issue_id=TEST_ISSUE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                kg_service=kg_service,
                depth=2,
                node_types=None,
                max_nodes=50,
                include_github=False,
            )

        assert len(result.nodes) == 1
        call_kwargs = kg_service.get_issue_knowledge_graph.call_args.kwargs
        assert call_kwargs["include_github"] is False

    async def test_issue_graph_edges_from_subgraph_included_in_response(self) -> None:
        """Edges returned by service are included in the response."""
        node_a = _make_graph_node(node_id=TEST_NODE_ID, label="Issue A")
        node_b_id = uuid4()
        node_b = _make_graph_node(node_id=node_b_id, node_type="note", label="Note B")
        edge = _make_graph_edge(source_id=TEST_NODE_ID, target_id=node_b_id)

        kg_service = _make_kg_service()
        kg_service.get_issue_knowledge_graph.return_value = EntitySubgraphResult(
            nodes=[node_a, node_b],
            edges=[edge],
            ephemeral_nodes=[],
            center_node_id=TEST_NODE_ID,
        )
        session = _make_session()

        with patch(_RLS_PATCH, new_callable=AsyncMock):
            result = await get_issue_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                issue_id=TEST_ISSUE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                kg_service=kg_service,
                depth=2,
                node_types=None,
                max_nodes=50,
                include_github=False,
            )

        assert len(result.nodes) == 2
        assert len(result.edges) == 1
        assert result.edges[0].source_id == str(TEST_NODE_ID)
        assert result.edges[0].target_id == str(node_b_id)

    async def test_issue_graph_depth_and_max_nodes_forwarded_to_service(self) -> None:
        """depth and max_nodes are forwarded to the service."""
        kg_service = _make_kg_service()
        kg_service.get_issue_knowledge_graph.return_value = EntitySubgraphResult(
            nodes=[], edges=[], ephemeral_nodes=[], center_node_id=None
        )
        session = _make_session()

        with patch(_RLS_PATCH, new_callable=AsyncMock):
            await get_issue_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                issue_id=TEST_ISSUE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                kg_service=kg_service,
                depth=3,
                node_types=None,
                max_nodes=25,
                include_github=False,
            )

        call_kwargs = kg_service.get_issue_knowledge_graph.call_args.kwargs
        assert call_kwargs["depth"] == 3
        assert call_kwargs["max_nodes"] == 25

    async def test_issue_graph_deduplicates_github_node_already_in_graph(self) -> None:
        """No ephemeral node when service returns empty ephemeral list (dedup in service)."""
        graph_node = _make_graph_node(node_id=TEST_NODE_ID, node_type="pull_request", label="PR")

        kg_service = _make_kg_service()
        kg_service.get_issue_knowledge_graph.return_value = EntitySubgraphResult(
            nodes=[graph_node],
            edges=[],
            ephemeral_nodes=[],  # Service already deduped
            center_node_id=TEST_NODE_ID,
        )
        session = _make_session()

        with patch(_RLS_PATCH, new_callable=AsyncMock):
            result = await get_issue_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                issue_id=TEST_ISSUE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                kg_service=kg_service,
                depth=2,
                node_types=None,
                max_nodes=50,
                include_github=True,
            )

        pr_nodes = [n for n in result.nodes if n.node_type == "pull_request"]
        assert len(pr_nodes) == 1
        assert pr_nodes[0].properties.get("ephemeral") is not True

    async def test_issue_graph_all_github_link_types_mapped(self) -> None:
        """Ephemeral nodes for all GitHub link types appear in response."""
        kg_service = _make_kg_service()
        kg_service.get_issue_knowledge_graph.return_value = EntitySubgraphResult(
            nodes=[],
            edges=[],
            ephemeral_nodes=[
                _make_ephemeral_node(node_type="branch", label="feat/login", external_id="b1"),
                _make_ephemeral_node(node_type="commit", label="abc123", external_id="c1"),
                _make_ephemeral_node(node_type="note", label="related note", external_id="m1"),
            ],
            center_node_id=TEST_NODE_ID,
        )
        session = _make_session()

        with patch(_RLS_PATCH, new_callable=AsyncMock):
            result = await get_issue_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                issue_id=TEST_ISSUE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                kg_service=kg_service,
                depth=2,
                node_types=None,
                max_nodes=50,
                include_github=True,
            )

        node_types_in_result = {n.node_type for n in result.nodes}
        assert "branch" in node_types_in_result
        assert "commit" in node_types_in_result
        assert "note" in node_types_in_result
        assert all(n.properties.get("ephemeral") is True for n in result.nodes)

    async def test_issue_graph_center_node_id_is_graph_node_not_issue(self) -> None:
        """center_node_id in response is the graph node id, not the issue id."""
        kg_service = _make_kg_service()
        kg_service.get_issue_knowledge_graph.return_value = EntitySubgraphResult(
            nodes=[], edges=[], ephemeral_nodes=[], center_node_id=TEST_NODE_ID
        )
        session = _make_session()

        with patch(_RLS_PATCH, new_callable=AsyncMock):
            result = await get_issue_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                issue_id=TEST_ISSUE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                kg_service=kg_service,
                depth=2,
                node_types=None,
                max_nodes=50,
                include_github=False,
            )

        assert result.center_node_id == TEST_NODE_ID
        assert result.center_node_id != TEST_ISSUE_ID
