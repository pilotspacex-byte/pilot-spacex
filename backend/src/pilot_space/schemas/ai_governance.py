"""Domain schemas for GovernanceRollbackService return types."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RollbackEligibility(BaseModel):
    """Result of a rollback eligibility check.

    Not currently returned as a standalone method; retained for future
    eligibility check endpoints or pre-flight validation.
    """

    model_config = ConfigDict(frozen=True)

    is_eligible: bool
    reason: str | None = None


class RollbackResult(BaseModel):
    """Rollback execution result."""

    model_config = ConfigDict(frozen=True)

    status: str
    entry_id: UUID


class GovernanceAction(BaseModel):
    """AI governance policy row."""

    model_config = ConfigDict(frozen=True)

    role: str
    action_type: str
    requires_approval: bool


class AIStatus(BaseModel):
    """BYOK configuration status for the workspace."""

    model_config = ConfigDict(frozen=True)

    byok_configured: bool
    providers: tuple[str, ...]


__all__ = [
    "AIStatus",
    "GovernanceAction",
    "RollbackEligibility",
    "RollbackResult",
]
