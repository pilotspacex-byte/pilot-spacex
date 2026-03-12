"""Unit tests for KnowledgeGraphQueryService.

Tests cover:
- Neighbor traversal (with center node inclusion)
- Subgraph extraction (with RootNodeNotFoundError)
- User context retrieval
- Issue-scoped subgraph (entity validation, GitHub synthesis, filtering, sorting)
- Project-scoped subgraph (entity validation, GitHub synthesis)

Feature 016: Knowledge Graph — Service layer
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from pilot_space.application.services.memory.knowledge_graph_query_service import (
    EntityNotFoundError,
    KnowledgeGraphQueryService,
    RootNodeNotFoundError,
)

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Fixed test identifiers
# ---------------------------------------------------------------------------

TEST_USER_ID = UUID("aaaaaaaa-0000-0000-0000-000000000001")
TEST_WORKSPACE_ID = UUID("bbbbbbbb-0000-0000-0000-000000000002")
TEST_NODE_ID = UUID("cccccccc-0000-0000-0000-000000000003")
TEST_ISSUE_ID = UUID("dddddddd-0000-0000-0000-000000000004")
TEST_PROJECT_ID = UUID("eeeeeeee-0000-0000-0000-000000000005")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_graph_node(
    node_id: UUID | None = None,
    node_type: str = "issue",
    label: str = "Test Issue",
    properties: dict[str, Any] | None = None,
) -> MagicMock:
    from pilot_space.domain.graph_node import NodeType

    node = MagicMock()
    node.id = node_id or uuid4()
    node.node_type = NodeType(node_type)
    node.label = label
    node.summary = f"Summary for {label}"
    node.properties = properties or {}
    node.created_at = datetime.now(tz=UTC)
    node.updated_at = datetime.now(tz=UTC)
    return node


def _make_graph_edge(
    source_id: UUID | None = None,
    target_id: UUID | None = None,
) -> MagicMock:
    from pilot_space.domain.graph_edge import EdgeType

    edge = MagicMock()
    edge.id = uuid4()
    edge.source_id = source_id or uuid4()
    edge.target_id = target_id or uuid4()
    edge.edge_type = EdgeType.RELATES_TO
    edge.weight = 0.8
    edge.properties = {}
    return edge


def _make_integration_link(
    link_type: str = "pull_request",
    title: str = "feat: add something",
    external_id: str = "123",
) -> MagicMock:
    from pilot_space.infrastructure.database.models.integration import IntegrationLinkType

    link = MagicMock()
    link.link_type = IntegrationLinkType(link_type)
    link.title = title
    link.external_id = external_id
    link.external_url = f"https://github.com/repo/pull/{external_id}"
    link.author_name = "dev"
    return link


def _make_kg_repo(**overrides: Any) -> AsyncMock:
    repo = AsyncMock()
    repo.get_neighbors = AsyncMock(return_value=[])
    repo.get_node_by_id = AsyncMock(return_value=None)
    repo.get_subgraph = AsyncMock(return_value=([], []))
    repo.get_user_context = AsyncMock(return_value=[])
    repo.get_edges_between = AsyncMock(return_value=[])
    repo.find_node_by_external_id = AsyncMock(return_value=None)
    for key, value in overrides.items():
        setattr(repo, key, value)
    return repo


def _make_il_repo(**overrides: Any) -> AsyncMock:
    repo = AsyncMock()
    repo.get_by_workspace_with_filter = AsyncMock(return_value=[])
    for key, value in overrides.items():
        setattr(repo, key, value)
    return repo


def _make_session(scalar_result: Any = None) -> AsyncMock:
    session = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalar_one_or_none = MagicMock(return_value=scalar_result)
    session.execute = AsyncMock(return_value=execute_result)
    return session


def _make_sequential_session(*responses: Any) -> AsyncMock:
    call_index = 0

    async def _execute(stmt: Any, *args: Any, **kwargs: Any) -> Any:
        nonlocal call_index
        idx = min(call_index, len(responses) - 1)
        call_index += 1
        spec = responses[idx]
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=spec.get("scalar"))
        return result

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=_execute)
    return session


def _build_service(
    session: AsyncMock | None = None,
    kg_repo: AsyncMock | None = None,
    il_repo: AsyncMock | None = None,
) -> KnowledgeGraphQueryService:
    return KnowledgeGraphQueryService(
        session=session or _make_session(),
        knowledge_graph_repository=kg_repo or _make_kg_repo(),
        integration_link_repository=il_repo or _make_il_repo(),
    )


# ---------------------------------------------------------------------------
# Test: get_neighbors
# ---------------------------------------------------------------------------


class TestGetNeighbors:
    async def test_returns_center_node_with_neighbors(self) -> None:
        center = _make_graph_node(node_id=TEST_NODE_ID, label="Center")
        neighbor = _make_graph_node(label="Neighbor")
        edge = _make_graph_edge(source_id=TEST_NODE_ID, target_id=neighbor.id)

        kg_repo = _make_kg_repo(
            get_neighbors=AsyncMock(return_value=[neighbor]),
            get_node_by_id=AsyncMock(return_value=center),
            get_edges_between=AsyncMock(return_value=[edge]),
        )
        svc = _build_service(kg_repo=kg_repo)

        result = await svc.get_neighbors(node_id=TEST_NODE_ID, workspace_id=TEST_WORKSPACE_ID)

        assert len(result.nodes) == 2
        assert result.center_node_id == TEST_NODE_ID
        assert len(result.edges) == 1

    async def test_returns_only_neighbors_when_center_not_found(self) -> None:
        neighbor = _make_graph_node(label="Neighbor")
        kg_repo = _make_kg_repo(
            get_neighbors=AsyncMock(return_value=[neighbor]),
            get_node_by_id=AsyncMock(return_value=None),
        )
        svc = _build_service(kg_repo=kg_repo)

        result = await svc.get_neighbors(node_id=TEST_NODE_ID, workspace_id=TEST_WORKSPACE_ID)

        assert len(result.nodes) == 1

    async def test_forwards_edge_types(self) -> None:
        from pilot_space.domain.graph_edge import EdgeType

        kg_repo = _make_kg_repo()
        svc = _build_service(kg_repo=kg_repo)

        await svc.get_neighbors(
            node_id=TEST_NODE_ID,
            workspace_id=TEST_WORKSPACE_ID,
            edge_types=[EdgeType.RELATES_TO],
        )

        call_kwargs = kg_repo.get_neighbors.call_args.kwargs
        assert call_kwargs["edge_types"] == [EdgeType.RELATES_TO]


# ---------------------------------------------------------------------------
# Test: get_subgraph
# ---------------------------------------------------------------------------


class TestGetSubgraph:
    async def test_returns_nodes_and_edges(self) -> None:
        node = _make_graph_node(node_id=TEST_NODE_ID)
        edge = _make_graph_edge(source_id=TEST_NODE_ID)
        kg_repo = _make_kg_repo(
            get_node_by_id=AsyncMock(return_value=node),
            get_subgraph=AsyncMock(return_value=([node], [edge])),
        )
        svc = _build_service(kg_repo=kg_repo)

        result = await svc.get_subgraph(root_id=TEST_NODE_ID, workspace_id=TEST_WORKSPACE_ID)

        assert len(result.nodes) == 1
        assert len(result.edges) == 1
        assert result.center_node_id == TEST_NODE_ID

    async def test_raises_when_root_not_found(self) -> None:
        kg_repo = _make_kg_repo(get_node_by_id=AsyncMock(return_value=None))
        svc = _build_service(kg_repo=kg_repo)

        with pytest.raises(RootNodeNotFoundError):
            await svc.get_subgraph(root_id=TEST_NODE_ID, workspace_id=TEST_WORKSPACE_ID)


# ---------------------------------------------------------------------------
# Test: get_user_context
# ---------------------------------------------------------------------------


class TestGetUserContext:
    async def test_returns_user_nodes(self) -> None:
        nodes = [_make_graph_node(label="Pref"), _make_graph_node(label="Pattern")]
        kg_repo = _make_kg_repo(get_user_context=AsyncMock(return_value=nodes))
        svc = _build_service(kg_repo=kg_repo)

        result = await svc.get_user_context(
            workspace_id=TEST_WORKSPACE_ID,
            user_id=TEST_USER_ID,
            limit=10,
        )

        assert len(result.nodes) == 2

    async def test_forwards_params_to_repo(self) -> None:
        kg_repo = _make_kg_repo()
        svc = _build_service(kg_repo=kg_repo)

        await svc.get_user_context(
            workspace_id=TEST_WORKSPACE_ID,
            user_id=TEST_USER_ID,
            limit=5,
        )

        call_kwargs = kg_repo.get_user_context.call_args.kwargs
        assert call_kwargs["user_id"] == TEST_USER_ID
        assert call_kwargs["workspace_id"] == TEST_WORKSPACE_ID
        assert call_kwargs["limit"] == 5


# ---------------------------------------------------------------------------
# Test: get_issue_knowledge_graph
# ---------------------------------------------------------------------------


class TestGetIssueKnowledgeGraph:
    async def test_raises_entity_not_found_when_issue_missing(self) -> None:
        session = _make_session(scalar_result=None)
        svc = _build_service(session=session)

        with pytest.raises(EntityNotFoundError) as exc_info:
            await svc.get_issue_knowledge_graph(
                issue_id=TEST_ISSUE_ID, workspace_id=TEST_WORKSPACE_ID
            )

        assert exc_info.value.entity_type == "Issue"

    async def test_returns_empty_when_no_graph_node(self) -> None:
        session = _make_session(scalar_result=TEST_ISSUE_ID)
        kg_repo = _make_kg_repo(find_node_by_external_id=AsyncMock(return_value=None))
        svc = _build_service(session=session, kg_repo=kg_repo)

        result = await svc.get_issue_knowledge_graph(
            issue_id=TEST_ISSUE_ID,
            workspace_id=TEST_WORKSPACE_ID,
            include_github=False,
        )

        assert result.nodes == []
        assert result.edges == []
        assert result.center_node_id is None

    async def test_returns_subgraph_with_center_node_id(self) -> None:
        session = _make_session(scalar_result=TEST_ISSUE_ID)
        graph_node = _make_graph_node(node_id=TEST_NODE_ID)
        kg_repo = _make_kg_repo(
            find_node_by_external_id=AsyncMock(return_value=graph_node),
            get_subgraph=AsyncMock(return_value=([graph_node], [])),
        )
        svc = _build_service(session=session, kg_repo=kg_repo)

        result = await svc.get_issue_knowledge_graph(
            issue_id=TEST_ISSUE_ID,
            workspace_id=TEST_WORKSPACE_ID,
            include_github=False,
        )

        assert result.center_node_id == TEST_NODE_ID
        assert len(result.nodes) == 1

    async def test_synthesizes_github_nodes(self) -> None:
        session = _make_session(scalar_result=TEST_ISSUE_ID)
        graph_node = _make_graph_node(node_id=TEST_NODE_ID)
        pr_link = _make_integration_link(link_type="pull_request", title="PR #1")

        kg_repo = _make_kg_repo(
            find_node_by_external_id=AsyncMock(return_value=graph_node),
            get_subgraph=AsyncMock(return_value=([graph_node], [])),
        )
        il_repo = _make_il_repo(
            get_by_workspace_with_filter=AsyncMock(return_value=[pr_link]),
        )
        svc = _build_service(session=session, kg_repo=kg_repo, il_repo=il_repo)

        result = await svc.get_issue_knowledge_graph(
            issue_id=TEST_ISSUE_ID,
            workspace_id=TEST_WORKSPACE_ID,
            include_github=True,
        )

        assert len(result.ephemeral_nodes) == 1
        assert result.ephemeral_nodes[0].node_type == "pull_request"
        assert result.ephemeral_nodes[0].properties["ephemeral"] is True

    async def test_deduplicates_github_node_already_in_graph(self) -> None:
        session = _make_session(scalar_result=TEST_ISSUE_ID)
        graph_node = _make_graph_node(
            node_id=TEST_NODE_ID,
            node_type="pull_request",
            properties={"external_id": "pr-99"},
        )
        pr_link = _make_integration_link(external_id="pr-99")

        kg_repo = _make_kg_repo(
            find_node_by_external_id=AsyncMock(return_value=graph_node),
            get_subgraph=AsyncMock(return_value=([graph_node], [])),
        )
        il_repo = _make_il_repo(
            get_by_workspace_with_filter=AsyncMock(return_value=[pr_link]),
        )
        svc = _build_service(session=session, kg_repo=kg_repo, il_repo=il_repo)

        result = await svc.get_issue_knowledge_graph(
            issue_id=TEST_ISSUE_ID,
            workspace_id=TEST_WORKSPACE_ID,
            include_github=True,
        )

        assert len(result.ephemeral_nodes) == 0

    async def test_filters_by_node_types(self) -> None:
        session = _make_session(scalar_result=TEST_ISSUE_ID)
        graph_node = _make_graph_node(node_id=TEST_NODE_ID)
        issue_node = _make_graph_node(node_type="issue", label="Issue")
        note_node = _make_graph_node(node_type="note", label="Note")

        kg_repo = _make_kg_repo(
            find_node_by_external_id=AsyncMock(return_value=graph_node),
            get_subgraph=AsyncMock(return_value=([issue_node, note_node], [])),
        )
        svc = _build_service(session=session, kg_repo=kg_repo)

        result = await svc.get_issue_knowledge_graph(
            issue_id=TEST_ISSUE_ID,
            workspace_id=TEST_WORKSPACE_ID,
            node_types="issue",
            include_github=False,
        )

        assert all(n.node_type.value == "issue" for n in result.nodes)
        assert result.node_type_filter_applied is True

    async def test_sorts_by_importance_tier(self) -> None:
        session = _make_session(scalar_result=TEST_ISSUE_ID)
        graph_node = _make_graph_node(node_id=TEST_NODE_ID)
        skill_node = _make_graph_node(node_type="skill_outcome", label="Skill")
        issue_node = _make_graph_node(node_type="issue", label="Issue")
        pr_node = _make_graph_node(node_type="pull_request", label="PR")

        kg_repo = _make_kg_repo(
            find_node_by_external_id=AsyncMock(return_value=graph_node),
            get_subgraph=AsyncMock(return_value=([skill_node, pr_node, issue_node], [])),
        )
        svc = _build_service(session=session, kg_repo=kg_repo)

        result = await svc.get_issue_knowledge_graph(
            issue_id=TEST_ISSUE_ID,
            workspace_id=TEST_WORKSPACE_ID,
            include_github=False,
        )

        assert result.nodes[0].node_type.value == "issue"
        assert result.nodes[-1].node_type.value == "skill_outcome"

    async def test_include_github_false_skips_synthesis(self) -> None:
        session = _make_session(scalar_result=TEST_ISSUE_ID)
        graph_node = _make_graph_node(node_id=TEST_NODE_ID)

        kg_repo = _make_kg_repo(
            find_node_by_external_id=AsyncMock(return_value=graph_node),
            get_subgraph=AsyncMock(return_value=([graph_node], [])),
        )
        il_repo = _make_il_repo()
        svc = _build_service(session=session, kg_repo=kg_repo, il_repo=il_repo)

        result = await svc.get_issue_knowledge_graph(
            issue_id=TEST_ISSUE_ID,
            workspace_id=TEST_WORKSPACE_ID,
            include_github=False,
        )

        il_repo.get_by_workspace_with_filter.assert_not_awaited()
        assert result.ephemeral_nodes == []

    async def test_depth_and_max_nodes_forwarded(self) -> None:
        session = _make_session(scalar_result=TEST_ISSUE_ID)
        graph_node = _make_graph_node(node_id=TEST_NODE_ID)

        kg_repo = _make_kg_repo(
            find_node_by_external_id=AsyncMock(return_value=graph_node),
            get_subgraph=AsyncMock(return_value=([], [])),
        )
        svc = _build_service(session=session, kg_repo=kg_repo)

        await svc.get_issue_knowledge_graph(
            issue_id=TEST_ISSUE_ID,
            workspace_id=TEST_WORKSPACE_ID,
            depth=3,
            max_nodes=25,
            include_github=False,
        )

        call_kwargs = kg_repo.get_subgraph.call_args.kwargs
        assert call_kwargs["max_depth"] == 3
        assert call_kwargs["max_nodes"] == 25


# ---------------------------------------------------------------------------
# Test: get_project_knowledge_graph
# ---------------------------------------------------------------------------


class TestGetProjectKnowledgeGraph:
    async def test_raises_entity_not_found_when_project_missing(self) -> None:
        session = _make_session(scalar_result=None)
        svc = _build_service(session=session)

        with pytest.raises(EntityNotFoundError) as exc_info:
            await svc.get_project_knowledge_graph(
                project_id=TEST_PROJECT_ID, workspace_id=TEST_WORKSPACE_ID
            )

        assert exc_info.value.entity_type == "Project"

    async def test_returns_subgraph_when_graph_node_exists(self) -> None:
        session = _make_session(scalar_result=TEST_PROJECT_ID)
        graph_node = _make_graph_node(node_id=TEST_NODE_ID, node_type="project")

        kg_repo = _make_kg_repo(
            find_node_by_external_id=AsyncMock(return_value=graph_node),
            get_subgraph=AsyncMock(return_value=([graph_node], [])),
        )
        svc = _build_service(session=session, kg_repo=kg_repo)

        result = await svc.get_project_knowledge_graph(
            project_id=TEST_PROJECT_ID,
            workspace_id=TEST_WORKSPACE_ID,
            include_github=False,
        )

        assert result.center_node_id == TEST_NODE_ID
        assert len(result.nodes) == 1

    async def test_uses_larger_fetch_max_override(self) -> None:
        session = _make_session(scalar_result=TEST_PROJECT_ID)
        graph_node = _make_graph_node(node_id=TEST_NODE_ID, node_type="project")

        kg_repo = _make_kg_repo(
            find_node_by_external_id=AsyncMock(return_value=graph_node),
            get_subgraph=AsyncMock(return_value=([], [])),
        )
        svc = _build_service(session=session, kg_repo=kg_repo)

        await svc.get_project_knowledge_graph(
            project_id=TEST_PROJECT_ID,
            workspace_id=TEST_WORKSPACE_ID,
            node_types="issue",
            max_nodes=50,
            include_github=False,
        )

        # When node_types is set, fetch_max_override=200 is used for projects
        call_kwargs = kg_repo.get_subgraph.call_args.kwargs
        assert call_kwargs["max_nodes"] == 200
