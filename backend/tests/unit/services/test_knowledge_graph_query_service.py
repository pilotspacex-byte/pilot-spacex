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

from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from pilot_space.application.services.memory.knowledge_graph_query_service import (
    EntityNotFoundError,
    KnowledgeGraphQueryService,
    RootNodeNotFoundError,
)
from tests.fixtures.knowledge_graph import (
    make_graph_edge as _make_graph_edge,
    make_graph_node as _make_graph_node,
    make_il_repo as _make_il_repo,
    make_integration_link as _make_integration_link,
    make_issue_repo as _make_issue_repo,
    make_kg_repo as _make_kg_repo,
    make_project_repo as _make_project_repo,
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
# Helpers (test-specific)
# ---------------------------------------------------------------------------


def _build_service(
    kg_repo: AsyncMock | None = None,
    il_repo: AsyncMock | None = None,
    issue_repo: AsyncMock | None = None,
    project_repo: AsyncMock | None = None,
) -> KnowledgeGraphQueryService:
    return KnowledgeGraphQueryService(
        knowledge_graph_repository=kg_repo or _make_kg_repo(),
        integration_link_repository=il_repo or _make_il_repo(),
        issue_repository=issue_repo or _make_issue_repo(),
        project_repository=project_repo or _make_project_repo(),
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
        issue_repo = _make_issue_repo(exists=AsyncMock(return_value=False))
        svc = _build_service(issue_repo=issue_repo)

        with pytest.raises(EntityNotFoundError) as exc_info:
            await svc.get_issue_knowledge_graph(
                issue_id=TEST_ISSUE_ID, workspace_id=TEST_WORKSPACE_ID
            )

        assert exc_info.value.entity_type == "Issue"

    async def test_returns_empty_when_no_graph_node(self) -> None:
        kg_repo = _make_kg_repo(find_node_by_external_id=AsyncMock(return_value=None))
        svc = _build_service(kg_repo=kg_repo)

        result = await svc.get_issue_knowledge_graph(
            issue_id=TEST_ISSUE_ID,
            workspace_id=TEST_WORKSPACE_ID,
            include_github=False,
        )

        assert result.nodes == []
        assert result.edges == []
        assert result.center_node_id is None

    async def test_returns_subgraph_with_center_node_id(self) -> None:
        graph_node = _make_graph_node(node_id=TEST_NODE_ID)
        kg_repo = _make_kg_repo(
            find_node_by_external_id=AsyncMock(return_value=graph_node),
            get_subgraph=AsyncMock(return_value=([graph_node], [])),
        )
        svc = _build_service(kg_repo=kg_repo)

        result = await svc.get_issue_knowledge_graph(
            issue_id=TEST_ISSUE_ID,
            workspace_id=TEST_WORKSPACE_ID,
            include_github=False,
        )

        assert result.center_node_id == TEST_NODE_ID
        assert len(result.nodes) == 1

    async def test_synthesizes_github_nodes(self) -> None:
        graph_node = _make_graph_node(node_id=TEST_NODE_ID)
        pr_link = _make_integration_link(link_type="pull_request", title="PR #1")

        kg_repo = _make_kg_repo(
            find_node_by_external_id=AsyncMock(return_value=graph_node),
            get_subgraph=AsyncMock(return_value=([graph_node], [])),
        )
        il_repo = _make_il_repo(
            get_by_issue_in_workspace=AsyncMock(return_value=[pr_link]),
        )
        svc = _build_service(kg_repo=kg_repo, il_repo=il_repo)

        result = await svc.get_issue_knowledge_graph(
            issue_id=TEST_ISSUE_ID,
            workspace_id=TEST_WORKSPACE_ID,
            include_github=True,
        )

        assert len(result.ephemeral_nodes) == 1
        assert result.ephemeral_nodes[0].node_type == "pull_request"
        assert result.ephemeral_nodes[0].properties["ephemeral"] is True

    async def test_deduplicates_github_node_already_in_graph(self) -> None:
        graph_node = _make_graph_node(
            node_id=TEST_NODE_ID,
            node_type="pull_request",
            properties={
                "external_id": "pr-99",
                "external_url": "https://github.com/repo/pull/pr-99",
            },
        )
        pr_link = _make_integration_link(external_id="pr-99")

        kg_repo = _make_kg_repo(
            find_node_by_external_id=AsyncMock(return_value=graph_node),
            get_subgraph=AsyncMock(return_value=([graph_node], [])),
        )
        il_repo = _make_il_repo(
            get_by_issue_in_workspace=AsyncMock(return_value=[pr_link]),
        )
        svc = _build_service(kg_repo=kg_repo, il_repo=il_repo)

        result = await svc.get_issue_knowledge_graph(
            issue_id=TEST_ISSUE_ID,
            workspace_id=TEST_WORKSPACE_ID,
            include_github=True,
        )

        assert len(result.ephemeral_nodes) == 0

    async def test_filters_by_node_types(self) -> None:
        graph_node = _make_graph_node(node_id=TEST_NODE_ID)
        issue_node = _make_graph_node(node_type="issue", label="Issue")
        note_node = _make_graph_node(node_type="note", label="Note")

        kg_repo = _make_kg_repo(
            find_node_by_external_id=AsyncMock(return_value=graph_node),
            get_subgraph=AsyncMock(return_value=([issue_node, note_node], [])),
        )
        svc = _build_service(kg_repo=kg_repo)

        result = await svc.get_issue_knowledge_graph(
            issue_id=TEST_ISSUE_ID,
            workspace_id=TEST_WORKSPACE_ID,
            node_types="issue",
            include_github=False,
        )

        assert all(n.node_type.value == "issue" for n in result.nodes)

    async def test_sorts_by_importance_tier(self) -> None:
        graph_node = _make_graph_node(node_id=TEST_NODE_ID)
        skill_node = _make_graph_node(node_type="skill_outcome", label="Skill")
        issue_node = _make_graph_node(node_type="issue", label="Issue")
        pr_node = _make_graph_node(node_type="pull_request", label="PR")

        kg_repo = _make_kg_repo(
            find_node_by_external_id=AsyncMock(return_value=graph_node),
            get_subgraph=AsyncMock(return_value=([skill_node, pr_node, issue_node], [])),
        )
        svc = _build_service(kg_repo=kg_repo)

        result = await svc.get_issue_knowledge_graph(
            issue_id=TEST_ISSUE_ID,
            workspace_id=TEST_WORKSPACE_ID,
            include_github=False,
        )

        assert result.nodes[0].node_type.value == "issue"
        assert result.nodes[-1].node_type.value == "skill_outcome"

    async def test_include_github_false_skips_synthesis(self) -> None:
        graph_node = _make_graph_node(node_id=TEST_NODE_ID)

        kg_repo = _make_kg_repo(
            find_node_by_external_id=AsyncMock(return_value=graph_node),
            get_subgraph=AsyncMock(return_value=([graph_node], [])),
        )
        il_repo = _make_il_repo()
        svc = _build_service(kg_repo=kg_repo, il_repo=il_repo)

        result = await svc.get_issue_knowledge_graph(
            issue_id=TEST_ISSUE_ID,
            workspace_id=TEST_WORKSPACE_ID,
            include_github=False,
        )

        il_repo.get_by_issue_in_workspace.assert_not_awaited()
        assert result.ephemeral_nodes == []

    async def test_depth_and_max_nodes_forwarded(self) -> None:
        graph_node = _make_graph_node(node_id=TEST_NODE_ID)

        kg_repo = _make_kg_repo(
            find_node_by_external_id=AsyncMock(return_value=graph_node),
            get_subgraph=AsyncMock(return_value=([], [])),
        )
        svc = _build_service(kg_repo=kg_repo)

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
        project_repo = _make_project_repo(exists=AsyncMock(return_value=False))
        svc = _build_service(project_repo=project_repo)

        with pytest.raises(EntityNotFoundError) as exc_info:
            await svc.get_project_knowledge_graph(
                project_id=TEST_PROJECT_ID, workspace_id=TEST_WORKSPACE_ID
            )

        assert exc_info.value.entity_type == "Project"

    async def test_returns_subgraph_when_graph_node_exists(self) -> None:
        graph_node = _make_graph_node(node_id=TEST_NODE_ID, node_type="project")

        kg_repo = _make_kg_repo(
            find_node_by_external_id=AsyncMock(return_value=graph_node),
            get_subgraph=AsyncMock(return_value=([graph_node], [])),
        )
        svc = _build_service(kg_repo=kg_repo)

        result = await svc.get_project_knowledge_graph(
            project_id=TEST_PROJECT_ID,
            workspace_id=TEST_WORKSPACE_ID,
            include_github=False,
        )

        assert result.center_node_id == TEST_NODE_ID
        assert len(result.nodes) == 1

    async def test_uses_larger_fetch_max_override(self) -> None:
        graph_node = _make_graph_node(node_id=TEST_NODE_ID, node_type="project")

        kg_repo = _make_kg_repo(
            find_node_by_external_id=AsyncMock(return_value=graph_node),
            get_subgraph=AsyncMock(return_value=([], [])),
        )
        svc = _build_service(kg_repo=kg_repo)

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
