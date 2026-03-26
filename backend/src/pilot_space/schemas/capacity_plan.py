"""Domain schemas for CapacityPlanService return types."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MemberCapacity(BaseModel):
    """Individual member utilization for a sprint cycle."""

    model_config = ConfigDict(frozen=True)

    user_id: UUID
    display_name: str
    avatar_url: str | None
    available_hours: float
    committed_hours: float
    utilization_pct: float
    is_over_allocated: bool


class CapacityPlanResponse(BaseModel):
    """Team capacity overview for a cycle."""

    model_config = ConfigDict(frozen=True)

    cycle_id: str
    cycle_name: str
    members: list[MemberCapacity]
    team_available: float
    team_committed: float
    team_utilization_pct: float
    has_data: bool


__all__ = [
    "CapacityPlanResponse",
    "MemberCapacity",
]
