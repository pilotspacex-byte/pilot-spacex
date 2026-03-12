"""Shared test factories for Knowledge Graph tests.

Used by:
- tests/unit/api/test_knowledge_graph.py
- tests/unit/api/test_knowledge_graph_project.py
- tests/unit/services/test_knowledge_graph_query_service.py
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

from pilot_space.application.services.memory.knowledge_graph_query_service import (
    EphemeralNode,
)


def make_graph_node(
    node_id: UUID | None = None,
    node_type: str = "issue",
    label: str = "Test Issue",
    content: str = "",
    properties: dict[str, Any] | None = None,
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
    node.properties = properties or {"state": "todo"}
    node.created_at = datetime.now(tz=UTC)
    node.updated_at = datetime.now(tz=UTC)
    return node


def make_graph_edge(
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


def make_ephemeral_node(
    node_type: str = "pull_request",
    label: str = "feat: fix login #42",
    external_id: str = "123",
) -> EphemeralNode:
    """Build an EphemeralNode dataclass."""
    now = datetime.now(tz=UTC)
    return EphemeralNode(
        id=f"ephemeral-{external_id}",
        node_type=node_type,
        label=label,
        summary=f"GitHub {node_type}: {label}",
        properties={
            "external_id": external_id,
            "external_url": f"https://github.com/repo/pull/{external_id}",
            "author_name": "dev",
            "ephemeral": True,
        },
        created_at=now,
        updated_at=now,
    )


_UNSET = object()


def make_session(scalar_result: Any = _UNSET) -> AsyncMock:
    """Build a mock AsyncSession.

    When scalar_result is provided (including None), the session's execute()
    returns a result with scalar_one_or_none() returning that value.
    When omitted, returns a plain AsyncMock session.
    """
    session = AsyncMock()
    if scalar_result is not _UNSET:
        execute_result = MagicMock()
        execute_result.scalar_one_or_none = MagicMock(return_value=scalar_result)
        session.execute = AsyncMock(return_value=execute_result)
    return session


def make_kg_service() -> AsyncMock:
    """Build a mock KnowledgeGraphQueryService."""
    svc = AsyncMock()
    svc.get_neighbors = AsyncMock()
    svc.get_subgraph = AsyncMock()
    svc.get_user_context = AsyncMock()
    svc.get_issue_knowledge_graph = AsyncMock()
    svc.get_project_knowledge_graph = AsyncMock()
    return svc


def make_kg_repo(**overrides: Any) -> AsyncMock:
    """Build a mock KnowledgeGraphRepository."""
    repo = AsyncMock()
    repo.hybrid_search = AsyncMock(return_value=[])
    repo.get_neighbors = AsyncMock(return_value=[])
    repo.get_node_by_id = AsyncMock(return_value=None)
    repo.get_subgraph = AsyncMock(return_value=([], []))
    repo.get_user_context = AsyncMock(return_value=[])
    repo.get_edges_between = AsyncMock(return_value=[])
    repo.find_node_by_external_id = AsyncMock(return_value=None)
    for key, value in overrides.items():
        setattr(repo, key, value)
    return repo


def make_il_repo(**overrides: Any) -> AsyncMock:
    """Build a mock IntegrationLinkRepository."""
    repo = AsyncMock()
    repo.get_by_issue_in_workspace = AsyncMock(return_value=[])
    repo.get_by_project_issues = AsyncMock(return_value=[])
    for key, value in overrides.items():
        setattr(repo, key, value)
    return repo


def make_issue_repo(**overrides: Any) -> AsyncMock:
    """Build a mock IssueRepository."""
    repo = AsyncMock()
    repo.exists = AsyncMock(return_value=True)
    for key, value in overrides.items():
        setattr(repo, key, value)
    return repo


def make_project_repo(**overrides: Any) -> AsyncMock:
    """Build a mock ProjectRepository."""
    repo = AsyncMock()
    repo.exists = AsyncMock(return_value=True)
    for key, value in overrides.items():
        setattr(repo, key, value)
    return repo


def make_integration_link(
    link_type: str = "pull_request",
    title: str = "feat: add something",
    external_id: str = "123",
) -> MagicMock:
    """Build a mock IntegrationLink."""
    from pilot_space.infrastructure.database.models.integration import IntegrationLinkType

    link = MagicMock()
    link.link_type = IntegrationLinkType(link_type)
    link.title = title
    link.external_id = external_id
    link.external_url = f"https://github.com/repo/pull/{external_id}"
    link.author_name = "dev"
    return link


# Shared RLS patch target
RLS_PATCH = "pilot_space.api.v1.routers.knowledge_graph.set_rls_context"
