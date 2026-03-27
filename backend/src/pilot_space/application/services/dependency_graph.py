"""Dependency graph service -- DAG construction, cycle detection, critical path.

T-237: Project-scoped issue dependency graph.
Feature 017: Note Versioning / PM Block Engine -- Phase 2c.

All DB access is delegated to ProjectRepository, IssueRepository, and
IssueLinkRepository. Graph algorithms remain as pure module-level functions.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from itertools import pairwise
from uuid import UUID

from pilot_space.domain.exceptions import NotFoundError
from pilot_space.infrastructure.database.models.issue_link import IssueLinkType
from pilot_space.infrastructure.database.repositories.issue_link_repository import (
    IssueLinkRepository,
)
from pilot_space.infrastructure.database.repositories.issue_repository import (
    IssueFilters,
    IssueRepository,
)
from pilot_space.infrastructure.database.repositories.project_repository import (
    ProjectRepository,
)
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)


# -- Result dataclasses --------------------------------------------------------


@dataclass(frozen=True)
class DependencyNode:
    """A node in the dependency graph."""

    id: str
    identifier: str
    name: str
    state: str
    state_group: str


@dataclass(frozen=True)
class DependencyEdge:
    """An edge in the dependency graph."""

    source_id: str
    target_id: str
    is_critical: bool = False


@dataclass
class DependencyGraphResult:
    """Full dependency graph result."""

    nodes: list[DependencyNode] = field(default_factory=list)
    edges: list[DependencyEdge] = field(default_factory=list)
    critical_path: list[str] = field(default_factory=list)
    circular_deps: list[list[str]] = field(default_factory=list)
    has_circular: bool = False


# -- Service -------------------------------------------------------------------


class DependencyGraphService:
    """Business logic for project dependency graph construction and analysis.

    Delegates DB queries for projects/issues/links to their respective
    repositories. Graph algorithms (cycle detection, critical path) remain
    as pure module-level functions.
    """

    def __init__(
        self,
        project_repository: ProjectRepository,
        issue_repository: IssueRepository,
        issue_link_repository: IssueLinkRepository,
    ) -> None:
        self._projects = project_repository
        self._issues = issue_repository
        self._links = issue_link_repository

    async def get_project_graph(
        self,
        project_id: UUID,
        workspace_id: UUID,
    ) -> DependencyGraphResult:
        """Build the full dependency graph for a project.

        Returns nodes, edges, critical path, and circular dependency cycles.
        """
        # Verify project exists in this workspace
        project = await self._projects.get_by_id(project_id)
        if not project or project.workspace_id != workspace_id or project.is_deleted:
            raise NotFoundError("Project not found")

        # Load all non-deleted issues in the project
        issues_page = await self._issues.get_workspace_issues(
            workspace_id,
            filters=IssueFilters(project_id=project_id),
            page_size=10_000,  # effectively unbounded for graph construction
        )
        issues = list(issues_page.items)
        issue_ids = {str(i.id) for i in issues}

        nodes = [
            DependencyNode(
                id=str(i.id),
                identifier=i.identifier,
                name=i.name,
                state=i.state.name if i.state else "Backlog",
                state_group=(
                    i.state.group if i.state and hasattr(i.state, "group") else "unstarted"
                ),
            )
            for i in issues
        ]

        # Load BLOCKS-type links for all issues in the project.
        # IssueLinkRepository.find_by_source is per-issue. We iterate over
        # all project issues (acceptable for typical project sizes < 500;
        # each call is a single indexed DB lookup via the same connection).
        edges: list[DependencyEdge] = []
        adj: dict[str, list[str]] = defaultdict(list)

        for issue in issues:
            src_links = await self._links.find_by_source(
                issue_id=issue.id,
                workspace_id=workspace_id,
                link_type=IssueLinkType.BLOCKS,
            )
            for link in src_links:
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
        marked_edges = [
            DependencyEdge(
                source_id=e.source_id,
                target_id=e.target_id,
                is_critical=(e.source_id, e.target_id) in critical_set,
            )
            for e in edges
        ]

        return DependencyGraphResult(
            nodes=nodes,
            edges=marked_edges,
            critical_path=critical_path,
            circular_deps=circular_deps,
            has_circular=bool(circular_deps),
        )


# -- Graph algorithms (module-level, pure functions) ---------------------------


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
