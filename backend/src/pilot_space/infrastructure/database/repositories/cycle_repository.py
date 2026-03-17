"""Cycle repository with workspace-scoped queries.

T157: Create CycleRepository with project-scoped queries and metrics.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING, Any

from sqlalchemy import Select, and_, asc, desc, func, select
from sqlalchemy.orm import joinedload, selectinload

from pilot_space.infrastructure.database.models import (
    Cycle,
    CycleStatus,
    Issue,
    StateGroup,
)
from pilot_space.infrastructure.database.repositories.base import (
    BaseRepository,
    CursorPage,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class CycleFilters:
    """Filter parameters for cycle queries.

    All filters are optional and combined with AND logic.
    """

    project_id: UUID | None = None
    status: CycleStatus | None = None
    statuses: list[CycleStatus] | None = None
    start_date_from: date | None = None
    start_date_to: date | None = None
    end_date_from: date | None = None
    end_date_to: date | None = None
    owned_by_id: UUID | None = None
    search_term: str | None = None


@dataclass
class CycleMetrics:
    """Metrics for a single cycle.

    Computed from issues assigned to the cycle.
    """

    cycle_id: UUID
    total_issues: int
    completed_issues: int
    in_progress_issues: int
    not_started_issues: int
    total_points: int
    completed_points: int
    completion_percentage: float
    velocity: float  # Completed points per day


class CycleRepository(BaseRepository[Cycle]):
    """Repository for Cycle entities with workspace-scoped queries.

    Provides:
    - Workspace-scoped CRUD operations
    - Project-scoped queries
    - Active cycle retrieval
    - Cycle metrics and velocity calculations
    - Issues in cycle with filtering
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: Async database session.
        """
        super().__init__(session, Cycle)

    async def get_by_id_with_relations(
        self,
        cycle_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Cycle | None:
        """Get cycle by ID with relationships eagerly loaded.

        Args:
            cycle_id: Cycle UUID.
            include_deleted: Whether to include soft-deleted cycles.

        Returns:
            Cycle with relations or None.
        """
        query = (
            select(Cycle)
            .options(
                joinedload(Cycle.project),
                joinedload(Cycle.owned_by),
            )
            .where(Cycle.id == cycle_id)
        )
        if not include_deleted:
            query = query.where(Cycle.is_deleted == False)  # noqa: E712
        result = await self.session.execute(query)
        return result.unique().scalar_one_or_none()

    async def get_by_project(
        self,
        project_id: UUID,
        *,
        filters: CycleFilters | None = None,
        cursor: str | None = None,
        page_size: int = 20,
        sort_by: str = "sequence",
        sort_order: str = "desc",
        include_deleted: bool = False,
    ) -> CursorPage[Cycle]:
        """Get paginated cycles for a project.

        Args:
            project_id: Project UUID.
            filters: Optional filter criteria.
            cursor: Pagination cursor.
            page_size: Items per page (max 100).
            sort_by: Column to sort by (sequence, created_at, start_date).
            sort_order: Sort direction ('asc' or 'desc').
            include_deleted: Whether to include soft-deleted cycles.

        Returns:
            CursorPage with filtered cycles.
        """
        page_size = min(page_size, 100)

        # Build base query with eager loading
        query = (
            select(Cycle)
            .options(
                joinedload(Cycle.project),
                joinedload(Cycle.owned_by),
            )
            .where(Cycle.project_id == project_id)
        )

        if not include_deleted:
            query = query.where(Cycle.is_deleted == False)  # noqa: E712

        # Apply filters
        if filters:
            query = self._apply_cycle_filters(query, filters)

        # Count query
        count_query = select(func.count()).select_from(Cycle).where(Cycle.project_id == project_id)
        if not include_deleted:
            count_query = count_query.where(Cycle.is_deleted == False)  # noqa: E712
        if filters:
            count_query = self._apply_cycle_filters(count_query, filters)  # type: ignore[arg-type]
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        # Get sort column
        sort_column = getattr(Cycle, sort_by, Cycle.sequence)
        order_func = desc if sort_order == "desc" else asc

        # Apply cursor
        if cursor:
            cursor_value = self._decode_cursor(cursor, sort_by)
            if cursor_value:
                if sort_order == "desc":
                    query = query.where(sort_column < cursor_value)
                else:
                    query = query.where(sort_column > cursor_value)

        # Apply ordering and limit
        query = query.order_by(order_func(sort_column)).limit(page_size + 1)

        # Execute
        result = await self.session.execute(query)
        items = list(result.unique().scalars().all())

        # Build pagination info
        has_next = len(items) > page_size
        if has_next:
            items = items[:page_size]

        next_cursor = None
        if has_next and items:
            next_cursor = self._encode_cursor(getattr(items[-1], sort_by))

        prev_cursor = None
        has_prev = cursor is not None
        if has_prev and items:
            prev_cursor = self._encode_cursor(getattr(items[0], sort_by))

        return CursorPage(
            items=items,
            total=total,
            next_cursor=next_cursor,
            prev_cursor=prev_cursor,
            has_next=has_next,
            has_prev=has_prev,
            page_size=page_size,
        )

    async def get_active_cycle(
        self,
        project_id: UUID,
    ) -> Cycle | None:
        """Get the currently active cycle for a project.

        Only one cycle should be active at a time per project.

        Args:
            project_id: Project UUID.

        Returns:
            Active Cycle or None.
        """
        query = (
            select(Cycle)
            .options(
                joinedload(Cycle.project),
                joinedload(Cycle.owned_by),
            )
            .where(
                and_(
                    Cycle.project_id == project_id,
                    Cycle.status == CycleStatus.ACTIVE,
                    Cycle.is_deleted == False,  # noqa: E712
                )
            )
        )
        result = await self.session.execute(query)
        return result.unique().scalar_one_or_none()

    async def get_issues_in_cycle(
        self,
        cycle_id: UUID,
        *,
        include_completed: bool = True,
    ) -> Sequence[Issue]:
        """Get all issues assigned to a cycle.

        Args:
            cycle_id: Cycle UUID.
            include_completed: Whether to include completed/cancelled issues.

        Returns:
            List of issues in the cycle.
        """
        from pilot_space.infrastructure.database.models import State

        query = (
            select(Issue)
            .options(
                joinedload(Issue.state),
                joinedload(Issue.assignee),
                selectinload(Issue.labels),
            )
            .where(
                and_(
                    Issue.cycle_id == cycle_id,
                    Issue.is_deleted == False,  # noqa: E712
                )
            )
        )

        if not include_completed:
            query = query.join(Issue.state).where(
                State.group.notin_([StateGroup.COMPLETED, StateGroup.CANCELLED])
            )

        query = query.order_by(Issue.sort_order, Issue.created_at)
        result = await self.session.execute(query)
        return result.unique().scalars().all()

    async def get_cycle_metrics(
        self,
        cycle_id: UUID,
    ) -> CycleMetrics | None:
        """Calculate metrics for a cycle.

        Args:
            cycle_id: Cycle UUID.

        Returns:
            CycleMetrics with computed values or None if cycle not found.
        """
        from pilot_space.infrastructure.database.models import State

        # Get the cycle first to get duration
        cycle = await self.get_by_id(cycle_id)
        if not cycle:
            return None

        # Get issue counts by state group
        query = (
            select(
                State.group,
                func.count(Issue.id).label("count"),
                func.coalesce(func.sum(Issue.estimate_points), 0).label("points"),
            )
            .select_from(Issue)
            .join(Issue.state)
            .where(
                and_(
                    Issue.cycle_id == cycle_id,
                    Issue.is_deleted == False,  # noqa: E712
                )
            )
            .group_by(State.group)
        )

        result = await self.session.execute(query)
        rows = result.all()

        # Initialize counters
        total_issues = 0
        completed_issues = 0
        in_progress_issues = 0
        not_started_issues = 0
        total_points = 0
        completed_points = 0

        for row in rows:
            group: StateGroup = row[0]
            count: int = row[1]
            points: int = row[2]

            total_issues += count
            total_points += points

            if group == StateGroup.COMPLETED:
                completed_issues += count
                completed_points += points
            elif group in (StateGroup.STARTED, StateGroup.UNSTARTED):
                if group == StateGroup.STARTED:
                    in_progress_issues += count
                else:
                    not_started_issues += count
            elif group == StateGroup.CANCELLED:
                # Cancelled issues don't count towards completion
                total_issues -= count
                total_points -= points

        # Calculate completion percentage
        completion_percentage = 0.0
        if total_issues > 0:
            completion_percentage = (completed_issues / total_issues) * 100

        # Calculate velocity (points per day)
        velocity = 0.0
        if cycle.start_date and cycle.end_date:
            days = (cycle.end_date - cycle.start_date).days
            if days > 0:
                velocity = completed_points / days

        return CycleMetrics(
            cycle_id=cycle_id,
            total_issues=total_issues,
            completed_issues=completed_issues,
            in_progress_issues=in_progress_issues,
            not_started_issues=not_started_issues,
            total_points=total_points,
            completed_points=completed_points,
            completion_percentage=completion_percentage,
            velocity=velocity,
        )

    async def get_metrics_for_cycles(
        self,
        cycle_ids: list[UUID],
    ) -> dict[UUID, CycleMetrics]:
        """Calculate metrics for multiple cycles in a single aggregate query.

        Issues are joined to their state group and aggregated per cycle_id,
        eliminating the N+1 pattern from calling get_cycle_metrics() in a loop.

        Args:
            cycle_ids: List of cycle UUIDs to compute metrics for.

        Returns:
            Mapping of cycle_id -> CycleMetrics. Cycles with no issues are
            not included.
        """
        if not cycle_ids:
            return {}

        from pilot_space.infrastructure.database.models import State

        # Fetch cycles to compute velocity (needs start/end dates)
        cycles_query = select(Cycle).where(Cycle.id.in_(cycle_ids))
        cycles_result = await self.session.execute(cycles_query)
        cycles_by_id: dict[UUID, Cycle] = {c.id: c for c in cycles_result.scalars().all()}

        # Single aggregate query: counts and points per (cycle_id, state_group)
        agg_query = (
            select(
                Issue.cycle_id,
                State.group,
                func.count(Issue.id).label("count"),
                func.coalesce(func.sum(Issue.estimate_points), 0).label("points"),
            )
            .select_from(Issue)
            .join(Issue.state)
            .where(
                and_(
                    Issue.cycle_id.in_(cycle_ids),
                    Issue.is_deleted == False,  # noqa: E712
                )
            )
            .group_by(Issue.cycle_id, State.group)
        )

        agg_result = await self.session.execute(agg_query)
        rows = agg_result.all()

        # Accumulate per-cycle counters, skipping cancelled
        accum: dict[UUID, dict[str, int]] = {}
        for row in rows:
            cid: UUID = row[0]
            group: StateGroup = row[1]
            count: int = row[2]
            points: int = row[3]

            if group == StateGroup.CANCELLED:
                continue

            if cid not in accum:
                accum[cid] = {
                    "total_issues": 0,
                    "completed_issues": 0,
                    "in_progress_issues": 0,
                    "not_started_issues": 0,
                    "total_points": 0,
                    "completed_points": 0,
                }

            accum[cid]["total_issues"] += count
            accum[cid]["total_points"] += points

            if group == StateGroup.COMPLETED:
                accum[cid]["completed_issues"] += count
                accum[cid]["completed_points"] += points
            elif group == StateGroup.STARTED:
                accum[cid]["in_progress_issues"] += count
            elif group == StateGroup.UNSTARTED:
                accum[cid]["not_started_issues"] += count

        metrics: dict[UUID, CycleMetrics] = {}
        for cid, counts in accum.items():
            cycle = cycles_by_id.get(cid)

            total_issues = counts["total_issues"]
            completed_issues = counts["completed_issues"]
            completed_points = counts["completed_points"]

            completion_percentage = (
                (completed_issues / total_issues) * 100 if total_issues > 0 else 0.0
            )

            velocity = 0.0
            if cycle and cycle.start_date and cycle.end_date:
                days = (cycle.end_date - cycle.start_date).days
                if days > 0:
                    velocity = completed_points / days

            metrics[cid] = CycleMetrics(
                cycle_id=cid,
                total_issues=total_issues,
                completed_issues=completed_issues,
                in_progress_issues=counts["in_progress_issues"],
                not_started_issues=counts["not_started_issues"],
                total_points=counts["total_points"],
                completed_points=completed_points,
                completion_percentage=completion_percentage,
                velocity=velocity,
            )

        return metrics

    async def get_completed_cycles_with_metrics(
        self,
        project_id: UUID,
        workspace_id: UUID,
        *,
        limit: int = 10,
    ) -> list[tuple[Cycle, CycleMetrics]]:
        """Get completed cycles with their metrics for velocity chart.

        Returns cycles ordered by sequence descending (most recent first).
        Scoped to the given workspace to enforce tenant isolation.

        Args:
            project_id: Project UUID.
            workspace_id: Workspace UUID — enforces tenant isolation boundary.
            limit: Maximum number of cycles to return.

        Returns:
            List of (cycle, metrics) tuples.
        """
        query = (
            select(Cycle)
            .options(
                joinedload(Cycle.project),
                joinedload(Cycle.owned_by),
            )
            .where(
                and_(
                    Cycle.project_id == project_id,
                    Cycle.workspace_id == workspace_id,
                    Cycle.status == CycleStatus.COMPLETED,
                    Cycle.is_deleted == False,  # noqa: E712
                )
            )
            .order_by(desc(Cycle.sequence))
            .limit(limit)
        )

        result = await self.session.execute(query)
        cycles = list(result.unique().scalars().all())

        if not cycles:
            return []

        cycle_ids = [c.id for c in cycles]
        metrics_map = await self.get_metrics_for_cycles(cycle_ids)

        pairs: list[tuple[Cycle, CycleMetrics]] = []
        for cycle in cycles:
            cycle_metrics = metrics_map.get(cycle.id)
            if cycle_metrics:
                pairs.append((cycle, cycle_metrics))

        return pairs

    async def get_next_sequence(self, project_id: UUID) -> int:
        """Get the next sequence number for a project.

        Args:
            project_id: Project UUID.

        Returns:
            Next available sequence number.
        """
        query = select(func.coalesce(func.max(Cycle.sequence), 0) + 1).where(
            Cycle.project_id == project_id
        )
        result = await self.session.execute(query)
        return result.scalar() or 1

    async def deactivate_project_cycles(
        self,
        project_id: UUID,
        *,
        exclude_cycle_id: UUID | None = None,
    ) -> int:
        """Deactivate all active cycles for a project.

        Used to ensure only one cycle is active at a time.

        Args:
            project_id: Project UUID.
            exclude_cycle_id: Cycle to exclude from deactivation.

        Returns:
            Number of cycles deactivated.
        """
        query = select(Cycle).where(
            and_(
                Cycle.project_id == project_id,
                Cycle.status == CycleStatus.ACTIVE,
                Cycle.is_deleted == False,  # noqa: E712
            )
        )

        if exclude_cycle_id:
            query = query.where(Cycle.id != exclude_cycle_id)

        result = await self.session.execute(query)
        cycles = result.scalars().all()

        count = 0
        for cycle in cycles:
            cycle.status = CycleStatus.COMPLETED
            count += 1

        await self.session.flush()
        return count

    def _apply_cycle_filters(
        self,
        query: Select[tuple[Cycle]],
        filters: CycleFilters,
    ) -> Select[tuple[Cycle]]:
        """Apply filter criteria to query.

        Args:
            query: Base SQLAlchemy query.
            filters: Filter criteria.

        Returns:
            Query with filters applied.
        """
        conditions: list[Any] = []

        if filters.project_id:
            conditions.append(Cycle.project_id == filters.project_id)

        if filters.status:
            conditions.append(Cycle.status == filters.status)

        if filters.statuses:
            conditions.append(Cycle.status.in_(filters.statuses))

        if filters.start_date_from:
            conditions.append(Cycle.start_date >= filters.start_date_from)

        if filters.start_date_to:
            conditions.append(Cycle.start_date <= filters.start_date_to)

        if filters.end_date_from:
            conditions.append(Cycle.end_date >= filters.end_date_from)

        if filters.end_date_to:
            conditions.append(Cycle.end_date <= filters.end_date_to)

        if filters.owned_by_id:
            conditions.append(Cycle.owned_by_id == filters.owned_by_id)

        if filters.search_term:
            search_pattern = f"%{filters.search_term}%"
            conditions.append(Cycle.name.ilike(search_pattern))

        if conditions:
            query = query.where(and_(*conditions))

        return query


__all__ = ["CycleFilters", "CycleMetrics", "CycleRepository"]
