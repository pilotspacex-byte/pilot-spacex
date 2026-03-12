"""Unit tests for the project-scoped Knowledge Graph endpoint.

Tests cover:
- 404 when project doesn't exist
- Empty response when no graph node exists for project
- Successful subgraph return when graph node exists
- GitHub node synthesis from project issues' integration_links

Feature 016: Knowledge Graph — Project-scoped endpoint
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from pilot_space.api.v1.routers.knowledge_graph import (
    get_project_knowledge_graph,
)
from pilot_space.api.v1.schemas.knowledge_graph import GraphResponse

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Fixed test identifiers
# ---------------------------------------------------------------------------

TEST_USER_ID = UUID("aaaaaaaa-0000-0000-0000-000000000001")
TEST_WORKSPACE_ID = UUID("bbbbbbbb-0000-0000-0000-000000000002")
TEST_NODE_ID = UUID("cccccccc-0000-0000-0000-000000000003")
TEST_PROJECT_ID = UUID("eeeeeeee-0000-0000-0000-000000000005")

# ---------------------------------------------------------------------------
# Helper factories (mirror test_knowledge_graph.py patterns)
# ---------------------------------------------------------------------------


def _make_graph_node(
    node_id: UUID | None = None,
    node_type: str = "project",
    label: str = "Test Project",
) -> MagicMock:
    """Build a mock GraphNode domain object."""
    from pilot_space.domain.graph_node import NodeType

    node = MagicMock()
    node.id = node_id or uuid4()
    node.node_type = NodeType(node_type)
    node.label = label
    node.summary = f"Summary for {label}"
    node.properties = {}
    node.created_at = datetime.now(tz=UTC)
    node.updated_at = datetime.now(tz=UTC)
    return node


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
    link.workspace_id = TEST_WORKSPACE_ID
    link.link_type = IntegrationLinkType(link_type)
    link.title = title
    link.external_id = external_id
    link.external_url = f"https://github.com/repo/pull/{external_id}"
    link.author_name = "dev"
    link.is_deleted = False
    return link


def _make_repo(**kwargs: object) -> AsyncMock:
    """Build a mock KnowledgeGraphRepository."""
    repo = AsyncMock()
    repo.get_subgraph = AsyncMock(return_value=([], []))
    for key, value in kwargs.items():
        setattr(repo, key, value)
    return repo


def _make_sequential_session(*responses: object) -> AsyncMock:
    """Build a mock AsyncSession returning different results on successive execute calls."""
    call_index = 0

    async def _execute(stmt: object, *args: object, **kwargs: object) -> object:
        nonlocal call_index
        idx = min(call_index, len(responses) - 1)
        call_index += 1
        spec = responses[idx]
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=spec.get("scalar"))  # type: ignore[union-attr]
        scalars_mock = MagicMock()
        scalars_mock.all = MagicMock(return_value=spec.get("scalars_all") or [])  # type: ignore[union-attr]
        result.scalars = MagicMock(return_value=scalars_mock)
        return result

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=_execute)
    return session


# ---------------------------------------------------------------------------
# Test: get_project_knowledge_graph — 404 path
# ---------------------------------------------------------------------------


class TestProjectKnowledgeGraph404:
    """GET /workspaces/{workspace_id}/projects/{project_id}/knowledge-graph — not found."""

    async def test_returns_404_when_project_not_found(self) -> None:
        """Non-existent project raises 404 before querying the graph."""
        from unittest.mock import patch

        from fastapi import HTTPException

        # Session returns None → project existence check fails → 404
        session = _make_sequential_session({"scalar": None})
        repo = _make_repo()

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
            await get_project_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                project_id=TEST_PROJECT_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                depth=2,
                node_types=None,
                max_nodes=50,
                include_github=False,
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Project not found"
        repo.get_subgraph.assert_not_awaited()

    async def test_returns_404_detail_message(self) -> None:
        """404 response contains 'Project not found' detail string."""
        from unittest.mock import patch

        from fastapi import HTTPException

        session = _make_sequential_session({"scalar": None})
        repo = _make_repo()

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
            await get_project_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                project_id=TEST_PROJECT_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                depth=2,
                node_types=None,
                max_nodes=50,
                include_github=False,
            )

        assert "Project not found" in exc_info.value.detail


# ---------------------------------------------------------------------------
# Test: get_project_knowledge_graph — empty graph path
# ---------------------------------------------------------------------------


class TestProjectKnowledgeGraphEmpty:
    """Returns empty GraphResponse when project has no graph node."""

    async def test_returns_empty_response_when_no_graph_node(self) -> None:
        """Project exists but has no graph node → empty GraphResponse with center_node_id=project_id."""
        from unittest.mock import patch

        # Call 0: project existence check → found. Call 1: graph node lookup → not found.
        session = _make_sequential_session(
            {"scalar": TEST_PROJECT_ID},
            {"scalar": None},
        )
        repo = _make_repo()

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
            result = await get_project_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                project_id=TEST_PROJECT_ID,
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
        assert result.center_node_id == TEST_PROJECT_ID
        repo.get_subgraph.assert_not_awaited()

    async def test_empty_response_does_not_call_subgraph(self) -> None:
        """get_subgraph is NOT called when no graph node found for project."""
        from unittest.mock import patch

        session = _make_sequential_session(
            {"scalar": TEST_PROJECT_ID},
            {"scalar": None},
        )
        repo = _make_repo()

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
            await get_project_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                project_id=TEST_PROJECT_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                depth=2,
                node_types=None,
                max_nodes=50,
                include_github=False,
            )

        repo.get_subgraph.assert_not_awaited()


# ---------------------------------------------------------------------------
# Test: get_project_knowledge_graph — success path
# ---------------------------------------------------------------------------


class TestProjectKnowledgeGraphSuccess:
    """Successful subgraph return when project graph node exists."""

    async def test_returns_subgraph_when_graph_node_exists(self) -> None:
        """Project with graph node returns populated GraphResponse."""
        from unittest.mock import patch

        gn_model = MagicMock()
        gn_model.id = TEST_NODE_ID
        gn_model.workspace_id = TEST_WORKSPACE_ID
        gn_model.is_deleted = False

        project_node = _make_graph_node(node_id=TEST_NODE_ID, node_type="project", label="MyApp")
        issue_node = _make_graph_node(node_type="issue", label="PS-1")
        edge = _make_graph_edge(source_id=TEST_NODE_ID, target_id=issue_node.id)

        session = _make_sequential_session(
            {"scalar": TEST_PROJECT_ID},
            {"scalar": gn_model},
        )
        repo = _make_repo(get_subgraph=AsyncMock(return_value=([project_node, issue_node], [edge])))

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
            result = await get_project_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                project_id=TEST_PROJECT_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                depth=2,
                node_types=None,
                max_nodes=50,
                include_github=False,
            )

        assert isinstance(result, GraphResponse)
        assert len(result.nodes) == 2
        assert len(result.edges) == 1
        assert result.center_node_id == TEST_NODE_ID

    async def test_depth_and_max_nodes_forwarded_to_subgraph(self) -> None:
        """depth and max_nodes query params are forwarded to get_subgraph."""
        from unittest.mock import patch

        gn_model = MagicMock()
        gn_model.id = TEST_NODE_ID
        gn_model.workspace_id = TEST_WORKSPACE_ID
        gn_model.is_deleted = False

        session = _make_sequential_session(
            {"scalar": TEST_PROJECT_ID},
            {"scalar": gn_model},
        )
        repo = _make_repo()

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
            await get_project_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                project_id=TEST_PROJECT_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                depth=3,
                node_types=None,
                max_nodes=75,
                include_github=False,
            )

        call_kwargs = repo.get_subgraph.call_args.kwargs
        assert call_kwargs["max_depth"] == 3
        assert call_kwargs["max_nodes"] == 75

    async def test_node_type_filter_applied(self) -> None:
        """node_types param filters out non-matching nodes from subgraph."""
        from unittest.mock import patch

        gn_model = MagicMock()
        gn_model.id = TEST_NODE_ID
        gn_model.workspace_id = TEST_WORKSPACE_ID
        gn_model.is_deleted = False

        session = _make_sequential_session(
            {"scalar": TEST_PROJECT_ID},
            {"scalar": gn_model},
        )

        project_node = _make_graph_node(node_id=TEST_NODE_ID, node_type="project", label="MyApp")
        issue_node = _make_graph_node(node_type="issue", label="PS-1")
        note_node = _make_graph_node(node_type="note", label="Note")
        repo = _make_repo(
            get_subgraph=AsyncMock(return_value=([project_node, issue_node, note_node], []))
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
            result = await get_project_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                project_id=TEST_PROJECT_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                depth=2,
                node_types="issue",
                max_nodes=50,
                include_github=False,
            )

        assert all(n.node_type == "issue" for n in result.nodes)

    async def test_sorts_nodes_by_importance_tier(self) -> None:
        """Nodes are sorted with issues/notes first, then PR/branch, then others."""
        from unittest.mock import patch

        gn_model = MagicMock()
        gn_model.id = TEST_NODE_ID
        gn_model.workspace_id = TEST_WORKSPACE_ID
        gn_model.is_deleted = False

        session = _make_sequential_session(
            {"scalar": TEST_PROJECT_ID},
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
            result = await get_project_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                project_id=TEST_PROJECT_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                depth=2,
                node_types=None,
                max_nodes=50,
                include_github=False,
            )

        assert result.nodes[0].node_type == "issue"
        assert result.nodes[-1].node_type == "skill_outcome"

    async def test_synthesizes_github_nodes_from_project_issues(self) -> None:
        """include_github=true with integration links appends ephemeral PR nodes."""
        from unittest.mock import patch

        gn_model = MagicMock()
        gn_model.id = TEST_NODE_ID
        gn_model.workspace_id = TEST_WORKSPACE_ID
        gn_model.is_deleted = False

        pr_link = _make_integration_link_mock(link_type="pull_request", title="feat: new feature")

        # Call 0: project existence. Call 1: graph node lookup. Call 2: integration links.
        session = _make_sequential_session(
            {"scalar": TEST_PROJECT_ID},
            {"scalar": gn_model},
            {"scalars_all": [pr_link]},
        )

        project_node = _make_graph_node(node_id=TEST_NODE_ID, node_type="project", label="MyApp")
        repo = _make_repo(get_subgraph=AsyncMock(return_value=([project_node], [])))

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
            result = await get_project_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                project_id=TEST_PROJECT_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                depth=2,
                node_types=None,
                max_nodes=50,
                include_github=True,
            )

        assert len(result.nodes) >= 2
        node_types_in_result = [n.node_type for n in result.nodes]
        assert "pull_request" in node_types_in_result

        gh_nodes = [n for n in result.nodes if n.node_type == "pull_request"]
        assert gh_nodes[0].properties.get("ephemeral") is True

    async def test_include_github_false_skips_link_query(self) -> None:
        """include_github=False does not query integration_links."""
        from unittest.mock import patch

        gn_model = MagicMock()
        gn_model.id = TEST_NODE_ID
        gn_model.workspace_id = TEST_WORKSPACE_ID
        gn_model.is_deleted = False

        # Only 2 DB calls expected: project existence + graph node lookup
        session = _make_sequential_session(
            {"scalar": TEST_PROJECT_ID},
            {"scalar": gn_model},
        )

        project_node = _make_graph_node(node_id=TEST_NODE_ID, node_type="project", label="MyApp")
        repo = _make_repo(get_subgraph=AsyncMock(return_value=([project_node], [])))

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
            result = await get_project_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                project_id=TEST_PROJECT_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                depth=2,
                node_types=None,
                max_nodes=50,
                include_github=False,
            )

        # Only the graph node — no ephemeral nodes added
        assert len(result.nodes) == 1
        # Session was called exactly twice (project check + node lookup)
        assert session.execute.await_count == 2

    async def test_rls_context_called_with_correct_args(self) -> None:
        """set_rls_context is called with session, user_id, and workspace_id."""
        from unittest.mock import patch

        from fastapi import HTTPException

        session = _make_sequential_session({"scalar": None})

        with (
            patch(
                "pilot_space.api.v1.routers.knowledge_graph.set_rls_context",
                new_callable=AsyncMock,
            ) as mock_rls,
            patch(
                "pilot_space.api.v1.routers.knowledge_graph.KnowledgeGraphRepository",
            ),
            pytest.raises(HTTPException, match="Project not found"),
        ):
            await get_project_knowledge_graph(
                workspace_id=TEST_WORKSPACE_ID,
                project_id=TEST_PROJECT_ID,
                session=session,
                current_user_id=TEST_USER_ID,
                depth=2,
                node_types=None,
                max_nodes=50,
                include_github=False,
            )

        mock_rls.assert_awaited_once_with(session, TEST_USER_ID, TEST_WORKSPACE_ID)
