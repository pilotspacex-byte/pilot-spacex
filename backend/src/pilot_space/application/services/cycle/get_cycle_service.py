"""Get Cycle service with velocity computation.

T159: Create GetCycleService with velocity computation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pilot_space.infrastructure.database.models import Cycle, CycleStatus
from pilot_space.infrastructure.database.repositories import CycleFilters, CycleMetrics
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from pilot_space.infrastructure.database.repositories import CycleRepository

logger = get_logger(__name__)


@dataclass
class GetCyclePayload:
    """Payload for getting a single cycle.

    Attributes:
        cycle_id: Cycle UUID to retrieve.
        include_metrics: Whether to compute metrics.
    """

    cycle_id: UUID
    include_metrics: bool = True


@dataclass
class GetCycleResult:
    """Result from getting a cycle."""

    cycle: Cycle | None
    metrics: CycleMetrics | None = None
    found: bool = False


@dataclass
class VelocityDataPoint:
    """Single velocity data point for a completed cycle."""

    cycle_id: UUID
    cycle_name: str
    completed_points: int
    committed_points: int
    velocity: float


@dataclass
class VelocityChartResult:
    """Result from velocity chart query."""

    project_id: UUID
    data_points: list[VelocityDataPoint]
    average_velocity: float


@dataclass
class ListCyclesPayload:
    """Payload for listing cycles.

    Attributes:
        workspace_id: Workspace UUID.
        project_id: Project UUID.
        status: Filter by status.
        statuses: Filter by multiple statuses.
        search_term: Search in cycle names.
        cursor: Pagination cursor.
        page_size: Items per page.
        sort_by: Column to sort by.
        sort_order: Sort direction.
        include_metrics: Whether to compute metrics for each cycle.
    """

    workspace_id: UUID
    project_id: UUID
    status: CycleStatus | None = None
    statuses: list[CycleStatus] | None = None
    search_term: str | None = None
    cursor: str | None = None
    page_size: int = 20
    sort_by: str = "sequence"
    sort_order: str = "desc"
    include_metrics: bool = False


@dataclass
class ListCyclesResult:
    """Result from listing cycles."""

    items: Sequence[Cycle]
    metrics: dict[str, CycleMetrics] = field(default_factory=dict)  # cycle_id -> metrics
    total: int = 0
    next_cursor: str | None = None
    prev_cursor: str | None = None
    has_next: bool = False
    has_prev: bool = False
    page_size: int = 20


class GetCycleService:
    """Service for retrieving cycles with metrics.

    Handles:
    - Single cycle retrieval
    - Paginated cycle listing
    - Velocity and burndown metrics computation
    """

    def __init__(
        self,
        cycle_repository: CycleRepository,
    ) -> None:
        """Initialize service.

        Args:
            cycle_repository: Cycle repository.
        """
        self._cycle_repo = cycle_repository

    async def execute(self, payload: GetCyclePayload) -> GetCycleResult:
        """Get a cycle by ID with optional metrics.

        Args:
            payload: Get cycle parameters.

        Returns:
            GetCycleResult with cycle and metrics.
        """
        cycle = await self._cycle_repo.get_by_id_with_relations(payload.cycle_id)

        if not cycle:
            return GetCycleResult(cycle=None, found=False)

        metrics = None
        if payload.include_metrics:
            metrics = await self._cycle_repo.get_cycle_metrics(payload.cycle_id)

        return GetCycleResult(
            cycle=cycle,
            metrics=metrics,
            found=True,
        )

    async def get_active_cycle(
        self,
        project_id: UUID,
        *,
        include_metrics: bool = True,
    ) -> GetCycleResult:
        """Get the active cycle for a project.

        Args:
            project_id: Project UUID.
            include_metrics: Whether to compute metrics.

        Returns:
            GetCycleResult with active cycle and metrics.
        """
        cycle = await self._cycle_repo.get_active_cycle(project_id)

        if not cycle:
            return GetCycleResult(cycle=None, found=False)

        metrics = None
        if include_metrics:
            metrics = await self._cycle_repo.get_cycle_metrics(cycle.id)

        return GetCycleResult(
            cycle=cycle,
            metrics=metrics,
            found=True,
        )

    async def list_cycles(self, payload: ListCyclesPayload) -> ListCyclesResult:
        """List cycles for a project with pagination.

        Args:
            payload: List cycles parameters.

        Returns:
            ListCyclesResult with cycles and pagination info.
        """
        filters = CycleFilters(
            project_id=payload.project_id,
            status=payload.status,
            statuses=payload.statuses,
            search_term=payload.search_term,
        )

        page = await self._cycle_repo.get_by_project(
            project_id=payload.project_id,
            filters=filters,
            cursor=payload.cursor,
            page_size=payload.page_size,
            sort_by=payload.sort_by,
            sort_order=payload.sort_order,
        )

        # Compute metrics if requested
        metrics: dict[str, CycleMetrics] = {}
        if payload.include_metrics:
            for cycle in page.items:
                cycle_metrics = await self._cycle_repo.get_cycle_metrics(cycle.id)
                if cycle_metrics:
                    metrics[str(cycle.id)] = cycle_metrics

        return ListCyclesResult(
            items=page.items,
            metrics=metrics,
            total=page.total,
            next_cursor=page.next_cursor,
            prev_cursor=page.prev_cursor,
            has_next=page.has_next,
            has_prev=page.has_prev,
            page_size=page.page_size,
        )

    async def get_velocity_chart(
        self,
        project_id: UUID,
        workspace_id: UUID,
        *,
        limit: int = 10,
    ) -> VelocityChartResult:
        """Get velocity chart data for a project.

        Returns velocity data points from the most recent completed cycles.
        Scoped to workspace_id to enforce tenant isolation.

        Args:
            project_id: Project UUID.
            workspace_id: Workspace UUID — enforces tenant isolation boundary.
            limit: Maximum number of cycles to include.

        Returns:
            VelocityChartResult with data points and average.
        """
        pairs = await self._cycle_repo.get_completed_cycles_with_metrics(
            project_id, workspace_id, limit=limit
        )

        data_points: list[VelocityDataPoint] = []
        total_velocity = 0.0

        # Reverse to show oldest first (chronological order)
        for cycle, metrics in reversed(pairs):
            point = VelocityDataPoint(
                cycle_id=cycle.id,
                cycle_name=cycle.name,
                completed_points=metrics.completed_points,
                committed_points=metrics.total_points,
                velocity=metrics.velocity,
            )
            data_points.append(point)
            total_velocity += metrics.velocity

        average_velocity = total_velocity / len(data_points) if data_points else 0.0

        return VelocityChartResult(
            project_id=project_id,
            data_points=data_points,
            average_velocity=average_velocity,
        )


__all__ = [
    "GetCyclePayload",
    "GetCycleResult",
    "GetCycleService",
    "ListCyclesPayload",
    "ListCyclesResult",
    "VelocityChartResult",
    "VelocityDataPoint",
]
