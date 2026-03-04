"""Unit tests for the Knowledge Graph REST API handler functions.

Tests cover hybrid search, neighbor traversal, subgraph extraction,
user context, and the issue-scoped endpoint with GitHub synthesis.

Each test calls the handler function directly with mocked dependencies,
following the established pattern in this codebase (see test_ai_drive.py).

Feature 016: Knowledge Graph — Unit 7 REST API
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

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

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Fixed test identifiers
# ---------------------------------------------------------------------------

TEST_USER_ID = UUID("aaaaaaaa-0000-0000-0000-000000000001")
TEST_WORKSPACE_ID = UUID("bbbbbbbb-0000-0000-0000-000000000002")
TEST_NODE_ID = UUID("cccccccc-0000-0000-0000-000000000003")
TEST_ISSUE_ID = UUID("dddddddd-0000-0000-0000-000000000004")

# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _make_graph_node(
    node_id: UUID | None = None,
    node_type: str = "issue",
    label: str = "Test Issue",
    content: str = "",
) -> MagicMock:
    """Build a mock GraphNode domain object."""
    from pilot_space.domain.graph_node import NodeType

    node = MagicMock()
    node.id = node_id or uuid4()
    node.node_type = NodeType(node_type)
    node.label = label
    _content = content or f"Content for {label}"
    node.content = _content
    node.summary = _content[:120]
    node.properties = {"state": "todo"}
    node.created_at = datetime.now(tz=UTC)
    node.updated_at = datetime.now(tz=UTC)
    return node


def _make_scored_node(score: float = 0.9, **kwargs: Any) -> MagicMock:
    """Build a mock ScoredNode."""
    scored = MagicMock()
    scored.node = _make_graph_node(**kwargs)
    scored.score = score
    return scored


def _make_graph_edge(
    source_id: UUID | None = None,
    target_id: UUID | None = None,
    edge_type: str = "relates_to",
) -> MagicMock:
    """Build a mock GraphEdge domain object."""
    from pilot_space.domain.graph_edge import EdgeType

    edge = MagicMock()
    edge.id = uuid4()
    edge.source_id = source_id or uuid4()
    edge.target_id = target_id or uuid4()
    edge.edge_type = EdgeType(edge_type)
    edge.weight = 0.8
    edge.properties = {}
    return edge


def _make_integration_link_mock(
    link_type: str = "pull_request",
    title: str = "feat: add something",
    external_id: str = "123",
) -> MagicMock:
    """Build a mock IntegrationLink model."""
    from pilot_space.infrastructure.database.models.integration import IntegrationLinkType

    link = MagicMock()
    link.issue_id = TEST_ISSUE_ID
    link.workspace_id = TEST_WORKSPACE_ID
    link.link_type = IntegrationLinkType(link_type)
    link.title = title
    link.external_id = external_id
    link.external_url = f"https://github.com/repo/pull/{external_id}"
    link.author_name = "dev"
    link.is_deleted = False
    return link


def _make_repo(**kwargs: Any) -> AsyncMock:
    """Build a mock KnowledgeGraphRepository."""
    repo = AsyncMock()
    repo.hybrid_search = AsyncMock(return_value=[])
    repo.get_neighbors = AsyncMock(return_value=[])
    repo.get_subgraph = AsyncMock(return_value=([], []))
    repo.get_user_context = AsyncMock(return_value=[])
    for key, value in kwargs.items():
        setattr(repo, key, value)
    return repo


def _make_session(scalar_result: Any = None, scalars_all: Any = None) -> AsyncMock:
    """Build a mock AsyncSession."""
    session = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalar_one_or_none = MagicMock(return_value=scalar_result)
    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=scalars_all or [])
    execute_result.scalars = MagicMock(return_value=scalars_mock)
    session.execute = AsyncMock(return_value=execute_result)
    return session


def _make_sequential_session(*responses: Any) -> AsyncMock:
    """Build a mock AsyncSession that returns different results on successive execute calls.

    Each item in ``responses`` is a dict with optional keys:
      - ``scalar``: value returned by ``scalar_one_or_none()``
      - ``scalars_all``: list returned by ``scalars().all()``

    Example::

        session = _make_sequential_session(
            {"scalar": issue_id},  # call 0: issue existence check
            {"scalar": gn_model},  # call 1: graph node lookup
            {"scalars_all": [pr_link]},  # call 2: integration links
        )
    """
    call_index = 0

    async def _execute(stmt: Any, *args: Any, **kwargs: Any) -> Any:
        nonlocal call_index
        idx = min(call_index, len(responses) - 1)
        call_index += 1
        spec = responses[idx]
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=spec.get("scalar"))
        scalars_mock = MagicMock()
        scalars_mock.all = MagicMock(return_value=spec.get("scalars_all") or [])
        result.scalars = MagicMock(return_value=scalars_mock)
        return result

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=_execute)
    return session


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
        dto = _edge_to_dto(
            edge_id=uuid4(),
            source_id=uuid4(),
            target_id=uuid4(),
            edge_type="relates_to",
            weight=0.8,
            properties={},
        )
        assert dto.label == "related to"
        assert dto.edge_type == "relates_to"

    def test_unknown_edge_type_falls_back_to_raw_value(self) -> None:
        """An unrecognised edge_type falls back to the raw enum string."""
        dto = _edge_to_dto(
            edge_id=uuid4(),
            source_id=uuid4(),
            target_id=uuid4(),
            edge_type="custom_edge",
            weight=0.5,
            properties={},
        )
        assert dto.label == "custom_edge"

    def test_all_known_edge_labels_present(self) -> None:
        """Every entry in _EDGE_LABELS round-trips through _edge_to_dto correctly."""
        for edge_type, expected_label in _EDGE_LABELS.items():
            dto = _edge_to_dto(
                edge_id=uuid4(),
                source_id=uuid4(),
                target_id=uuid4(),
                edge_type=edge_type.value,
                weight=1.0,
                properties={},
            )
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

        with MagicMock() as mock_rls:
            from unittest.mock import patch

            with (
                patch(
                    "pilot_space.api.v1.routers.knowledge_graph.set_rls_context",
                    new_callable=AsyncMock,
                ) as mock_rls_fn,
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
        # Score is recomputed by GraphSearchService._rerank from sub-components;
        # exact value is tested in graph_search_service tests.
        assert result.nodes[0].score is not None

    async def test_search_with_node_type_filter(self) -> None:
        """node_types param is forwarded as parsed NodeType list to the repo."""
        from unittest.mock import patch

        from pilot_space.domain.graph_node import NodeType

        scored = [_make_scored_node(node_type="note", label="Meeting notes")]
        repo = _make_repo(hybrid_search=AsyncMock(return_value=scored))
        session = _make_session()

        with (
            patch(
                "pilot_space.api.v1.routers.knowledge_graph.set_rls_context",
                new_callable=AsyncMock,
            ),
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
        from unittest.mock import patch

        repo = _make_repo()
        session = _make_session()

        with (
            patch(
                "pilot_space.api.v1.routers.knowledge_graph.set_rls_context",
                new_callable=AsyncMock,
            ) as mock_rls,
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
        from unittest.mock import patch

        from fastapi import HTTPException

        repo = _make_repo()
        session = _make_session()

        with (
            patch(
                "pilot_space.api.v1.routers.knowledge_graph.set_rls_context",
                new_callable=AsyncMock,
            ),
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
        """Valid node_id returns GraphResponse with neighbor nodes."""
        from unittest.mock import patch

        neighbors = [_make_graph_node(label="Neighbor note", node_type="note")]
        repo = _make_repo(get_neighbors=AsyncMock(return_value=neighbors))
        session = _make_session()

        with (
            patch(
                "pilot_space.api.v1.routers.knowledge_graph.set_rls_context",
                new_callable=AsyncMock,
            ),
            patch(
                "pilot_space.api.v1.routers.knowledge_graph.KnowledgeGraphRepository",
                return_value=repo,
            ),
        ):
            result = await get_node_neighbors(
                workspace_id=TEST_WORKSPACE_ID,
                node_id=TEST_NODE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                depth=1,
                edge_types=None,
            )

        assert isinstance(result, GraphResponse)
        assert len(result.nodes) == 1
        assert result.center_node_id == TEST_NODE_ID
        assert result.nodes[0].node_type == "note"

    async def test_neighbors_passes_edge_type_filter(self) -> None:
        """edge_types param is forwarded to repo as EdgeType list."""
        from unittest.mock import patch

        from pilot_space.domain.graph_edge import EdgeType

        repo = _make_repo(get_neighbors=AsyncMock(return_value=[]))
        session = _make_session()

        with (
            patch(
                "pilot_space.api.v1.routers.knowledge_graph.set_rls_context",
                new_callable=AsyncMock,
            ),
            patch(
                "pilot_space.api.v1.routers.knowledge_graph.KnowledgeGraphRepository",
                return_value=repo,
            ),
        ):
            await get_node_neighbors(
                workspace_id=TEST_WORKSPACE_ID,
                node_id=TEST_NODE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                depth=1,
                edge_types="relates_to",
            )

        call_kwargs = repo.get_neighbors.call_args.kwargs
        assert call_kwargs["edge_types"] == [EdgeType.RELATES_TO]

    async def test_neighbors_raises_422_on_invalid_edge_type(self) -> None:
        """Invalid edge_type value raises HTTPException with status 422."""
        from unittest.mock import patch

        from fastapi import HTTPException

        repo = _make_repo()
        session = _make_session()

        with (
            patch(
                "pilot_space.api.v1.routers.knowledge_graph.set_rls_context",
                new_callable=AsyncMock,
            ),
            patch(
                "pilot_space.api.v1.routers.knowledge_graph.KnowledgeGraphRepository",
                return_value=repo,
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await get_node_neighbors(
                workspace_id=TEST_WORKSPACE_ID,
                node_id=TEST_NODE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
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
        from unittest.mock import patch

        node1 = _make_graph_node(node_id=TEST_NODE_ID, label="Root issue")
        node2 = _make_graph_node(label="Related note", node_type="note")
        edge = _make_graph_edge(source_id=TEST_NODE_ID, target_id=node2.id)
        repo = _make_repo(get_subgraph=AsyncMock(return_value=([node1, node2], [edge])))
        session = _make_session()

        with (
            patch(
                "pilot_space.api.v1.routers.knowledge_graph.set_rls_context",
                new_callable=AsyncMock,
            ),
            patch(
                "pilot_space.api.v1.routers.knowledge_graph.KnowledgeGraphRepository",
                return_value=repo,
            ),
        ):
            result = await get_subgraph(
                workspace_id=TEST_WORKSPACE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                root_id=TEST_NODE_ID,
                max_depth=2,
                max_nodes=50,
            )

        assert isinstance(result, GraphResponse)
        assert len(result.nodes) == 2
        assert len(result.edges) == 1
        assert result.center_node_id == TEST_NODE_ID
        assert result.edges[0].edge_type == "relates_to"


# ---------------------------------------------------------------------------
# Test: get_user_context
# ---------------------------------------------------------------------------


class TestGetUserContext:
    """GET /workspaces/{workspace_id}/knowledge-graph/user-context"""

    async def test_user_context_returns_personal_nodes(self) -> None:
        """User context endpoint returns nodes scoped to the current user."""
        from unittest.mock import patch

        personal_nodes = [
            _make_graph_node(node_type="user_preference", label="My preferences"),
            _make_graph_node(node_type="learned_pattern", label="PR workflow"),
        ]
        repo = _make_repo(get_user_context=AsyncMock(return_value=personal_nodes))
        session = _make_session()

        with (
            patch(
                "pilot_space.api.v1.routers.knowledge_graph.set_rls_context",
                new_callable=AsyncMock,
            ),
            patch(
                "pilot_space.api.v1.routers.knowledge_graph.KnowledgeGraphRepository",
                return_value=repo,
            ),
        ):
            result = await get_user_context(
                workspace_id=TEST_WORKSPACE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                limit=10,
            )

        assert isinstance(result, GraphResponse)
        assert len(result.nodes) == 2
        node_types = {n.node_type for n in result.nodes}
        assert "user_preference" in node_types
        assert "learned_pattern" in node_types

    async def test_user_context_passes_user_id_to_repo(self) -> None:
        """get_user_context repo call receives the correct user_id and workspace_id."""
        from unittest.mock import patch

        repo = _make_repo(get_user_context=AsyncMock(return_value=[]))
        session = _make_session()

        with (
            patch(
                "pilot_space.api.v1.routers.knowledge_graph.set_rls_context",
                new_callable=AsyncMock,
            ),
            patch(
                "pilot_space.api.v1.routers.knowledge_graph.KnowledgeGraphRepository",
                return_value=repo,
            ),
        ):
            await get_user_context(
                workspace_id=TEST_WORKSPACE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                limit=5,
            )

        call_kwargs = repo.get_user_context.call_args.kwargs
        assert call_kwargs["user_id"] == TEST_USER_ID
        assert call_kwargs["workspace_id"] == TEST_WORKSPACE_ID
        assert call_kwargs["limit"] == 5


# ---------------------------------------------------------------------------
# Test: get_issue_knowledge_graph
# ---------------------------------------------------------------------------


class TestIssueKnowledgeGraph:
    """GET /workspaces/{workspace_id}/issues/{issue_id}/knowledge-graph"""

    async def test_issue_graph_returns_404_when_issue_not_found(self) -> None:
        """Non-existent issue raises 404 before querying the graph (H-4)."""
        from unittest.mock import patch

        from fastapi import HTTPException

        # Session returns None → issue existence check fails → 404
        session = _make_session(scalar_result=None)
        repo = _make_repo(get_subgraph=AsyncMock(return_value=([], [])))

        with (
            patch(
                "pilot_space.api.v1.routers.knowledge_graph.set_rls_context",
                new_callable=AsyncMock,
            ),
            patch(
                "pilot_space.api.v1.routers.knowledge_graph.KnowledgeGraphRepository",
                return_value=repo,
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await get_issue_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                issue_id=TEST_ISSUE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                depth=2,
                node_types=None,
                max_nodes=50,
                include_github=False,
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Issue not found"
        repo.get_subgraph.assert_not_awaited()

    async def test_issue_graph_returns_empty_when_no_graph_node(self) -> None:
        """Issue exists but has no graph node → empty GraphResponse with center_node_id=issue_id."""
        from unittest.mock import patch

        # Call 0: issue existence check → found. Call 1: graph node lookup → not found.
        session = _make_sequential_session(
            {"scalar": TEST_ISSUE_ID},
            {"scalar": None},
        )
        repo = _make_repo(get_subgraph=AsyncMock(return_value=([], [])))

        with (
            patch(
                "pilot_space.api.v1.routers.knowledge_graph.set_rls_context",
                new_callable=AsyncMock,
            ),
            patch(
                "pilot_space.api.v1.routers.knowledge_graph.KnowledgeGraphRepository",
                return_value=repo,
            ),
        ):
            result = await get_issue_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                issue_id=TEST_ISSUE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                depth=2,
                node_types=None,
                max_nodes=50,
                include_github=False,
            )

        assert isinstance(result, GraphResponse)
        assert result.nodes == []
        assert result.edges == []
        assert result.center_node_id == TEST_ISSUE_ID
        # Subgraph is NOT called when no graph node found
        repo.get_subgraph.assert_not_awaited()

    async def test_issue_graph_synthesizes_github_nodes(self) -> None:
        """include_github=true with integration links appends ephemeral PR nodes."""
        from unittest.mock import patch

        # Mock graph node model
        gn_model = MagicMock()
        gn_model.id = TEST_NODE_ID
        gn_model.workspace_id = TEST_WORKSPACE_ID
        gn_model.node_type = "issue"
        gn_model.label = "PS-1"
        gn_model.content = "Fix the login bug"
        gn_model.properties = {}
        gn_model.created_at = datetime.now(tz=UTC)
        gn_model.updated_at = datetime.now(tz=UTC)
        gn_model.is_deleted = False
        gn_model.embedding = None
        gn_model.external_id = TEST_ISSUE_ID
        gn_model.user_id = None

        pr_link = _make_integration_link_mock(link_type="pull_request", title="feat: fix login #42")

        # Call 0: issue existence. Call 1: graph node lookup. Call 2: integration links.
        session = _make_sequential_session(
            {"scalar": TEST_ISSUE_ID},
            {"scalar": gn_model},
            {"scalars_all": [pr_link]},
        )

        graph_node = _make_graph_node(node_id=TEST_NODE_ID, label="PS-1")
        repo = _make_repo(get_subgraph=AsyncMock(return_value=([graph_node], [])))

        with (
            patch(
                "pilot_space.api.v1.routers.knowledge_graph.set_rls_context",
                new_callable=AsyncMock,
            ),
            patch(
                "pilot_space.api.v1.routers.knowledge_graph.KnowledgeGraphRepository",
                return_value=repo,
            ),
        ):
            result = await get_issue_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                issue_id=TEST_ISSUE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                depth=2,
                node_types=None,
                max_nodes=50,
                include_github=True,
            )

        assert isinstance(result, GraphResponse)
        # Original node + synthesized PR node
        assert len(result.nodes) >= 2
        node_types = [n.node_type for n in result.nodes]
        assert "pull_request" in node_types

        # Verify ephemeral flag on the GitHub node
        gh_nodes = [n for n in result.nodes if n.node_type == "pull_request"]
        assert gh_nodes[0].properties.get("ephemeral") is True

    async def test_issue_graph_applies_node_type_filter(self) -> None:
        """node_types query param filters out non-matching nodes from subgraph."""
        from unittest.mock import patch

        gn_model = MagicMock()
        gn_model.id = TEST_NODE_ID
        gn_model.workspace_id = TEST_WORKSPACE_ID
        gn_model.is_deleted = False

        # Call 0: issue existence check. Call 1: graph node lookup.
        session = _make_sequential_session(
            {"scalar": TEST_ISSUE_ID},
            {"scalar": gn_model},
        )

        issue_node = _make_graph_node(node_id=TEST_NODE_ID, node_type="issue", label="PS-1")
        note_node = _make_graph_node(node_type="note", label="Note")
        repo = _make_repo(get_subgraph=AsyncMock(return_value=([issue_node, note_node], [])))

        with (
            patch(
                "pilot_space.api.v1.routers.knowledge_graph.set_rls_context",
                new_callable=AsyncMock,
            ),
            patch(
                "pilot_space.api.v1.routers.knowledge_graph.KnowledgeGraphRepository",
                return_value=repo,
            ),
        ):
            result = await get_issue_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                issue_id=TEST_ISSUE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                depth=2,
                node_types="issue",
                max_nodes=50,
                include_github=False,
            )

        # Only issue nodes should remain after filtering
        assert all(n.node_type == "issue" for n in result.nodes)

    async def test_issue_graph_sorts_by_importance_tier(self) -> None:
        """Nodes are sorted with issues/notes/decisions first, then PR/branch, then others."""
        from unittest.mock import patch

        gn_model = MagicMock()
        gn_model.id = TEST_NODE_ID
        gn_model.workspace_id = TEST_WORKSPACE_ID
        gn_model.is_deleted = False

        # Call 0: issue existence. Call 1: graph node lookup.
        session = _make_sequential_session(
            {"scalar": TEST_ISSUE_ID},
            {"scalar": gn_model},
        )

        skill_node = _make_graph_node(node_type="skill_outcome", label="Skill")
        issue_node = _make_graph_node(node_type="issue", label="Issue")
        pr_node = _make_graph_node(node_type="pull_request", label="PR")
        repo = _make_repo(
            get_subgraph=AsyncMock(return_value=([skill_node, pr_node, issue_node], []))
        )

        with (
            patch(
                "pilot_space.api.v1.routers.knowledge_graph.set_rls_context",
                new_callable=AsyncMock,
            ),
            patch(
                "pilot_space.api.v1.routers.knowledge_graph.KnowledgeGraphRepository",
                return_value=repo,
            ),
        ):
            result = await get_issue_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                issue_id=TEST_ISSUE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                depth=2,
                node_types=None,
                max_nodes=50,
                include_github=False,
            )

        # First node must be issue (tier 0), last must be skill_outcome (tier 2)
        assert result.nodes[0].node_type == "issue"
        assert result.nodes[-1].node_type == "skill_outcome"

    async def test_issue_graph_include_github_false_skips_link_query(self) -> None:
        """include_github=False does not query integration_links at all."""
        from unittest.mock import patch

        gn_model = MagicMock()
        gn_model.id = TEST_NODE_ID
        gn_model.workspace_id = TEST_WORKSPACE_ID
        gn_model.is_deleted = False

        # Only 2 DB calls expected: issue existence + graph node lookup
        session = _make_sequential_session(
            {"scalar": TEST_ISSUE_ID},
            {"scalar": gn_model},
        )

        graph_node = _make_graph_node(node_id=TEST_NODE_ID, label="PS-1")
        repo = _make_repo(get_subgraph=AsyncMock(return_value=([graph_node], [])))

        with (
            patch(
                "pilot_space.api.v1.routers.knowledge_graph.set_rls_context",
                new_callable=AsyncMock,
            ),
            patch(
                "pilot_space.api.v1.routers.knowledge_graph.KnowledgeGraphRepository",
                return_value=repo,
            ),
        ):
            result = await get_issue_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                issue_id=TEST_ISSUE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                depth=2,
                node_types=None,
                max_nodes=50,
                include_github=False,
            )

        # Only the graph node — no ephemeral nodes added
        assert len(result.nodes) == 1
        assert result.nodes[0].node_type == "issue"
        # Session was called exactly twice (issue check + node lookup)
        assert session.execute.await_count == 2

    async def test_issue_graph_edges_from_subgraph_included_in_response(self) -> None:
        """Edges returned by get_subgraph are included in the response."""
        from unittest.mock import patch

        gn_model = MagicMock()
        gn_model.id = TEST_NODE_ID
        gn_model.workspace_id = TEST_WORKSPACE_ID
        gn_model.is_deleted = False

        session = _make_sequential_session(
            {"scalar": TEST_ISSUE_ID},
            {"scalar": gn_model},
        )

        node_a = _make_graph_node(node_id=TEST_NODE_ID, label="Issue A")
        node_b_id = uuid4()
        node_b = _make_graph_node(node_id=node_b_id, node_type="note", label="Note B")
        edge = _make_graph_edge(source_id=TEST_NODE_ID, target_id=node_b_id)
        repo = _make_repo(get_subgraph=AsyncMock(return_value=([node_a, node_b], [edge])))

        with (
            patch(
                "pilot_space.api.v1.routers.knowledge_graph.set_rls_context",
                new_callable=AsyncMock,
            ),
            patch(
                "pilot_space.api.v1.routers.knowledge_graph.KnowledgeGraphRepository",
                return_value=repo,
            ),
        ):
            result = await get_issue_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                issue_id=TEST_ISSUE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                depth=2,
                node_types=None,
                max_nodes=50,
                include_github=False,
            )

        assert len(result.nodes) == 2
        assert len(result.edges) == 1
        assert result.edges[0].source_id == str(TEST_NODE_ID)
        assert result.edges[0].target_id == str(node_b_id)

    async def test_issue_graph_depth_and_max_nodes_forwarded_to_subgraph(self) -> None:
        """depth and max_nodes query params are forwarded to get_subgraph."""
        from unittest.mock import patch

        gn_model = MagicMock()
        gn_model.id = TEST_NODE_ID
        gn_model.workspace_id = TEST_WORKSPACE_ID
        gn_model.is_deleted = False

        session = _make_sequential_session(
            {"scalar": TEST_ISSUE_ID},
            {"scalar": gn_model},
        )

        repo = _make_repo(get_subgraph=AsyncMock(return_value=([], [])))

        with (
            patch(
                "pilot_space.api.v1.routers.knowledge_graph.set_rls_context",
                new_callable=AsyncMock,
            ),
            patch(
                "pilot_space.api.v1.routers.knowledge_graph.KnowledgeGraphRepository",
                return_value=repo,
            ),
        ):
            await get_issue_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                issue_id=TEST_ISSUE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                depth=3,
                node_types=None,
                max_nodes=25,
                include_github=False,
            )

        call_kwargs = repo.get_subgraph.call_args.kwargs
        assert call_kwargs["max_depth"] == 3
        assert call_kwargs["max_nodes"] == 25

    async def test_issue_graph_deduplicates_github_node_already_in_graph(self) -> None:
        """Ephemeral node skipped when a real graph node already has the same external_id."""
        from unittest.mock import patch

        gn_model = MagicMock()
        gn_model.id = TEST_NODE_ID
        gn_model.workspace_id = TEST_WORKSPACE_ID
        gn_model.is_deleted = False

        pr_link = _make_integration_link_mock(link_type="pull_request", external_id="pr-99")

        # The real graph node already references the same PR external_id in properties
        graph_node = _make_graph_node(node_id=TEST_NODE_ID, node_type="pull_request", label="PR")
        graph_node.properties = {"external_id": "pr-99"}

        session = _make_sequential_session(
            {"scalar": TEST_ISSUE_ID},
            {"scalar": gn_model},
            {"scalars_all": [pr_link]},
        )

        repo = _make_repo(get_subgraph=AsyncMock(return_value=([graph_node], [])))

        with (
            patch(
                "pilot_space.api.v1.routers.knowledge_graph.set_rls_context",
                new_callable=AsyncMock,
            ),
            patch(
                "pilot_space.api.v1.routers.knowledge_graph.KnowledgeGraphRepository",
                return_value=repo,
            ),
        ):
            result = await get_issue_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                issue_id=TEST_ISSUE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                depth=2,
                node_types=None,
                max_nodes=50,
                include_github=True,
            )

        # Ephemeral node must NOT be added — real node already covers it
        pr_nodes = [n for n in result.nodes if n.node_type == "pull_request"]
        assert len(pr_nodes) == 1
        assert pr_nodes[0].properties.get("ephemeral") is not True

    async def test_issue_graph_all_github_link_types_mapped(self) -> None:
        """branch, commit (→code_reference), and mention (→note) links are mapped correctly."""
        from unittest.mock import patch

        gn_model = MagicMock()
        gn_model.id = TEST_NODE_ID
        gn_model.workspace_id = TEST_WORKSPACE_ID
        gn_model.is_deleted = False

        branch_link = _make_integration_link_mock(link_type="branch", title="feat/login")
        commit_link = _make_integration_link_mock(link_type="commit", title="abc123")
        mention_link = _make_integration_link_mock(link_type="mention", title="related note")

        session = _make_sequential_session(
            {"scalar": TEST_ISSUE_ID},
            {"scalar": gn_model},
            {"scalars_all": [branch_link, commit_link, mention_link]},
        )

        repo = _make_repo(get_subgraph=AsyncMock(return_value=([], [])))

        with (
            patch(
                "pilot_space.api.v1.routers.knowledge_graph.set_rls_context",
                new_callable=AsyncMock,
            ),
            patch(
                "pilot_space.api.v1.routers.knowledge_graph.KnowledgeGraphRepository",
                return_value=repo,
            ),
        ):
            result = await get_issue_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                issue_id=TEST_ISSUE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                depth=2,
                node_types=None,
                max_nodes=50,
                include_github=True,
            )

        node_types_in_result = {n.node_type for n in result.nodes}
        assert "branch" in node_types_in_result
        assert "code_reference" in node_types_in_result
        assert "note" in node_types_in_result
        assert all(n.properties.get("ephemeral") is True for n in result.nodes)

    async def test_issue_graph_center_node_id_is_graph_node_not_issue(self) -> None:
        """center_node_id in response is the graph node id, not the issue id."""
        from unittest.mock import patch

        gn_model = MagicMock()
        gn_model.id = TEST_NODE_ID  # graph node id — different from TEST_ISSUE_ID
        gn_model.workspace_id = TEST_WORKSPACE_ID
        gn_model.is_deleted = False

        session = _make_sequential_session(
            {"scalar": TEST_ISSUE_ID},
            {"scalar": gn_model},
        )

        repo = _make_repo(get_subgraph=AsyncMock(return_value=([], [])))

        with (
            patch(
                "pilot_space.api.v1.routers.knowledge_graph.set_rls_context",
                new_callable=AsyncMock,
            ),
            patch(
                "pilot_space.api.v1.routers.knowledge_graph.KnowledgeGraphRepository",
                return_value=repo,
            ),
        ):
            result = await get_issue_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                issue_id=TEST_ISSUE_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                depth=2,
                node_types=None,
                max_nodes=50,
                include_github=False,
            )

        assert result.center_node_id == TEST_NODE_ID
        assert result.center_node_id != TEST_ISSUE_ID
