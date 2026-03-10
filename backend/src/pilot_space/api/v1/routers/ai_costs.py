"""AI cost tracking endpoints.

Cost tracking and analytics for AI usage.

T091-T094: Cost tracking endpoints.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from pilot_space.api.middleware.request_context import WorkspaceId
from pilot_space.api.v1.schemas.cost import (
    CostByAgent,
    CostByDay,
    CostByUser,
    CostByUserResponse,
    CostSummaryResponse,
    CostTrendsResponse,
    TrendDataPoint,
)
from pilot_space.dependencies import (
    CostTrackerDep,
    CurrentUserId,
    DbSession,
)
from pilot_space.infrastructure.database.models.ai_cost_record import AICostRecord
from pilot_space.infrastructure.database.models.user import User

router = APIRouter(prefix="/costs", tags=["AI Costs"])


@router.get(
    "/summary",
    response_model=CostSummaryResponse,
    summary="Get AI cost summary",
    description="Get aggregated AI cost summary for workspace.",
)
async def get_cost_summary(
    workspace_id: WorkspaceId,
    current_user_id: CurrentUserId,
    cost_tracker: CostTrackerDep,
    session: DbSession,
    start_date: Annotated[date | None, Query(description="Period start date")] = None,
    end_date: Annotated[date | None, Query(description="Period end date")] = None,
    group_by: Annotated[
        str | None,
        Query(
            description="Group breakdown by field. Valid values: operation_type, agent_name, provider, model.",
            pattern=r"^(operation_type|agent_name|provider|model)$",
        ),
    ] = None,
) -> CostSummaryResponse:
    """Get AI cost summary for workspace.

    Default period: last 30 days.
    Requires workspace context via X-Workspace-Id header.

    Args:
        workspace_id: Workspace UUID from request context.
        current_user_id: Current authenticated user ID.
        cost_tracker: Cost tracker dependency.
        session: Database session.
        start_date: Optional period start date.
        end_date: Optional period end date.

    Returns:
        Cost summary with breakdowns by agent, user, and day.
    """

    # Default to last 30 days
    if not end_date:
        end_date = datetime.now(UTC).date()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    # Validate date range
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before or equal to end_date",
        )

    # Get total metrics
    total_query = select(
        func.coalesce(func.sum(AICostRecord.cost_usd), 0).label("total_cost"),
        func.count(AICostRecord.id).label("total_requests"),
        func.coalesce(func.sum(AICostRecord.input_tokens), 0).label("total_input_tokens"),
        func.coalesce(func.sum(AICostRecord.output_tokens), 0).label("total_output_tokens"),
    ).where(
        (AICostRecord.workspace_id == workspace_id)
        & (func.date(AICostRecord.created_at).between(start_date, end_date))
        & (AICostRecord.is_deleted == False)  # noqa: E712
    )
    total_result = await session.execute(total_query)
    total_row = total_result.one()

    # Get detailed breakdowns
    details = await cost_tracker.get_cost_summary_detailed(
        workspace_id=workspace_id,
        start_date=start_date,
        end_date=end_date,
    )

    # Fetch user names for by_user breakdown
    user_ids = [uuid.UUID(u["user_id"]) for u in details["by_user"]]
    users_map = {}
    if user_ids:
        users_query = select(User).where(User.id.in_(user_ids))
        users_result = await session.execute(users_query)
        users_map = {str(u.id): u.full_name or u.email for u in users_result.scalars()}

    # Build group_by=operation_type breakdown (AIGOV-06)
    by_feature: dict[str, float] | None = None
    if group_by == "operation_type":
        op_type_stmt = (
            select(
                AICostRecord.operation_type,
                func.sum(AICostRecord.cost_usd).label("cost"),
            )
            .where(
                (AICostRecord.workspace_id == workspace_id)
                & (func.date(AICostRecord.created_at).between(start_date, end_date))
                & (AICostRecord.is_deleted == False)  # noqa: E712
            )
            .group_by(AICostRecord.operation_type)
        )
        op_result = await session.execute(op_type_stmt)
        by_feature = {
            (row.operation_type if row.operation_type is not None else "unknown"): float(row.cost)
            for row in op_result
        }

    # Build response
    by_agent = [CostByAgent(**item) for item in details["by_agent"]]
    by_user = [
        CostByUser(
            user_id=item["user_id"],
            user_name=users_map.get(item["user_id"], "Unknown User"),
            total_cost_usd=item["total_cost_usd"],
            request_count=item["request_count"],
        )
        for item in details["by_user"]
    ]
    by_day = [CostByDay(**item) for item in details["by_day"]]

    return CostSummaryResponse(
        workspace_id=str(workspace_id),
        period_start=start_date,
        period_end=end_date,
        total_cost_usd=float(total_row.total_cost),
        total_requests=int(total_row.total_requests),
        total_input_tokens=int(total_row.total_input_tokens),
        total_output_tokens=int(total_row.total_output_tokens),
        by_agent=by_agent,
        by_user=by_user,
        by_day=by_day,
        by_feature=by_feature,
    )


@router.get(
    "/by-user",
    response_model=CostByUserResponse,
    summary="Get cost breakdown by user",
    description="Get AI cost breakdown by user for workspace.",
)
async def get_cost_by_user(
    workspace_id: WorkspaceId,
    current_user_id: CurrentUserId,
    cost_tracker: CostTrackerDep,
    session: DbSession,
    start_date: Annotated[date | None, Query(description="Period start date")] = None,
    end_date: Annotated[date | None, Query(description="Period end date")] = None,
) -> CostByUserResponse:
    """Get cost breakdown by user.

    Default period: last 30 days.

    Args:
        workspace_id: Workspace UUID from request context.
        current_user_id: Current authenticated user ID.
        cost_tracker: Cost tracker dependency.
        session: Database session.
        start_date: Optional period start date.
        end_date: Optional period end date.

    Returns:
        User cost breakdown.
    """

    # Default to last 30 days
    if not end_date:
        end_date = datetime.now(UTC).date()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    # Validate date range
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before or equal to end_date",
        )

    user_costs = await cost_tracker.get_cost_by_user_detailed(
        workspace_id=workspace_id,
        start_date=start_date,
        end_date=end_date,
    )

    # Fetch user names
    user_ids = [uuid.UUID(u["user_id"]) for u in user_costs]
    users_map = {}
    if user_ids:
        users_query = select(User).where(User.id.in_(user_ids))
        users_result = await session.execute(users_query)
        users_map = {str(u.id): u.full_name or u.email for u in users_result.scalars()}

    users = [
        CostByUser(
            user_id=item["user_id"],
            user_name=users_map.get(item["user_id"], "Unknown User"),
            total_cost_usd=item["total_cost_usd"],
            request_count=item["request_count"],
        )
        for item in user_costs
    ]

    total_cost = sum(u.total_cost_usd for u in users)

    return CostByUserResponse(
        workspace_id=str(workspace_id),
        period_start=start_date,
        period_end=end_date,
        users=users,
        total_cost_usd=total_cost,
    )


@router.get(
    "/trends",
    response_model=CostTrendsResponse,
    summary="Get cost trends",
    description="Get AI cost trends over time.",
)
async def get_cost_trends(
    workspace_id: WorkspaceId,
    current_user_id: CurrentUserId,
    cost_tracker: CostTrackerDep,
    start_date: Annotated[date | None, Query(description="Period start date")] = None,
    end_date: Annotated[date | None, Query(description="Period end date")] = None,
    granularity: Annotated[str, Query(description="Granularity: daily or weekly")] = "daily",
) -> CostTrendsResponse:
    """Get cost trends over time.

    Default period: last 30 days for daily, last 90 days for weekly.

    Args:
        workspace_id: Workspace UUID from request context.
        current_user_id: Current authenticated user ID.
        cost_tracker: Cost tracker dependency.
        start_date: Optional period start date.
        end_date: Optional period end date.
        granularity: Trend granularity (daily or weekly).

    Returns:
        Cost trends data.
    """

    # Validate granularity
    if granularity not in {"daily", "weekly"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="granularity must be 'daily' or 'weekly'",
        )

    # Default date ranges
    if not end_date:
        end_date = datetime.now(UTC).date()
    if not start_date:
        # Default: 30 days for daily, 90 days for weekly
        days_back = 90 if granularity == "weekly" else 30
        start_date = end_date - timedelta(days=days_back)

    # Validate date range
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before or equal to end_date",
        )

    trends_data = await cost_tracker.get_cost_trends(
        workspace_id=workspace_id,
        start_date=start_date,
        end_date=end_date,
        granularity=granularity,
    )

    trends = [TrendDataPoint(**item) for item in trends_data]

    return CostTrendsResponse(
        workspace_id=str(workspace_id),
        period_start=start_date,
        period_end=end_date,
        granularity=granularity,
        trends=trends,
    )


__all__ = ["router"]
