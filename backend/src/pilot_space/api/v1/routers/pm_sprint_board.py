"""PM Block — Sprint board endpoints.

T-231: Sprint board data (issues grouped by cycle + state)
T-233: AI-proposed state transition (DD-003 approval flow)

Feature 017: Note Versioning / PM Block Engine — Phase 2b

Thin router shell -- all business logic delegated to SprintBoardService.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status
from pydantic import BaseModel, Field

from pilot_space.api.v1.dependencies import SprintBoardServiceDep
from pilot_space.dependencies.auth import CurrentUserId, SessionDep, require_workspace_member

router = APIRouter(prefix="", tags=["pm-blocks"])


# -- Response Schemas ----------------------------------------------------------


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


class ProposeTransitionRequest(BaseModel):
    """Request body for an AI-proposed issue state transition."""

    issue_id: str = Field(..., description="Issue UUID to transition")
    proposed_state: str = Field(..., description="Target state group key")
    reason: str | None = Field(None, description="AI rationale for the proposal")


class ProposeTransitionResponse(BaseModel):
    """Response confirming the approval request was created."""

    approval_id: str
    status: str = "pending"


# -- Sprint Board Endpoint (T-231) --------------------------------------------


@router.get(
    "/workspaces/{workspace_id}/sprint-board",
    response_model=SprintBoardResponse,
    summary="Sprint board data for a cycle",
)
async def get_sprint_board(
    workspace_id: Annotated[UUID, Path()],
    session: SessionDep,
    service: SprintBoardServiceDep,
    cycle_id: Annotated[str, Query(description="Cycle UUID")],
    current_user_id: CurrentUserId,
    _: Annotated[UUID, Depends(require_workspace_member)],
) -> SprintBoardResponse:
    """Return issues for a cycle grouped into 6 state lanes (FR-049)."""
    result = await service.get_board(workspace_id, cycle_id)
    return SprintBoardResponse(**result)


# -- AI State Transition Proposal Endpoint (T-233) ----------------------------


@router.post(
    "/workspaces/{workspace_id}/sprint-board/propose-transition",
    response_model=ProposeTransitionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="AI proposes an issue state transition (DD-003)",
)
async def propose_state_transition(
    workspace_id: Annotated[UUID, Path()],
    body: ProposeTransitionRequest,
    session: SessionDep,
    service: SprintBoardServiceDep,
    current_user_id: CurrentUserId,
    _: Annotated[UUID, Depends(require_workspace_member)],
) -> ProposeTransitionResponse:
    """Create an approval request for an AI-proposed state transition (FR-050)."""
    approval_id = await service.propose_transition(
        workspace_id=workspace_id,
        user_id=current_user_id,
        issue_id=body.issue_id,
        proposed_state=body.proposed_state,
        reason=body.reason,
    )
    return ProposeTransitionResponse(approval_id=approval_id)
