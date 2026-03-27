"""Domain schemas for SprintBoardService return types."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SprintBoardCard(BaseModel):
    """A single issue card on the sprint board."""

    model_config = ConfigDict(frozen=True)

    id: str
    identifier: str | None
    name: str
    priority: str
    state_name: str
    state_id: str
    assignee_id: str | None
    assignee_name: str | None
    labels: list[str]
    estimate_hours: float | None


class SprintBoardLane(BaseModel):
    """A state lane containing issue cards."""

    model_config = ConfigDict(frozen=True)

    state_id: str
    state_name: str
    state_group: str
    count: int
    issues: list[SprintBoardCard]


class SprintBoardResponse(BaseModel):
    """Full sprint board response for a cycle."""

    model_config = ConfigDict(frozen=True)

    cycle_id: str
    cycle_name: str
    lanes: list[SprintBoardLane]
    total_issues: int
    is_read_only: bool


class TransitionProposal(BaseModel):
    """AI state transition proposal result — contains the approval ID."""

    model_config = ConfigDict(frozen=True)

    approval_id: str


__all__ = [
    "SprintBoardCard",
    "SprintBoardLane",
    "SprintBoardResponse",
    "TransitionProposal",
]
