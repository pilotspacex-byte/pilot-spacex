"""Domain schemas for AdminDashboardService return types (TENANT-04)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class WorkspaceOverview(BaseModel):
    """List item representing a workspace with aggregated health metrics."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    name: str
    slug: str
    created_at: datetime | None
    member_count: int
    owner_email: str | None
    last_active: datetime | None
    storage_used_bytes: int
    ai_action_count: int
    rate_limit_violation_count: int


class QuotaConfig(BaseModel):
    """Workspace quota configuration."""

    model_config = ConfigDict(frozen=True)

    rate_limit_standard_rpm: int | None
    rate_limit_ai_rpm: int | None
    storage_quota_mb: int | None


class TopMember(BaseModel):
    """Workspace member with activity statistics."""

    model_config = ConfigDict(frozen=True)

    user_id: UUID
    email: str | None
    full_name: str | None
    role: str
    action_count: int


class RecentAIAction(BaseModel):
    """AI action log entry."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    action: str
    resource_type: str
    resource_id: UUID | None
    actor_id: UUID | None
    ai_model: str | None
    ai_token_cost: float | None
    created_at: datetime | None


class WorkspaceDetail(BaseModel):
    """Single workspace detail with metrics, members, and AI action history."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    name: str
    slug: str
    created_at: datetime | None
    member_count: int
    owner_email: str | None
    last_active: datetime | None
    storage_used_bytes: int
    ai_action_count: int
    rate_limit_violation_count: int
    quota: QuotaConfig
    top_members: list[TopMember]
    recent_ai_actions: list[RecentAIAction]


__all__ = [
    "QuotaConfig",
    "RecentAIAction",
    "TopMember",
    "WorkspaceDetail",
    "WorkspaceOverview",
]
