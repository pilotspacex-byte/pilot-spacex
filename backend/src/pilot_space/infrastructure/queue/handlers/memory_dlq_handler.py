"""MemoryDLQJobHandler — retry failed memory embedding jobs.

T-035: Retry DLQ entries (max 6 total attempts, exponential backoff).
Detect orphaned skill executions (execution exists, no memory entry, >1h old) → log warning.
pg_cron triggers hourly by enqueuing to ai_normal.

Feature 015: AI Workforce Platform — Memory Engine
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import select, text

from pilot_space.infrastructure.database.models.memory_entry import MemoryDLQ
from pilot_space.infrastructure.logging import get_logger
from pilot_space.infrastructure.queue.models import QueueName

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.queue.supabase_queue import SupabaseQueueClient

logger = get_logger(__name__)

_MAX_TOTAL_ATTEMPTS = 6
_BASE_BACKOFF_SECONDS = 30.0
_ORPHAN_AGE_HOURS = 1


def _next_retry_at(attempts: int) -> datetime:
    """Compute next retry timestamp using exponential backoff.

    Args:
        attempts: Current attempt count (before this retry).

    Returns:
        UTC datetime for next retry attempt.
    """
    delay = min(_BASE_BACKOFF_SECONDS * (2**attempts), 3600.0)
    return datetime.now(tz=UTC) + timedelta(seconds=delay)


class MemoryDLQJobHandler:
    """Handles memory DLQ reconciliation jobs.

    Retries failed memory embedding jobs up to 6 total attempts.
    Logs warnings for orphaned skill executions (>1h old with no memory entry).

    Args:
        session: Async DB session.
        queue: Queue client for re-enqueuing embedding jobs.
    """

    def __init__(
        self,
        session: AsyncSession,
        queue: SupabaseQueueClient,
    ) -> None:
        self._session = session
        self._queue = queue

    async def handle(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Process a DLQ reconciliation job.

        Args:
            payload: Queue message payload (workspace_id optional for scoping).

        Returns:
            Result dict with retry/discard/orphan counts.
        """
        workspace_id_str = payload.get("workspace_id")
        workspace_id = UUID(workspace_id_str) if workspace_id_str else None

        retried, discarded, orphans = await self._reconcile(workspace_id)

        logger.info(
            "MemoryDLQJobHandler: retried=%d discarded=%d orphans=%d (workspace=%s)",
            retried,
            discarded,
            orphans,
            workspace_id,
        )
        return {"retried": retried, "discarded": discarded, "orphans": orphans}

    async def _reconcile(
        self,
        workspace_id: UUID | None,
    ) -> tuple[int, int, int]:
        """Reconcile DLQ entries and detect orphans.

        Args:
            workspace_id: Optional workspace filter.

        Returns:
            Tuple of (retried, discarded, orphan_warnings) counts.
        """
        retried = 0
        discarded = 0

        # Load DLQ entries
        query = select(MemoryDLQ).where(
            MemoryDLQ.next_retry_at <= datetime.now(tz=UTC),
        )
        if workspace_id is not None:
            query = query.where(MemoryDLQ.workspace_id == workspace_id)

        result = await self._session.execute(query)
        dlq_entries = result.scalars().all()

        for entry in dlq_entries:
            if entry.attempts >= _MAX_TOTAL_ATTEMPTS:  # type: ignore[operator]
                # Permanently discard after max attempts
                await self._session.delete(entry)
                discarded += 1
                logger.warning(
                    "MemoryDLQJobHandler: discarding entry %s after %d attempts",
                    entry.id,
                    entry.attempts,
                )
                await self._session.commit()
                continue

            # Re-enqueue embedding job
            try:
                job_payload: dict[str, Any] = dict(entry.payload)  # type: ignore[arg-type]
                await self._queue.enqueue(QueueName.AI_NORMAL, job_payload)

                # Update attempts and next_retry_at
                entry.attempts = (entry.attempts or 0) + 1  # type: ignore[operator]
                entry.next_retry_at = _next_retry_at(entry.attempts)  # type: ignore[assignment]
                retried += 1
                await self._session.commit()
            except Exception:
                logger.error(
                    "MemoryDLQJobHandler: failed to re-enqueue entry %s",
                    entry.id,
                    exc_info=True,
                )
                await self._session.rollback()

        # Detect orphaned skill executions
        orphans = await self._detect_orphans(workspace_id)

        return retried, discarded, orphans

    async def _detect_orphans(self, workspace_id: UUID | None) -> int:
        """Find skill executions older than 1h with no linked memory entry.

        Args:
            workspace_id: Optional workspace filter.

        Returns:
            Count of orphaned executions logged as warnings.
        """
        cutoff = datetime.now(tz=UTC) - timedelta(hours=_ORPHAN_AGE_HOURS)
        params: dict[str, Any] = {"cutoff": cutoff}

        workspace_clause = ""
        if workspace_id is not None:
            workspace_clause = " AND wi.workspace_id = :workspace_id"
            params["workspace_id"] = str(workspace_id)

        orphan_sql = text(f"""
            SELECT se.id, wi.workspace_id
            FROM skill_executions se
            JOIN work_intents wi ON wi.id = se.intent_id
            WHERE se.created_at < :cutoff
              AND se.is_deleted = false
              AND NOT EXISTS (
                  SELECT 1 FROM memory_entries me
                  WHERE me.source_id = se.id
                    AND me.is_deleted = false
              )
            {workspace_clause}
            LIMIT 100
        """)

        result = await self._session.execute(orphan_sql, params)
        orphaned_rows = result.fetchall()

        for row in orphaned_rows:
            logger.warning(
                "MemoryDLQJobHandler: orphaned skill_execution %s in workspace %s (>%dh old, no memory entry)",
                row[0],
                row[1],
                _ORPHAN_AGE_HOURS,
            )

        return len(orphaned_rows)
