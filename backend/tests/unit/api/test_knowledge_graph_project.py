"""Unit tests for the project-scoped Knowledge Graph endpoint.

Tests cover:
- 404 when project doesn't exist (EntityNotFoundError from service)
- Empty response when no graph node exists for project
- Successful subgraph return when graph node exists
- GitHub node synthesis from project issues' integration_links
- Parameter forwarding to KnowledgeGraphQueryService

Router-level tests mock KnowledgeGraphQueryService (injected via kg_service param).

Feature 016: Knowledge Graph — Project-scoped endpoint
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest

from pilot_space.api.v1.routers.knowledge_graph import (
    get_project_knowledge_graph,
)
from pilot_space.api.v1.schemas.knowledge_graph import GraphResponse
from pilot_space.application.services.memory.knowledge_graph_query_service import (
    EntityNotFoundError,
    EntitySubgraphResult,
)
from pilot_space.domain.exceptions import ValidationError as DomainValidationError
from tests.fixtures.knowledge_graph import (
    RLS_PATCH as _RLS_PATCH,
    make_ephemeral_node as _make_ephemeral_node,
    make_graph_edge as _make_graph_edge,
    make_graph_node as _make_graph_node,
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
TEST_PROJECT_ID = UUID("eeeeeeee-0000-0000-0000-000000000005")


def _default_kwargs(**overrides: object) -> dict[str, object]:
    """Build default kwargs for get_project_knowledge_graph."""
    defaults: dict[str, object] = {
        "workspace_id": TEST_WORKSPACE_ID,
        "project_id": TEST_PROJECT_ID,
        "current_user_id": TEST_USER_ID,
        "depth": 2,
        "node_types": None,
        "max_nodes": 50,
        "include_github": False,
    }
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# Test: 404 path
# ---------------------------------------------------------------------------


class TestProjectKnowledgeGraph404:
    """GET /workspaces/{wid}/projects/{pid}/knowledge-graph — not found."""

    async def test_returns_404_with_correct_detail(self) -> None:
        """EntityNotFoundError from service bubbles up (caught by global app_error_handler)."""
        kg_service = _make_kg_service()
        kg_service.get_project_knowledge_graph.side_effect = EntityNotFoundError(
            "Project", TEST_PROJECT_ID
        )
        session = _make_session()

        with (
            patch(_RLS_PATCH, new_callable=AsyncMock),
            pytest.raises(EntityNotFoundError) as exc_info,
        ):
            await get_project_knowledge_graph(
                session=session,
                kg_service=kg_service,
                **_default_kwargs(),  # type: ignore[arg-type]
            )

        assert exc_info.value.http_status == 404
        assert exc_info.value.entity_type == "Project"


# ---------------------------------------------------------------------------
# Test: empty graph path
# ---------------------------------------------------------------------------


class TestProjectKnowledgeGraphEmpty:
    """Returns empty GraphResponse when project has no graph node."""

    async def test_returns_empty_without_calling_subgraph(self) -> None:
        """Project exists but has no graph node — empty response, center_node_id=None."""
        kg_service = _make_kg_service()
        kg_service.get_project_knowledge_graph.return_value = EntitySubgraphResult(
            nodes=[], edges=[], ephemeral_nodes=[], center_node_id=None
        )
        session = _make_session()

        with patch(_RLS_PATCH, new_callable=AsyncMock):
            result = await get_project_knowledge_graph(
                session=session,
                kg_service=kg_service,
                **_default_kwargs(),  # type: ignore[arg-type]
            )

        assert isinstance(result, GraphResponse)
        assert result.nodes == []
        assert result.edges == []
        assert result.center_node_id is None


# ---------------------------------------------------------------------------
# Test: success path
# ---------------------------------------------------------------------------


class TestProjectKnowledgeGraphSuccess:
    """Successful subgraph return when project graph node exists."""

    async def test_returns_subgraph_when_graph_node_exists(self) -> None:
        """Project with graph node returns populated GraphResponse."""
        project_node = _make_graph_node(node_id=TEST_NODE_ID, node_type="project", label="MyApp")
        issue_node = _make_graph_node(node_type="issue", label="PS-1")
        edge = _make_graph_edge(source_id=TEST_NODE_ID, target_id=issue_node.id)

        kg_service = _make_kg_service()
        kg_service.get_project_knowledge_graph.return_value = EntitySubgraphResult(
            nodes=[project_node, issue_node],
            edges=[edge],
            ephemeral_nodes=[],
            center_node_id=TEST_NODE_ID,
        )
        session = _make_session()

        with patch(_RLS_PATCH, new_callable=AsyncMock):
            result = await get_project_knowledge_graph(
                session=session,
                kg_service=kg_service,
                **_default_kwargs(),  # type: ignore[arg-type]
            )

        assert isinstance(result, GraphResponse)
        assert len(result.nodes) == 2
        assert len(result.edges) == 1
        assert result.center_node_id == TEST_NODE_ID

    async def test_depth_and_max_nodes_forwarded_to_service(self) -> None:
        """depth and max_nodes query params are forwarded to the service."""
        kg_service = _make_kg_service()
        kg_service.get_project_knowledge_graph.return_value = EntitySubgraphResult(
            nodes=[], edges=[], ephemeral_nodes=[], center_node_id=None
        )
        session = _make_session()

        with patch(_RLS_PATCH, new_callable=AsyncMock):
            await get_project_knowledge_graph(
                session=session,
                kg_service=kg_service,
                **_default_kwargs(depth=3, max_nodes=75),  # type: ignore[arg-type]
            )

        call_kwargs = kg_service.get_project_knowledge_graph.call_args.kwargs
        assert call_kwargs["depth"] == 3
        assert call_kwargs["max_nodes"] == 75

    async def test_node_type_filter_forwarded(self) -> None:
        """node_types param is forwarded to the service."""
        issue_node = _make_graph_node(node_type="issue", label="PS-1")

        kg_service = _make_kg_service()
        kg_service.get_project_knowledge_graph.return_value = EntitySubgraphResult(
            nodes=[issue_node],
            edges=[],
            ephemeral_nodes=[],
            center_node_id=TEST_NODE_ID,
        )
        session = _make_session()

        with patch(_RLS_PATCH, new_callable=AsyncMock):
            result = await get_project_knowledge_graph(
                session=session,
                kg_service=kg_service,
                **_default_kwargs(node_types="issue"),  # type: ignore[arg-type]
            )

        assert all(n.node_type == "issue" for n in result.nodes)
        call_kwargs = kg_service.get_project_knowledge_graph.call_args.kwargs
        assert call_kwargs["node_types"] == "issue"

    async def test_rejects_invalid_node_types(self) -> None:
        """Invalid node_types value raises ValidationError with status 422."""
        kg_service = _make_kg_service()
        session = _make_session()

        with (
            patch(_RLS_PATCH, new_callable=AsyncMock),
            pytest.raises(DomainValidationError) as exc_info,
        ):
            await get_project_knowledge_graph(
                session=session,
                kg_service=kg_service,
                **_default_kwargs(node_types="not_a_valid_type"),  # type: ignore[arg-type]
            )

        assert exc_info.value.http_status == 422
        assert "Invalid node_type" in exc_info.value.message

    async def test_sorts_nodes_by_importance_tier(self) -> None:
        """Service returns sorted nodes; verify order preserved in response."""
        issue_node = _make_graph_node(node_type="issue", label="Issue")
        pr_node = _make_graph_node(node_type="pull_request", label="PR")
        skill_node = _make_graph_node(node_type="skill_outcome", label="Skill")

        kg_service = _make_kg_service()
        # Service returns already sorted: issue (tier 0), PR (tier 1), skill (tier 2)
        kg_service.get_project_knowledge_graph.return_value = EntitySubgraphResult(
            nodes=[issue_node, pr_node, skill_node],
            edges=[],
            ephemeral_nodes=[],
            center_node_id=TEST_NODE_ID,
        )
        session = _make_session()

        with patch(_RLS_PATCH, new_callable=AsyncMock):
            result = await get_project_knowledge_graph(
                session=session,
                kg_service=kg_service,
                **_default_kwargs(),  # type: ignore[arg-type]
            )

        assert result.nodes[0].node_type == "issue"
        assert result.nodes[-1].node_type == "skill_outcome"

    async def test_synthesizes_github_nodes_from_project_issues(self) -> None:
        """Ephemeral PR nodes from service are appended to the response."""
        project_node = _make_graph_node(node_id=TEST_NODE_ID, node_type="project", label="MyApp")
        ephemeral = _make_ephemeral_node(
            node_type="pull_request", label="feat: new feature", external_id="456"
        )

        kg_service = _make_kg_service()
        kg_service.get_project_knowledge_graph.return_value = EntitySubgraphResult(
            nodes=[project_node],
            edges=[],
            ephemeral_nodes=[ephemeral],
            center_node_id=TEST_NODE_ID,
        )
        session = _make_session()

        with patch(_RLS_PATCH, new_callable=AsyncMock):
            result = await get_project_knowledge_graph(
                session=session,
                kg_service=kg_service,
                **_default_kwargs(include_github=True),  # type: ignore[arg-type]
            )

        assert len(result.nodes) >= 2
        gh_nodes = [n for n in result.nodes if n.node_type == "pull_request"]
        assert len(gh_nodes) == 1
        assert gh_nodes[0].properties.get("ephemeral") is True
        call_kwargs = kg_service.get_project_knowledge_graph.call_args.kwargs
        assert call_kwargs["include_github"] is True

    async def test_include_github_false_forwarded(self) -> None:
        """include_github=False is forwarded to the service."""
        project_node = _make_graph_node(node_id=TEST_NODE_ID, node_type="project", label="MyApp")

        kg_service = _make_kg_service()
        kg_service.get_project_knowledge_graph.return_value = EntitySubgraphResult(
            nodes=[project_node],
            edges=[],
            ephemeral_nodes=[],
            center_node_id=TEST_NODE_ID,
        )
        session = _make_session()

        with patch(_RLS_PATCH, new_callable=AsyncMock):
            result = await get_project_knowledge_graph(
                session=session,
                kg_service=kg_service,
                **_default_kwargs(),  # type: ignore[arg-type]
            )

        assert len(result.nodes) == 1
        call_kwargs = kg_service.get_project_knowledge_graph.call_args.kwargs
        assert call_kwargs["include_github"] is False

    async def test_rls_context_called_with_correct_args(self) -> None:
        """set_rls_context is called with session, user_id, and workspace_id."""
        kg_service = _make_kg_service()
        kg_service.get_project_knowledge_graph.side_effect = EntityNotFoundError(
            "Project", TEST_PROJECT_ID
        )
        session = _make_session()

        with (
            patch(_RLS_PATCH, new_callable=AsyncMock) as mock_rls,
            pytest.raises(EntityNotFoundError),
        ):
            await get_project_knowledge_graph(
                session=session,
                kg_service=kg_service,
                **_default_kwargs(),  # type: ignore[arg-type]
            )

        mock_rls.assert_awaited_once_with(session, TEST_USER_ID, TEST_WORKSPACE_ID)
