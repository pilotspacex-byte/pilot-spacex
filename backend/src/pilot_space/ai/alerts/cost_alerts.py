"""Cost tracking alerts for high-spend workspaces.

T329: Daily and weekly cost threshold checks with alert messages.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Cost thresholds (configurable per workspace in production)
DAILY_COST_THRESHOLD = Decimal("10.00")
WEEKLY_COST_THRESHOLD = Decimal("50.00")
MONTHLY_COST_THRESHOLD = Decimal("200.00")


async def get_daily_cost(
    db_session: AsyncSession,
    workspace_id: UUID,
) -> Decimal:
    """Get total AI cost for workspace in last 24 hours.

    Args:
        db_session: Database session.
        workspace_id: Workspace to check.

    Returns:
        Total cost in USD.
    """
    from sqlalchemy import func, select

    from pilot_space.infrastructure.database.models.ai_cost_record import (
        AICostRecord,
    )

    since = datetime.now(UTC) - timedelta(days=1)

    query = select(func.coalesce(func.sum(AICostRecord.cost_usd), 0)).where(
        AICostRecord.workspace_id == workspace_id,
        AICostRecord.created_at >= since,
    )

    result = await db_session.execute(query)
    total = result.scalar_one()

    return Decimal(str(total))


async def get_weekly_cost(
    db_session: AsyncSession,
    workspace_id: UUID,
) -> Decimal:
    """Get total AI cost for workspace in last 7 days.

    Args:
        db_session: Database session.
        workspace_id: Workspace to check.

    Returns:
        Total cost in USD.
    """
    from sqlalchemy import func, select

    from pilot_space.infrastructure.database.models.ai_cost_record import (
        AICostRecord,
    )

    since = datetime.now(UTC) - timedelta(days=7)

    query = select(func.coalesce(func.sum(AICostRecord.cost_usd), 0)).where(
        AICostRecord.workspace_id == workspace_id,
        AICostRecord.created_at >= since,
    )

    result = await db_session.execute(query)
    total = result.scalar_one()

    return Decimal(str(total))


async def get_monthly_cost(
    db_session: AsyncSession,
    workspace_id: UUID,
) -> Decimal:
    """Get total AI cost for workspace in last 30 days.

    Args:
        db_session: Database session.
        workspace_id: Workspace to check.

    Returns:
        Total cost in USD.
    """
    from sqlalchemy import func, select

    from pilot_space.infrastructure.database.models.ai_cost_record import (
        AICostRecord,
    )

    since = datetime.now(UTC) - timedelta(days=30)

    query = select(func.coalesce(func.sum(AICostRecord.cost_usd), 0)).where(
        AICostRecord.workspace_id == workspace_id,
        AICostRecord.created_at >= since,
    )

    result = await db_session.execute(query)
    total = result.scalar_one()

    return Decimal(str(total))


async def check_cost_alerts(
    db_session: AsyncSession,
    workspace_id: UUID,
    daily_threshold: Decimal | None = None,
    weekly_threshold: Decimal | None = None,
) -> list[str]:
    """Check for cost alert conditions and return alert messages.

    Args:
        db_session: Database session.
        workspace_id: Workspace to check.
        daily_threshold: Custom daily threshold (defaults to DAILY_COST_THRESHOLD).
        weekly_threshold: Custom weekly threshold (defaults to WEEKLY_COST_THRESHOLD).

    Returns:
        List of alert messages (empty if no alerts).

    Example:
        >>> alerts = await check_cost_alerts(session, workspace_id)
        >>> if alerts:
        ...     for alert in alerts:
        ...         print(f"Alert: {alert}")
    """
    alerts: list[str] = []

    daily_limit = daily_threshold or DAILY_COST_THRESHOLD
    weekly_limit = weekly_threshold or WEEKLY_COST_THRESHOLD

    # Check daily cost
    daily_cost = await get_daily_cost(db_session, workspace_id)
    if daily_cost > daily_limit:
        alerts.append(f"Daily AI cost ${daily_cost:.2f} exceeds threshold ${daily_limit:.2f}")
        logger.warning(
            "Daily cost threshold exceeded",
            extra={
                "workspace_id": str(workspace_id),
                "daily_cost": float(daily_cost),
                "threshold": float(daily_limit),
            },
        )

    # Check weekly cost
    weekly_cost = await get_weekly_cost(db_session, workspace_id)
    if weekly_cost > weekly_limit:
        alerts.append(f"Weekly AI cost ${weekly_cost:.2f} exceeds threshold ${weekly_limit:.2f}")
        logger.warning(
            "Weekly cost threshold exceeded",
            extra={
                "workspace_id": str(workspace_id),
                "weekly_cost": float(weekly_cost),
                "threshold": float(weekly_limit),
            },
        )

    if alerts:
        logger.info(
            "Cost alerts generated",
            extra={
                "workspace_id": str(workspace_id),
                "alert_count": len(alerts),
                "daily_cost": float(daily_cost),
                "weekly_cost": float(weekly_cost),
            },
        )

    return alerts


async def get_cost_summary(
    db_session: AsyncSession,
    workspace_id: UUID,
) -> dict[str, Decimal]:
    """Get comprehensive cost summary for workspace.

    Args:
        db_session: Database session.
        workspace_id: Workspace to check.

    Returns:
        Dictionary with daily, weekly, and monthly costs.
    """
    return {
        "daily": await get_daily_cost(db_session, workspace_id),
        "weekly": await get_weekly_cost(db_session, workspace_id),
        "monthly": await get_monthly_cost(db_session, workspace_id),
    }


__all__ = [
    "DAILY_COST_THRESHOLD",
    "MONTHLY_COST_THRESHOLD",
    "WEEKLY_COST_THRESHOLD",
    "check_cost_alerts",
    "get_cost_summary",
    "get_daily_cost",
    "get_monthly_cost",
    "get_weekly_cost",
]
