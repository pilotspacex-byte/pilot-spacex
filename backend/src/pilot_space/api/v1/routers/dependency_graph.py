"""Dependency Graph API — project-scoped issue dependency graph.

T-237: GET /api/v1/projects/{project_id}/dependency-graph
       Returns nodes, edges, critical_path, and circular dependency detection.

Feature 017: Note Versioning / PM Block Engine — Phase 2c
"""

from __future__ import annotations

from collections import defaultdict, deque
from itertools import pairwise
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, Query
from pydantic import BaseModel

from pilot_space.dependencies.auth import CurrentUserId, SessionDep
from pilot_space.domain.exceptions import NotFoundError

router = APIRouter(prefix="/projects", tags=["dependency-graph"])


# ── Response Schemas ─────────────────────────────────────────────────────────


class DependencyNode(BaseModel):
    id: str
    identifier: str
    name: str
    state: str
    state_group: str


class DependencyEdge(BaseModel):
    source_id: str
    target_id: str
    is_critical: bool = False


class DependencyGraphResponse(BaseModel):
    nodes: list[DependencyNode]
    edges: list[DependencyEdge]
    critical_path: list[str]
    circular_deps: list[list[str]]
    has_circular: bool


# ── Endpoint ─────────────────────────────────────────────────────────────────


@router.get(
    "/{project_id}/dependency-graph",
    response_model=DependencyGraphResponse,
    summary="Dependency graph for a project",
)
async def get_dependency_graph(
    project_id: Annotated[UUID, Path()],
    session: SessionDep,
    workspace_id: Annotated[str, Query(description="Workspace UUID for RLS enforcement")],
    current_user_id: CurrentUserId,
) -> DependencyGraphResponse:
    """Return DAG nodes, edges, critical path, and circular dep detection for a project.

    Queries all non-deleted issues in the project, then fetches BLOCKS-type
    IssueLinks between those issues. Returns the full directed graph plus
    longest-path critical path and any circular dependency cycles.
    """
    from sqlalchemy import select

    from pilot_space.infrastructure.database.models import Issue
    from pilot_space.infrastructure.database.models.issue_link import IssueLink, IssueLinkType

    workspace_uuid = UUID(workspace_id)

    # Verify project exists in workspace (RLS also enforced at DB level)
    from pilot_space.infrastructure.database.models.project import Project

    project_result = await session.execute(
        select(Project).where(
            Project.id == project_id,
            Project.workspace_id == workspace_uuid,
            Project.is_deleted == False,  # noqa: E712
        )
    )
    project = project_result.scalar_one_or_none()
    if not project:
        raise NotFoundError("Project not found")

    # Load all non-deleted issues in the project
    issues_result = await session.execute(
        select(Issue).where(
            Issue.project_id == project_id,
            Issue.workspace_id == workspace_uuid,
            Issue.is_deleted == False,  # noqa: E712
        )
    )
    issues = issues_result.scalars().all()
    issue_ids = {str(i.id) for i in issues}

    nodes = [
        DependencyNode(
            id=str(i.id),
            identifier=i.identifier,
            name=i.name,
            state=i.state.name if i.state else "Backlog",
            state_group=i.state.group if i.state and hasattr(i.state, "group") else "unstarted",
        )
        for i in issues
    ]

    # Load BLOCKS-type links where both source and target are in this project
    links_result = await session.execute(
        select(IssueLink).where(
            IssueLink.source_issue_id.in_([UUID(iid) for iid in issue_ids]),
            IssueLink.workspace_id == workspace_uuid,
            IssueLink.link_type == IssueLinkType.BLOCKS,
        )
    )
    links = links_result.scalars().all()

    edges: list[DependencyEdge] = []
    adj: dict[str, list[str]] = defaultdict(list)

    for link in links:
        src = str(link.source_issue_id)
        tgt = str(link.target_issue_id)
        if src in issue_ids and tgt in issue_ids:
            edges.append(DependencyEdge(source_id=src, target_id=tgt))
            adj[src].append(tgt)

    # Detect circular dependencies via DFS
    circular_deps = _find_cycles(issue_ids, adj)

    # Compute critical path on the DAG (excluding cyclic nodes)
    cyclic_nodes = {n for cycle in circular_deps for n in cycle}
    clean_ids = issue_ids - cyclic_nodes
    critical_path = _longest_path(clean_ids, adj)

    # Mark critical path edges
    critical_set = set(pairwise(critical_path))
    for edge in edges:
        edge.is_critical = (edge.source_id, edge.target_id) in critical_set

    return DependencyGraphResponse(
        nodes=nodes,
        edges=edges,
        critical_path=critical_path,
        circular_deps=circular_deps,
        has_circular=bool(circular_deps),
    )


# ── Graph Algorithms ─────────────────────────────────────────────────────────


def _find_cycles(node_ids: set[str], adj: dict[str, list[str]]) -> list[list[str]]:
    """Find all cycles in directed graph via DFS."""
    visited: set[str] = set()
    in_stack: set[str] = set()
    cycles: list[list[str]] = []

    def dfs(node: str, path: list[str]) -> None:
        visited.add(node)
        in_stack.add(node)
        path.append(node)
        for neighbor in adj.get(node, []):
            if neighbor not in visited:
                dfs(neighbor, path)
            elif neighbor in in_stack:
                start = path.index(neighbor)
                cycles.append(path[start:])
        path.pop()
        in_stack.discard(node)

    for node in node_ids:
        if node not in visited:
            dfs(node, [])

    return cycles


def _longest_path(node_ids: set[str], adj: dict[str, list[str]]) -> list[str]:
    """Compute longest path in DAG via dynamic programming (topological sort)."""
    if not node_ids:
        return []

    in_degree: dict[str, int] = dict.fromkeys(node_ids, 0)
    for src, targets in adj.items():
        if src in node_ids:
            for tgt in targets:
                if tgt in node_ids:
                    in_degree[tgt] = in_degree.get(tgt, 0) + 1

    # Kahn's algorithm for topological order
    queue: deque[str] = deque(n for n in node_ids if in_degree.get(n, 0) == 0)
    dist: dict[str, int] = dict.fromkeys(node_ids, 0)
    prev: dict[str, str | None] = dict.fromkeys(node_ids)
    topo: list[str] = []

    while queue:
        node = queue.popleft()
        topo.append(node)
        for neighbor in adj.get(node, []):
            if neighbor in node_ids:
                if dist[node] + 1 > dist.get(neighbor, 0):
                    dist[neighbor] = dist[node] + 1
                    prev[neighbor] = node
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

    if not topo:
        return []

    end = max(topo, key=lambda n: dist.get(n, 0))
    path: list[str] = []
    cur: str | None = end
    while cur is not None:
        path.append(cur)
        cur = prev.get(cur)
    return list(reversed(path))
