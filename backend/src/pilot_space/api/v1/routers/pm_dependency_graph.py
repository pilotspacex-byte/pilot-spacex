"""PM Block — Dependency graph endpoints.

T-237: Dependency graph (nodes + edges + circular detection)

Feature 017: Note Versioning / PM Block Engine — Phase 2c
"""

from __future__ import annotations

from collections import defaultdict, deque
from itertools import pairwise
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query

from pilot_space.api.v1.dependencies import WorkspaceRepositoryDep
from pilot_space.api.v1.schemas.pm_dependency_graph import (
    DependencyMapResponse,
    DepMapEdge,
    DepMapNode,
)
from pilot_space.dependencies.auth import CurrentUserId, SessionDep, require_workspace_member
from pilot_space.infrastructure.database.repositories.pm_block_queries_repository import (
    PMBlockQueriesRepository,
)

router = APIRouter(prefix="", tags=["pm-blocks"])


# ── Graph Algorithms ──────────────────────────────────────────────────────────


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


# ── Dependency Map Endpoint (T-237) ──────────────────────────────────────────


@router.get(
    "/workspaces/{workspace_id}/dependency-map",
    response_model=DependencyMapResponse,
    summary="Dependency graph for a cycle",
)
async def get_dependency_map(
    workspace_id: Annotated[UUID, Path()],
    session: SessionDep,
    workspace_repo: WorkspaceRepositoryDep,
    cycle_id: Annotated[str, Query(description="Cycle UUID")],
    current_user_id: CurrentUserId,
    _: Annotated[UUID, Depends(require_workspace_member)],
) -> DependencyMapResponse:
    """Return DAG nodes, edges, critical path, and circular dep detection (FR-051)."""
    cycle_uuid = UUID(cycle_id)
    repo = PMBlockQueriesRepository(session)

    issues = await repo.get_cycle_issues_with_state(cycle_uuid, workspace_id)
    issue_ids = {str(i.id) for i in issues}

    nodes = [
        DepMapNode(
            id=str(i.id),
            identifier=i.identifier,
            name=i.name,
            state=i.state.name if i.state else "Backlog",
            state_group=i.state.group if i.state and hasattr(i.state, "group") else "unstarted",
        )
        for i in issues
    ]

    links = await repo.get_issue_links_in_cycle([UUID(iid) for iid in issue_ids], workspace_id)

    edges: list[DepMapEdge] = []
    adj: dict[str, list[str]] = defaultdict(list)

    for link in links:
        src = str(link.source_issue_id)
        tgt = str(link.target_issue_id)
        if src in issue_ids and tgt in issue_ids:
            edges.append(DepMapEdge(source_id=src, target_id=tgt))
            adj[src].append(tgt)

    circular_deps = _find_cycles(issue_ids, adj)

    cyclic_nodes = {n for cycle in circular_deps for n in cycle}
    clean_ids = issue_ids - cyclic_nodes
    critical_path = _longest_path(clean_ids, adj)

    critical_set = set(pairwise(critical_path))
    for edge in edges:
        edge.is_critical = (edge.source_id, edge.target_id) in critical_set

    return DependencyMapResponse(
        nodes=nodes,
        edges=edges,
        critical_path=critical_path,
        circular_deps=circular_deps,
        has_circular=bool(circular_deps),
    )
