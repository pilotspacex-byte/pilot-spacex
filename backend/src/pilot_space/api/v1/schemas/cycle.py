"""Cycle API schemas.

T162: Create Cycle Pydantic schemas for API layer.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from pilot_space.api.v1.schemas.base import BaseSchema
from pilot_space.api.v1.schemas.issue import IssueBriefResponse, UserBriefSchema
from pilot_space.infrastructure.database.models import CycleStatus

__all__: list[str] = []  # Defined at end of file


# ============================================================================
# Request Schemas
# ============================================================================


class CycleCreateRequest(BaseSchema):
    """Request to create a cycle."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    project_id: UUID
    start_date: date | None = None
    end_date: date | None = None
    owned_by_id: UUID | None = None
    status: CycleStatus = CycleStatus.DRAFT


class CycleUpdateRequest(BaseSchema):
    """Request to update a cycle."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: CycleStatus | None = None
    owned_by_id: UUID | None = None

    # Explicit clear flags
    clear_description: bool = False
    clear_start_date: bool = False
    clear_end_date: bool = False
    clear_owner: bool = False


class AddIssueToCycleRequest(BaseSchema):
    """Request to add an issue to a cycle."""

    issue_id: UUID


class BulkAddIssuesToCycleRequest(BaseSchema):
    """Request to add multiple issues to a cycle."""

    issue_ids: list[UUID] = Field(..., min_length=1, max_length=100)


class RolloverCycleRequest(BaseSchema):
    """Request to rollover a cycle."""

    target_cycle_id: UUID
    issue_ids: list[UUID] | None = None
    include_in_progress: bool = True
    complete_source_cycle: bool = True


# ============================================================================
# Response Schemas
# ============================================================================


class ProjectBriefSchema(BaseSchema):
    """Brief project information for nested responses."""

    id: UUID
    name: str
    identifier: str


class CycleMetricsResponse(BaseSchema):
    """Cycle metrics response."""

    cycle_id: UUID
    total_issues: int
    completed_issues: int
    in_progress_issues: int
    not_started_issues: int
    total_points: int
    completed_points: int
    completion_percentage: float
    velocity: float  # Points per day


class CycleResponse(BaseSchema):
    """Full cycle response."""

    id: UUID
    workspace_id: UUID
    name: str
    description: str | None
    status: CycleStatus
    start_date: date | None
    end_date: date | None
    sequence: int
    created_at: datetime
    updated_at: datetime

    # Relations
    project: ProjectBriefSchema
    owned_by: UserBriefSchema | None

    # Optional metrics
    metrics: CycleMetricsResponse | None = None

    # Issue count (for list views)
    issue_count: int = 0

    @classmethod
    def from_cycle(
        cls,
        cycle: Any,
        *,
        metrics: Any | None = None,
        issue_count: int = 0,
    ) -> CycleResponse:
        """Create from Cycle model.

        Args:
            cycle: Cycle model instance.
            metrics: Optional CycleMetrics dataclass.
            issue_count: Number of issues in cycle.

        Returns:
            CycleResponse instance.
        """
        metrics_response = None
        if metrics:
            metrics_response = CycleMetricsResponse(
                cycle_id=metrics.cycle_id,
                total_issues=metrics.total_issues,
                completed_issues=metrics.completed_issues,
                in_progress_issues=metrics.in_progress_issues,
                not_started_issues=metrics.not_started_issues,
                total_points=metrics.total_points,
                completed_points=metrics.completed_points,
                completion_percentage=metrics.completion_percentage,
                velocity=metrics.velocity,
            )

        return cls(
            id=cycle.id,
            workspace_id=cycle.workspace_id,
            name=cycle.name,
            description=cycle.description,
            status=cycle.status,
            start_date=cycle.start_date,
            end_date=cycle.end_date,
            sequence=cycle.sequence,
            created_at=cycle.created_at,
            updated_at=cycle.updated_at,
            project=ProjectBriefSchema.model_validate(cycle.project),
            owned_by=(UserBriefSchema.model_validate(cycle.owned_by) if cycle.owned_by else None),
            metrics=metrics_response,
            issue_count=issue_count,
        )


class CycleListResponse(BaseSchema):
    """Paginated cycle list response."""

    items: list[CycleResponse]
    total: int
    next_cursor: str | None
    prev_cursor: str | None
    has_next: bool
    has_prev: bool
    page_size: int


class CycleBriefResponse(BaseSchema):
    """Brief cycle response for lists and references."""

    id: UUID
    name: str
    status: CycleStatus
    start_date: date | None
    end_date: date | None


class RolloverCycleResponse(BaseSchema):
    """Response from cycle rollover."""

    source_cycle: CycleResponse
    target_cycle: CycleResponse
    rolled_over_issues: list[IssueBriefResponse]
    skipped_count: int
    total_rolled_over: int


# ============================================================================
# Burndown Chart Data
# ============================================================================


class BurndownDataPoint(BaseSchema):
    """Single data point for burndown chart."""

    date: date
    remaining_points: int
    remaining_issues: int
    ideal_points: float
    ideal_issues: float


class BurndownChartResponse(BaseSchema):
    """Burndown chart data response."""

    cycle_id: UUID
    start_date: date
    end_date: date
    total_points: int
    total_issues: int
    data_points: list[BurndownDataPoint]


# ============================================================================
# Velocity Chart Data
# ============================================================================


class VelocityDataPoint(BaseSchema):
    """Single data point for velocity chart."""

    cycle_id: UUID
    cycle_name: str
    completed_points: int
    committed_points: int
    velocity: float  # Points per day


class VelocityChartResponse(BaseSchema):
    """Velocity chart data across cycles."""

    project_id: UUID
    data_points: list[VelocityDataPoint]
    average_velocity: float


__all__ = [
    "AddIssueToCycleRequest",
    "BulkAddIssuesToCycleRequest",
    "BurndownChartResponse",
    "BurndownDataPoint",
    "CycleBriefResponse",
    "CycleCreateRequest",
    "CycleListResponse",
    "CycleMetricsResponse",
    "CycleResponse",
    "CycleUpdateRequest",
    "ProjectBriefSchema",
    "RolloverCycleRequest",
    "RolloverCycleResponse",
    "VelocityChartResponse",
    "VelocityDataPoint",
]
