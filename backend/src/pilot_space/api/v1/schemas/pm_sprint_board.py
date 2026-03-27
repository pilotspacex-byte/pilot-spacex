"""Pydantic schemas for PM Block sprint board endpoints.

T-231: Sprint board data (issues grouped by cycle + state)
T-233: AI-proposed state transition (DD-003 approval flow)

Feature 017: Note Versioning / PM Block Engine — Phase 2b
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SprintBoardIssueCard(BaseModel):
    """A single issue card on the sprint board."""

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
    """A state lane on the sprint board containing issue cards."""

    state_id: str
    state_name: str
    state_group: str
    count: int
    issues: list[SprintBoardIssueCard]


class SprintBoardResponse(BaseModel):
    """Response for the sprint board endpoint (T-231)."""

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


__all__ = [
    "ProposeTransitionRequest",
    "ProposeTransitionResponse",
    "SprintBoardIssueCard",
    "SprintBoardLane",
    "SprintBoardResponse",
]
