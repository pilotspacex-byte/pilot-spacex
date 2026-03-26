"""PM Block — Capacity plan endpoints.

T-242: Capacity plan (member hours vs committed)

Feature 017: Note Versioning / PM Block Engine — Phase 2d

Thin router shell -- all business logic delegated to CapacityPlanService.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query
from pydantic import BaseModel

from pilot_space.api.v1.dependencies import CapacityPlanServiceDep
from pilot_space.dependencies.auth import CurrentUserId, SessionDep, require_workspace_member

router = APIRouter(prefix="", tags=["pm-blocks"])


# -- Response Schemas ----------------------------------------------------------


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


# -- Capacity Plan Endpoint (T-242) -------------------------------------------


@router.get(
    "/workspaces/{workspace_id}/capacity-plan",
    response_model=CapacityPlanResponse,
    summary="Capacity plan for a cycle",
)
async def get_capacity_plan(
    workspace_id: Annotated[UUID, Path()],
    session: SessionDep,
    service: CapacityPlanServiceDep,
    cycle_id: Annotated[str, Query(description="Cycle UUID")],
    current_user_id: CurrentUserId,
    _: Annotated[UUID, Depends(require_workspace_member)],
) -> CapacityPlanResponse:
    """Return available vs committed hours per member (FR-053)."""
    result = await service.get_capacity(workspace_id, cycle_id)
    return CapacityPlanResponse(**result)
