"""PM Block — Sprint board endpoints.

T-231: Sprint board data (issues grouped by cycle + state)
T-233: AI-proposed state transition (DD-003 approval flow)

Feature 017: Note Versioning / PM Block Engine — Phase 2b
"""

from __future__ import annotations

from collections import defaultdict
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status
from pydantic import BaseModel, Field

from pilot_space.api.v1.dependencies import WorkspaceRepositoryDep
from pilot_space.dependencies.auth import CurrentUserId, SessionDep, require_workspace_member
from pilot_space.domain.exceptions import NotFoundError
from pilot_space.infrastructure.database.repositories.pm_block_queries_repository import (
    PMBlockQueriesRepository,
)

router = APIRouter(prefix="", tags=["pm-blocks"])


# ── Response Schemas ──────────────────────────────────────────────────────────


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


# ── Sprint Board Endpoint (T-231) ─────────────────────────────────────────────

STATE_GROUP_ORDER = ["backlog", "todo", "in_progress", "in_review", "done", "cancelled"]


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
    current_user_id: CurrentUserId,
    _: Annotated[UUID, Depends(require_workspace_member)],
) -> SprintBoardResponse:
    """Return issues for a cycle grouped into 6 state lanes (FR-049)."""
    workspace = await workspace_repo.get_by_id(workspace_id)
    if not workspace:
        raise NotFoundError("Workspace not found")

    cycle_uuid = UUID(cycle_id)
    repo = PMBlockQueriesRepository(session)

    cycle = await repo.get_cycle(cycle_uuid, workspace_id)
    if not cycle:
        raise NotFoundError("Cycle not found")

    issues = await repo.get_cycle_issues_with_state_and_assignee(cycle_uuid, workspace_id)

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

    is_read_only = str(getattr(cycle, "status", "")).lower() in ("completed", "cancelled")

    return SprintBoardResponse(
        cycle_id=cycle_id,
        cycle_name=cycle.name,
        lanes=lanes,
        total_issues=len(issues),
        is_read_only=is_read_only,
    )


# ── AI State Transition Proposal Endpoint (T-233) ─────────────────────────────


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
    current_user_id: CurrentUserId,
    _: Annotated[UUID, Depends(require_workspace_member)],
) -> ProposeTransitionResponse:
    """Create an approval request for an AI-proposed state transition (FR-050).

    The caller (sprint board "Move →" button or AI orchestrator) submits the
    proposal; a human must approve it via the standard approvals flow (DD-003)
    before the issue state is mutated.
    """
    from pilot_space.ai.infrastructure.approval import ActionType, ApprovalService

    approval_service = ApprovalService(session=session)
    approval_id = await approval_service.create_approval_request(
        workspace_id=workspace_id,
        user_id=current_user_id,
        action_type=ActionType.TRANSITION_ISSUE_STATE,
        action_data={
            "issue_id": body.issue_id,
            "proposed_state": body.proposed_state,
            "reason": body.reason,
        },
        requested_by_agent="sprint-board-ai",
        context={"workspace_id": str(workspace_id), "issue_id": body.issue_id},
    )
    return ProposeTransitionResponse(approval_id=str(approval_id))
