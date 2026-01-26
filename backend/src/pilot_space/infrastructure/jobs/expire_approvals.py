"""Approval expiration background job.

Runs periodically to mark expired pending approvals as expired.
Should be scheduled to run hourly via APScheduler or similar.

T076: Approval expiration cron job.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def expire_pending_approvals(session: AsyncSession) -> int:
    """Mark expired pending approval requests as expired.

    Scans all pending requests and updates those past their expiration time.

    Args:
        session: Database session.

    Returns:
        Number of expired approvals.

    Example:
        >>> from pilot_space.infrastructure.database.engine import get_db_session
        >>> async with get_db_session() as session:
        ...     count = await expire_pending_approvals(session)
        ...     print(f"Expired {count} requests")
    """
    from pilot_space.ai.infrastructure.approval import ApprovalService

    service = ApprovalService(session)
    count = await service.expire_stale_requests()

    if count > 0:
        logger.info(f"Expired {count} approval requests")

    return count


async def run_expiration_job() -> None:
    """Run the approval expiration job.

    Creates a database session and expires stale requests.
    Intended to be called by a scheduler (APScheduler, Celery, etc.).

    Example:
        >>> # Schedule with APScheduler
        >>> from apscheduler.schedulers.asyncio import AsyncIOScheduler
        >>> scheduler = AsyncIOScheduler()
        >>> scheduler.add_job(run_expiration_job, 'interval', hours=1)
        >>> scheduler.start()
    """
    from pilot_space.infrastructure.database.engine import get_db_session

    async with get_db_session() as session:
        count = await expire_pending_approvals(session)
        logger.info(
            "Approval expiration job completed",
            extra={"expired_count": count, "timestamp": datetime.now(UTC).isoformat()},
        )


__all__ = ["expire_pending_approvals", "run_expiration_job"]
