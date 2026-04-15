"""BatchRunRepository for sprint batch execution data access.

Provides CRUD operations and domain-specific queries for BatchRun and
BatchRunIssue entities, including the dispatchable-issues gate query
used by the BatchImplWorker to determine which issues are ready to execute.

Phase 76 Plan 01 — sprint batch implementation foundation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, not_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from pilot_space.infrastructure.database.models.batch_run import BatchRun, BatchRunStatus
from pilot_space.infrastructure.database.models.batch_run_issue import (
    BatchRunIssue,
    BatchRunIssueStatus,
)
from pilot_space.infrastructure.database.repositories.base import BaseRepository


class BatchRunRepository(BaseRepository[BatchRun]):
    """Repository for BatchRun and BatchRunIssue entities.

    Extends BaseRepository with batch-execution–specific queries:
    - Dispatchable-issues gate: which QUEUED issues have all blockers COMPLETED
    - Bulk cancel of pending/queued issues
    - Progress counter increments on the parent BatchRun
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize BatchRunRepository.

        Args:
            session: The async database session.
        """
        super().__init__(session, BatchRun)

    # ------------------------------------------------------------------
    # BatchRun queries
    # ------------------------------------------------------------------

    async def get_by_id_with_items(self, batch_run_id: UUID) -> BatchRun | None:
        """Get a BatchRun by ID, eagerly loading its BatchRunIssue items.

        Args:
            batch_run_id: The BatchRun UUID.

        Returns:
            The BatchRun with items loaded, or None if not found.
        """
        query = (
            select(BatchRun)
            .where(
                and_(
                    BatchRun.id == batch_run_id,
                    BatchRun.is_deleted == False,  # noqa: E712
                )
            )
            .options(selectinload(BatchRun.items))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_dashboard_data(self, batch_run_id: UUID) -> BatchRun | None:
        """Get a BatchRun with eagerly loaded items AND their related issues.

        Loads items with their issue relationships (for identifier/title) to
        support the dashboard aggregation endpoint without N+1 queries.

        Args:
            batch_run_id: The BatchRun UUID.

        Returns:
            The BatchRun with items and issue relationships loaded, or None.
        """
        query = (
            select(BatchRun)
            .where(
                and_(
                    BatchRun.id == batch_run_id,
                    BatchRun.is_deleted == False,  # noqa: E712
                )
            )
            .options(
                selectinload(BatchRun.items).selectinload(BatchRunIssue.issue)
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # BatchRunIssue queries
    # ------------------------------------------------------------------

    async def get_batch_run_issues(self, batch_run_id: UUID) -> list[BatchRunIssue]:
        """Get all BatchRunIssue rows for a batch run, ordered by execution_order.

        Args:
            batch_run_id: The BatchRun UUID.

        Returns:
            List of BatchRunIssue records ordered by execution_order ASC.
        """
        query = (
            select(BatchRunIssue)
            .where(
                and_(
                    BatchRunIssue.batch_run_id == batch_run_id,
                    BatchRunIssue.is_deleted == False,  # noqa: E712
                )
            )
            .order_by(BatchRunIssue.execution_order.asc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_dispatchable_issues(self, batch_run_id: UUID) -> list[BatchRunIssue]:
        """Return QUEUED issues whose all lower-order blockers are COMPLETED.

        An issue is dispatchable when every issue with a lower execution_order
        in the same batch run has reached COMPLETED status. This implements
        the topological dependency gate: a wave of issues starts only when the
        previous wave is fully done.

        SQL equivalent:
            SELECT * FROM batch_run_issues bri
            WHERE bri.batch_run_id = :batch_run_id
              AND bri.status = 'queued'
              AND NOT EXISTS (
                SELECT 1 FROM batch_run_issues b2
                WHERE b2.batch_run_id = :batch_run_id
                  AND b2.execution_order < bri.execution_order
                  AND b2.status != 'completed'
              )

        Args:
            batch_run_id: The BatchRun UUID.

        Returns:
            List of BatchRunIssue records ready for dispatch.
        """
        # Alias for the blocking subquery
        b2 = BatchRunIssue.__table__.alias("b2")

        blocker_subquery = (
            select(b2.c.id)
            .where(
                and_(
                    b2.c.batch_run_id == batch_run_id,
                    b2.c.execution_order < BatchRunIssue.execution_order,
                    b2.c.status != BatchRunIssueStatus.COMPLETED.value,
                    b2.c.is_deleted == False,  # noqa: E712
                )
            )
        )

        query = (
            select(BatchRunIssue)
            .where(
                and_(
                    BatchRunIssue.batch_run_id == batch_run_id,
                    BatchRunIssue.status == BatchRunIssueStatus.QUEUED,
                    BatchRunIssue.is_deleted == False,  # noqa: E712
                    not_(blocker_subquery.exists()),
                )
            )
            .order_by(BatchRunIssue.execution_order.asc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_issue_status(
        self,
        batch_run_issue_id: UUID,
        status: BatchRunIssueStatus,
        **kwargs: Any,
    ) -> BatchRunIssue | None:
        """Update the status (and optional fields) of a BatchRunIssue.

        Accepted kwargs: pr_url, error_message, current_stage, worktree_path,
        started_at, completed_at.

        Args:
            batch_run_issue_id: The BatchRunIssue UUID.
            status: The new status.
            **kwargs: Additional fields to update.

        Returns:
            The updated BatchRunIssue, or None if not found.
        """
        allowed_fields = {
            "pr_url",
            "error_message",
            "current_stage",
            "worktree_path",
            "started_at",
            "completed_at",
        }
        values: dict[str, Any] = {"status": status}
        for key, value in kwargs.items():
            if key in allowed_fields:
                values[key] = value

        await self.session.execute(
            update(BatchRunIssue)
            .where(BatchRunIssue.id == batch_run_issue_id)
            .values(**values)
        )
        await self.session.flush()

        # Re-fetch to return updated state
        result = await self.session.execute(
            select(BatchRunIssue).where(BatchRunIssue.id == batch_run_issue_id)
        )
        return result.scalar_one_or_none()

    async def cancel_pending_issues(
        self,
        batch_run_id: UUID,
        *,
        min_execution_order: int | None = None,
    ) -> int:
        """Bulk-cancel all QUEUED and PENDING issues in a batch run.

        Used when cancelling a batch run or when a blocking issue fails and
        its dependents must be cascaded to CANCELLED.

        Args:
            batch_run_id: The BatchRun UUID.
            min_execution_order: If provided, only cancel issues with
                execution_order >= this value (for partial cascade).

        Returns:
            Number of rows updated.
        """
        cancellable_statuses = [
            BatchRunIssueStatus.QUEUED.value,
            BatchRunIssueStatus.PENDING.value,
        ]
        conditions = [
            BatchRunIssue.batch_run_id == batch_run_id,
            BatchRunIssue.status.in_(cancellable_statuses),
            BatchRunIssue.is_deleted == False,  # noqa: E712
        ]
        if min_execution_order is not None:
            conditions.append(BatchRunIssue.execution_order >= min_execution_order)

        result = await self.session.execute(
            update(BatchRunIssue)
            .where(and_(*conditions))
            .values(status=BatchRunIssueStatus.CANCELLED)
        )
        await self.session.flush()
        return result.rowcount  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Progress counter helpers
    # ------------------------------------------------------------------

    async def increment_completed(self, batch_run_id: UUID) -> None:
        """Increment the completed_issues counter on the parent BatchRun.

        Args:
            batch_run_id: The BatchRun UUID.
        """
        from sqlalchemy import text

        await self.session.execute(
            text(
                "UPDATE batch_runs SET completed_issues = completed_issues + 1 "
                "WHERE id = :id"
            ),
            {"id": batch_run_id},
        )
        await self.session.flush()

    async def increment_failed(self, batch_run_id: UUID) -> None:
        """Increment the failed_issues counter on the parent BatchRun.

        Args:
            batch_run_id: The BatchRun UUID.
        """
        from sqlalchemy import text

        await self.session.execute(
            text(
                "UPDATE batch_runs SET failed_issues = failed_issues + 1 "
                "WHERE id = :id"
            ),
            {"id": batch_run_id},
        )
        await self.session.flush()

    async def update_batch_run_status(
        self,
        batch_run_id: UUID,
        status: BatchRunStatus,
        *,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> None:
        """Update the status of a BatchRun row.

        Args:
            batch_run_id: The BatchRun UUID.
            status: The new status.
            started_at: Optional start timestamp.
            completed_at: Optional completion timestamp.
        """
        values: dict[str, Any] = {"status": status}
        if started_at is not None:
            values["started_at"] = started_at
        if completed_at is not None:
            values["completed_at"] = completed_at

        await self.session.execute(
            update(BatchRun).where(BatchRun.id == batch_run_id).values(**values)
        )
        await self.session.flush()
