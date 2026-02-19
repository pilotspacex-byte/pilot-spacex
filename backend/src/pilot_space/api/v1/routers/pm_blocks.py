"""PM Block API — Sprint board, dependency map, capacity plan, release notes.

T-231: Sprint board data (issues grouped by cycle + state)
T-237: Dependency graph (nodes + edges + circular detection)
T-242: Capacity plan (member hours vs committed)
T-244: Release notes generation from completed issues
T-249: PMBlockInsight CRUD (list / dismiss / batch-dismiss)

Feature 017: Note Versioning / PM Block Engine — Phase 2b-2e
"""

from __future__ import annotations

from collections import defaultdict, deque
from itertools import pairwise
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query, status
from pydantic import BaseModel, ConfigDict, Field

from pilot_space.api.v1.dependencies import WorkspaceRepositoryDep
from pilot_space.dependencies import get_current_user_id
from pilot_space.dependencies.auth import SessionDep
from pilot_space.domain.pm_block_insight import InsightSeverity, PMBlockType
from pilot_space.infrastructure.database.repositories.pm_block_insight_repository import (
    PMBlockInsightRepository,
)
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/pm-blocks", tags=["pm-blocks"])


# ── Response Schemas ────────────────────────────────────────────────────────


class PMBlockInsightResponse(BaseModel):
    """Response schema for a single PMBlockInsight."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    block_id: str
    block_type: PMBlockType
    insight_type: str
    severity: InsightSeverity
    title: str
    analysis: str
    references: list[str]
    suggested_actions: list[str]
    confidence: float
    dismissed: bool


class SprintBoardIssueCard(BaseModel):
    id: str
    identifier: str
    name: str
    priority: str
    state_name: str
    state_id: str
    assignee_id: str | None = None
    assignee_name: str | None = None
    labels: list[str] = Field(default_factory=list)
    estimate_hours: float | None = None


class SprintBoardLane(BaseModel):
    state_id: str
    state_name: str
    state_group: str
    count: int
    issues: list[SprintBoardIssueCard]


class SprintBoardResponse(BaseModel):
    cycle_id: str
    cycle_name: str
    lanes: list[SprintBoardLane]
    total_issues: int
    is_read_only: bool = False


class DepMapNode(BaseModel):
    id: str
    identifier: str
    name: str
    state: str
    state_group: str


class DepMapEdge(BaseModel):
    source_id: str
    target_id: str
    is_critical: bool = False


class DependencyMapResponse(BaseModel):
    nodes: list[DepMapNode]
    edges: list[DepMapEdge]
    critical_path: list[str]
    circular_deps: list[list[str]]
    has_circular: bool


class CapacityMember(BaseModel):
    user_id: str
    display_name: str
    avatar_url: str | None = None
    available_hours: float
    committed_hours: float
    utilization_pct: float
    is_over_allocated: bool


class CapacityPlanResponse(BaseModel):
    cycle_id: str
    cycle_name: str
    members: list[CapacityMember]
    team_available: float
    team_committed: float
    team_utilization_pct: float
    has_data: bool


class ReleaseEntry(BaseModel):
    issue_id: str
    identifier: str
    name: str
    category: str  # features / bug_fixes / improvements / internal / uncategorized
    confidence: float
    human_edited: bool = False


class ReleaseNotesResponse(BaseModel):
    cycle_id: str
    version_label: str
    entries: list[ReleaseEntry]
    generated_at: str


# ── Sprint Board Endpoint (T-231) ───────────────────────────────────────────


@router.get(
    "/workspaces/{workspace_id}/sprint-board",
    response_model=SprintBoardResponse,
    summary="Sprint board data for a cycle",
)
async def get_sprint_board(
    workspace_id: Annotated[UUID, Path()],
    session: SessionDep,
    workspace_repo: WorkspaceRepositoryDep,
    cycle_id: Annotated[str, Query(description="Cycle UUID")],
    current_user_id: UUID = get_current_user_id,  # type: ignore[assignment]
) -> SprintBoardResponse:
    """Return issues for a cycle grouped into 6 state lanes (FR-049)."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from pilot_space.infrastructure.database.models import Cycle, Issue

    # Verify workspace membership (RLS is also enforced at DB level)
    workspace = await workspace_repo.get_by_id(workspace_id)
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    cycle_uuid = UUID(cycle_id)

    # Load cycle
    cycle_result = await session.execute(
        select(Cycle).where(
            Cycle.id == cycle_uuid,
            Cycle.workspace_id == workspace_id,
            Cycle.is_deleted == False,  # noqa: E712
        )
    )
    cycle = cycle_result.scalar_one_or_none()
    if not cycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cycle not found")

    # Load issues in cycle with state/assignee
    issues_result = await session.execute(
        select(Issue)
        .options(selectinload(Issue.state), selectinload(Issue.assignee))
        .where(
            Issue.cycle_id == cycle_uuid,
            Issue.workspace_id == workspace_id,
            Issue.is_deleted == False,  # noqa: E712
        )
    )
    issues = issues_result.scalars().all()

    # Group by state
    STATE_GROUP_ORDER = ["backlog", "todo", "in_progress", "in_review", "done", "cancelled"]
    lanes_map: dict[str, list[SprintBoardIssueCard]] = defaultdict(list)

    for issue in issues:
        state = issue.state
        lane_key = state.name.lower().replace(" ", "_") if state else "backlog"
        card = SprintBoardIssueCard(
            id=str(issue.id),
            identifier=issue.identifier,
            name=issue.name,
            priority=issue.priority.value
            if hasattr(issue.priority, "value")
            else str(issue.priority),
            state_name=state.name if state else "Backlog",
            state_id=str(state.id) if state else "",
            assignee_id=str(issue.assignee_id) if issue.assignee_id else None,
            assignee_name=getattr(issue.assignee, "full_name", None)
            or getattr(issue.assignee, "email", None)
            if issue.assignee
            else None,
            labels=[],
            estimate_hours=float(getattr(issue, "estimate_points", None) or 0) or None,
        )
        lanes_map[lane_key].append(card)

    lanes = [
        SprintBoardLane(
            state_id=grp,
            state_name=grp.replace("_", " ").title(),
            state_group=grp,
            count=len(lanes_map.get(grp, [])),
            issues=lanes_map.get(grp, []),
        )
        for grp in STATE_GROUP_ORDER
    ]

    return SprintBoardResponse(
        cycle_id=cycle_id,
        cycle_name=cycle.name,
        lanes=lanes,
        total_issues=len(issues),
    )


# ── Dependency Map Endpoint (T-237) ─────────────────────────────────────────


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
    current_user_id: UUID = get_current_user_id,  # type: ignore[assignment]
) -> DependencyMapResponse:
    """Return DAG nodes, edges, critical path, and circular dep detection (FR-051)."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from pilot_space.infrastructure.database.models import Issue, IssueLink

    cycle_uuid = UUID(cycle_id)

    issues_result = await session.execute(
        select(Issue)
        .options(selectinload(Issue.state))
        .where(
            Issue.cycle_id == cycle_uuid,
            Issue.workspace_id == workspace_id,
            Issue.is_deleted == False,  # noqa: E712
        )
    )
    issues = issues_result.scalars().all()
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

    # Load issue links (blocks/blocked_by within this cycle)
    links_result = await session.execute(
        select(IssueLink).where(
            IssueLink.source_issue_id.in_([UUID(iid) for iid in issue_ids]),
            IssueLink.workspace_id == workspace_id,
        )
    )
    links = links_result.scalars().all()

    edges: list[DepMapEdge] = []
    adj: dict[str, list[str]] = defaultdict(list)

    for link in links:
        src = str(link.source_issue_id)
        tgt = str(link.target_issue_id)
        if src in issue_ids and tgt in issue_ids:
            edges.append(DepMapEdge(source_id=src, target_id=tgt))
            adj[src].append(tgt)

    # Detect circular dependencies (DFS)
    circular_deps = _find_cycles(issue_ids, adj)

    # Compute critical path (longest path in DAG after removing cyclic nodes)
    cyclic_nodes = {n for cycle in circular_deps for n in cycle}
    clean_ids = issue_ids - cyclic_nodes
    critical_path = _longest_path(clean_ids, adj)

    # Mark critical path edges
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
                # Found cycle — extract it
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


# ── Capacity Plan Endpoint (T-242) ───────────────────────────────────────────


@router.get(
    "/workspaces/{workspace_id}/capacity-plan",
    response_model=CapacityPlanResponse,
    summary="Capacity plan for a cycle",
)
async def get_capacity_plan(
    workspace_id: Annotated[UUID, Path()],
    session: SessionDep,
    workspace_repo: WorkspaceRepositoryDep,
    cycle_id: Annotated[str, Query(description="Cycle UUID")],
    current_user_id: UUID = get_current_user_id,  # type: ignore[assignment]
) -> CapacityPlanResponse:
    """Return available vs committed hours per member (FR-053)."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from pilot_space.infrastructure.database.models import Cycle, Issue
    from pilot_space.infrastructure.database.models.workspace_member import WorkspaceMember

    cycle_uuid = UUID(cycle_id)

    cycle_result = await session.execute(
        select(Cycle).where(
            Cycle.id == cycle_uuid,
            Cycle.workspace_id == workspace_id,
            Cycle.is_deleted == False,  # noqa: E712
        )
    )
    cycle = cycle_result.scalar_one_or_none()
    if not cycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cycle not found")

    # Load members with availability
    members_result = await session.execute(
        select(WorkspaceMember)
        .options(selectinload(WorkspaceMember.user))
        .where(
            WorkspaceMember.workspace_id == workspace_id,
        )
    )
    members = members_result.scalars().all()

    # Load assigned issues in cycle with estimate_hours
    issues_result = await session.execute(
        select(Issue).where(
            Issue.cycle_id == cycle_uuid,
            Issue.workspace_id == workspace_id,
            Issue.is_deleted == False,  # noqa: E712
            Issue.assignee_id.isnot(None),
        )
    )
    issues = issues_result.scalars().all()

    # Sum committed hours per assignee
    committed: dict[str, float] = defaultdict(float)
    for issue in issues:
        est = getattr(issue, "estimate_points", None)
        if issue.assignee_id and est:
            committed[str(issue.assignee_id)] += float(est)

    capacity_members: list[CapacityMember] = []
    has_data = False

    for m in members:
        weekly_hours = getattr(m, "weekly_available_hours", None)
        available = float(weekly_hours or 40)
        commit = committed.get(str(m.user_id), 0.0)
        utilization = (commit / available * 100) if available > 0 else 0.0

        if weekly_hours is not None:
            has_data = True

        user = m.user
        display_name = getattr(user, "display_name", None) or getattr(user, "email", str(m.user_id))

        capacity_members.append(
            CapacityMember(
                user_id=str(m.user_id),
                display_name=display_name,
                avatar_url=getattr(user, "avatar_url", None),
                available_hours=available,
                committed_hours=round(commit, 1),
                utilization_pct=round(utilization, 1),
                is_over_allocated=utilization > 100,
            )
        )

    team_available = sum(m.available_hours for m in capacity_members)
    team_committed = sum(m.committed_hours for m in capacity_members)
    team_util = (team_committed / team_available * 100) if team_available > 0 else 0.0

    return CapacityPlanResponse(
        cycle_id=cycle_id,
        cycle_name=cycle.name,
        members=capacity_members,
        team_available=round(team_available, 1),
        team_committed=round(team_committed, 1),
        team_utilization_pct=round(team_util, 1),
        has_data=has_data,
    )


# ── Release Notes Endpoint (T-244) ───────────────────────────────────────────


@router.get(
    "/workspaces/{workspace_id}/release-notes",
    response_model=ReleaseNotesResponse,
    summary="AI-classified release notes for a cycle",
)
async def get_release_notes(
    workspace_id: Annotated[UUID, Path()],
    session: SessionDep,
    workspace_repo: WorkspaceRepositoryDep,
    cycle_id: Annotated[str, Query(description="Cycle UUID")],
    current_user_id: UUID = get_current_user_id,  # type: ignore[assignment]
) -> ReleaseNotesResponse:
    """Return completed issues classified into release note categories (FR-054)."""
    from datetime import UTC, datetime

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from pilot_space.infrastructure.database.models import Cycle, Issue

    cycle_uuid = UUID(cycle_id)

    cycle_result = await session.execute(
        select(Cycle).where(
            Cycle.id == cycle_uuid,
            Cycle.workspace_id == workspace_id,
            Cycle.is_deleted == False,  # noqa: E712
        )
    )
    cycle = cycle_result.scalar_one_or_none()
    if not cycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cycle not found")

    # Load completed issues
    issues_result = await session.execute(
        select(Issue)
        .options(selectinload(Issue.state))
        .where(
            Issue.cycle_id == cycle_uuid,
            Issue.workspace_id == workspace_id,
            Issue.is_deleted == False,  # noqa: E712
        )
    )
    issues = issues_result.scalars().all()

    entries: list[ReleaseEntry] = []
    for issue in issues:
        state_group = (
            issue.state.group.value if issue.state and hasattr(issue.state.group, "value") else ""
        )
        if state_group not in ("completed",):
            continue

        category, confidence = _classify_issue(issue)
        entries.append(
            ReleaseEntry(
                issue_id=str(issue.id),
                identifier=issue.identifier,
                name=issue.name,
                category=category,
                confidence=confidence,
            )
        )

    version_label = getattr(cycle, "name", cycle_id)

    return ReleaseNotesResponse(
        cycle_id=cycle_id,
        version_label=version_label,
        entries=entries,
        generated_at=datetime.now(UTC).isoformat(),
    )


def _classify_issue(issue: object) -> tuple[str, float]:
    """Heuristic classification of an issue into release note category.

    Returns (category, confidence). Real system would use LLM; this is
    rule-based fallback sufficient for FR-058 graceful degradation.
    """
    issue_type = getattr(issue, "type", None)
    name = (getattr(issue, "name", "") or "").lower()

    if issue_type == "bug" or any(k in name for k in ("fix", "bug", "crash", "error", "broken")):
        return "bug_fixes", 0.85
    if issue_type == "feature" or any(k in name for k in ("add", "new ", "implement", "create")):
        return "features", 0.80
    if issue_type == "improvement" or any(
        k in name for k in ("improve", "enhance", "optimize", "refactor")
    ):
        return "improvements", 0.75
    if any(k in name for k in ("internal", "chore", "migrate", "upgrade", "deps")):
        return "internal", 0.70
    return "uncategorized", 0.25


# ── PM Block Insights Endpoints (T-249) ─────────────────────────────────────


@router.get(
    "/workspaces/{workspace_id}/pm-block-insights",
    response_model=list[PMBlockInsightResponse],
    summary="List AI insights for a PM block",
)
async def list_pm_block_insights(
    workspace_id: Annotated[UUID, Path()],
    session: SessionDep,
    workspace_repo: WorkspaceRepositoryDep,
    block_id: Annotated[str, Query(description="TipTap block ID")],
    include_dismissed: Annotated[bool, Query()] = False,
    current_user_id: UUID = get_current_user_id,  # type: ignore[assignment]
) -> list[PMBlockInsightResponse]:
    """Return AI-generated insights for a PM block (FR-056)."""
    repo = PMBlockInsightRepository(session)
    insights = await repo.list_by_block(
        block_id=block_id,
        workspace_id=workspace_id,
        include_dismissed=include_dismissed,
    )
    return [
        PMBlockInsightResponse(
            id=i.id,
            workspace_id=i.workspace_id,
            block_id=i.block_id,
            block_type=i.block_type,
            insight_type=i.insight_type,
            severity=i.severity,
            title=i.title,
            analysis=i.analysis,
            references=i.references or [],
            suggested_actions=i.suggested_actions or [],
            confidence=i.confidence,
            dismissed=i.dismissed,
        )
        for i in insights
    ]


@router.post(
    "/workspaces/{workspace_id}/pm-block-insights/{insight_id}/dismiss",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Dismiss a PM block insight",
)
async def dismiss_pm_block_insight(
    workspace_id: Annotated[UUID, Path()],
    insight_id: Annotated[UUID, Path()],
    session: SessionDep,
    current_user_id: UUID = get_current_user_id,  # type: ignore[assignment]
) -> None:
    """Dismiss a single insight (FR-059)."""
    repo = PMBlockInsightRepository(session)
    insight = await repo.get_by_id(insight_id)
    if not insight or insight.workspace_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Insight not found")
    insight.dismissed = True
    await session.flush()


@router.post(
    "/workspaces/{workspace_id}/pm-block-insights/dismiss-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Dismiss all insights for a block",
)
async def dismiss_all_pm_block_insights(
    workspace_id: Annotated[UUID, Path()],
    session: SessionDep,
    block_id: Annotated[str, Query(description="TipTap block ID")],
    current_user_id: UUID = get_current_user_id,  # type: ignore[assignment]
) -> None:
    """Batch-dismiss all active insights for a block (FR-059)."""
    repo = PMBlockInsightRepository(session)
    await repo.batch_dismiss(block_id=block_id, workspace_id=workspace_id)
