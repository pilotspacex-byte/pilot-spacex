"""Pydantic schemas for PM Block Insight endpoints.

T-249: PMBlockInsight CRUD (list / dismiss / batch-dismiss)
T-252: Refresh insights

Feature 017: Note Versioning / PM Block Engine — Phase 2b-2e
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from pilot_space.domain.pm_block_insight import InsightSeverity, PMBlockType


class PMBlockInsightResponse(BaseModel):
    """Response schema for a single PMBlockInsight."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    block_id: str
    block_type: PMBlockType
    insight_type: str
    severity: InsightSeverity
    title: str
    analysis: str
    references: list[str]
    suggested_actions: list[str]
    confidence: float
    dismissed: bool


class RefreshInsightsRequest(BaseModel):
    """Request body for refreshing AI insights for a PM block."""

    block_type: str = Field(..., description="PM block type enum value")
    data: dict[str, object] = Field(default_factory=dict)


__all__ = [
    "PMBlockInsightResponse",
    "RefreshInsightsRequest",
]
