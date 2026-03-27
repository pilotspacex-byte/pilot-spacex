"""CapacityPlanService — capacity plan data for cycles.

Extracted from pm_capacity router (T-242).
Handles utilization calculation and team aggregation.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING
from uuid import UUID

from pilot_space.domain.exceptions import NotFoundError
from pilot_space.infrastructure.logging import get_logger
from pilot_space.schemas.capacity_plan import CapacityPlanResponse, MemberCapacity

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.repositories.pm_block_queries_repository import (
        PMBlockQueriesRepository,
    )

logger = get_logger(__name__)


class CapacityPlanService:
    """Capacity plan business logic.

    Computes member-level and team-level utilization for a cycle.
    """

    def __init__(
        self,
        session: AsyncSession,
        pm_block_queries_repository: PMBlockQueriesRepository,
    ) -> None:
        self._session = session
        self._repo = pm_block_queries_repository

    async def get_capacity(
        self,
        workspace_id: UUID,
        cycle_id: str,
    ) -> CapacityPlanResponse:
        """Calculate capacity plan for a cycle.

        Args:
            workspace_id: Workspace UUID.
            cycle_id: Cycle UUID string.

        Returns:
            Dict with cycle info, member capacities, team totals.

        Raises:
            NotFoundError: If cycle not found.
        """
        cycle_uuid = UUID(cycle_id)
        repo = self._repo

        cycle = await repo.get_cycle(cycle_uuid, workspace_id)
        if not cycle:
            raise NotFoundError("Cycle not found")

        members = await repo.get_workspace_members_with_user(workspace_id)
        issues = await repo.get_cycle_assigned_issues(cycle_uuid, workspace_id)

        committed: dict[str, float] = defaultdict(float)
        for issue in issues:
            est = getattr(issue, "estimate_points", None)
            if issue.assignee_id and est:
                committed[str(issue.assignee_id)] += float(est)

        capacity_members: list[MemberCapacity] = []
        has_data = False

        for m in members:
            weekly_hours = getattr(m, "weekly_available_hours", None)
            available = float(weekly_hours or 40)
            commit = committed.get(str(m.user_id), 0.0)
            utilization = (commit / available * 100) if available > 0 else 0.0

            if weekly_hours is not None:
                has_data = True

            user = m.user
            display_name = getattr(user, "display_name", None) or getattr(
                user, "email", str(m.user_id)
            )

            capacity_members.append(
                MemberCapacity(
                    user_id=m.user_id,
                    display_name=display_name,
                    avatar_url=getattr(user, "avatar_url", None),
                    available_hours=available,
                    committed_hours=round(commit, 1),
                    utilization_pct=round(utilization, 1),
                    is_over_allocated=utilization > 100,
                )
            )

        team_available = sum(m.available_hours for m in capacity_members)
        team_committed = sum(m.committed_hours for m in capacity_members)
        team_util = (team_committed / team_available * 100) if team_available > 0 else 0.0

        return CapacityPlanResponse(
            cycle_id=cycle_id,
            cycle_name=cycle.name,
            members=capacity_members,
            team_available=round(team_available, 1),
            team_committed=round(team_committed, 1),
            team_utilization_pct=round(team_util, 1),
            has_data=has_data,
        )


__all__ = ["CapacityPlanService"]
