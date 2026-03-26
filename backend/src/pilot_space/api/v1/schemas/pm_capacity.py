"""Pydantic schemas for PM Block capacity plan endpoints.

T-242: Capacity plan (member hours vs committed)

Feature 017: Note Versioning / PM Block Engine — Phase 2d
"""

from __future__ import annotations

from pydantic import BaseModel


class CapacityMember(BaseModel):
    """Capacity data for a single workspace member."""

    user_id: str
    display_name: str
    avatar_url: str | None = None
    available_hours: float
    committed_hours: float
    utilization_pct: float
    is_over_allocated: bool


class CapacityPlanResponse(BaseModel):
    """Response for the capacity plan endpoint (T-242)."""

    cycle_id: str
    cycle_name: str
    members: list[CapacityMember]
    team_available: float
    team_committed: float
    team_utilization_pct: float
    has_data: bool


__all__ = [
    "CapacityMember",
    "CapacityPlanResponse",
]
