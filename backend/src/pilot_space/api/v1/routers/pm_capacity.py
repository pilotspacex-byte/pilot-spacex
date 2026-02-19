"""PM Block — Capacity plan endpoints.

T-242: Capacity plan (member hours vs committed)

Feature 017: Note Versioning / PM Block Engine — Phase 2d
"""

from __future__ import annotations

from collections import defaultdict
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query, status
from pydantic import BaseModel

from pilot_space.api.v1.dependencies import WorkspaceRepositoryDep
from pilot_space.dependencies.auth import CurrentUserId, SessionDep
from pilot_space.infrastructure.database.repositories.pm_block_queries_repository import (
    PMBlockQueriesRepository,
)

router = APIRouter(prefix="", tags=["pm-blocks"])


# ── Response Schemas ──────────────────────────────────────────────────────────


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


# ── Capacity Plan Endpoint (T-242) ────────────────────────────────────────────


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
    current_user_id: CurrentUserId,
) -> CapacityPlanResponse:
    """Return available vs committed hours per member (FR-053)."""
    cycle_uuid = UUID(cycle_id)
    repo = PMBlockQueriesRepository(session)

    cycle = await repo.get_cycle(cycle_uuid, workspace_id)
    if not cycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cycle not found")

    members = await repo.get_workspace_members_with_user(workspace_id)
    issues = await repo.get_cycle_assigned_issues(cycle_uuid, workspace_id)

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
