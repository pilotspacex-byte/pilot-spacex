"""BatchImplWorker -- long-running worker for sprint batch implementation.

Polls the pgmq batch_impl queue for trigger messages (one per BatchRun).
On trigger: polls batch_run_issues for dispatchable issues, launching up to
3 concurrent asyncio Tasks via Semaphore(3). Each Task delegates to
BatchImplHandler for subprocess lifecycle.

VT heartbeat prevents pgmq re-delivery during 30-minute batch jobs.

Architecture:
    1. BatchImplWorker.start() -- poll loop (follows MemoryWorker pattern)
    2. _vt_heartbeat() -- extend visibility timeout every 90s
    3. _process_batch() -- outer driver loop until all issues are terminal
    4. _dispatch_pending() -- check dispatchable issues, launch Tasks
    5. _run_issue_guarded() -- acquire Semaphore, delegate to BatchImplHandler

Phase 76 Plan 02 -- sprint batch implementation engine.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pilot_space.infrastructure.database.models.batch_run import BatchRun, BatchRunStatus
from pilot_space.infrastructure.database.models.batch_run_issue import (
    BatchRunIssue,
    BatchRunIssueStatus,
)
from pilot_space.infrastructure.database.repositories.batch_run_repository import (
    BatchRunRepository,
)
from pilot_space.infrastructure.database.rls import set_rls_context
from pilot_space.infrastructure.logging import get_logger
from pilot_space.infrastructure.queue.models import QueueName

if TYPE_CHECKING:
    from redis.asyncio import Redis
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from pilot_space.infrastructure.queue.supabase_queue import SupabaseQueueClient

__all__ = ["BatchImplWorker"]

logger = get_logger(__name__)

# Polling intervals (seconds)
_POLL_INTERVAL_S = 5.0
_VT_HEARTBEAT_INTERVAL_S = 90.0
_VT_EXTENSION_S = 120
_DISPATCH_INTERVAL_S = 3.0

# pgmq dequeue settings
_BATCH_SIZE = 1
_VISIBILITY_TIMEOUT_S = 120
_SLEEP_ERROR_S = 5.0
_MAX_NACK_ATTEMPTS = 2


class BatchImplWorker:
    """Long-running worker for sprint batch implementation.

    Dequeues batch_impl trigger messages, then drives each BatchRun to
    completion by dispatching dispatchable issues to pilot implement --oneshot
    subprocesses via BatchImplHandler.

    Concurrency: maximum 3 simultaneous subprocesses via asyncio.Semaphore(3).

    Args:
        queue: Supabase queue client for pgmq operations.
        session_factory: Async session factory for per-request DB sessions.
        redis_client: Redis client for pub/sub status broadcasting.
    """

    def __init__(
        self,
        queue: SupabaseQueueClient,
        session_factory: async_sessionmaker[AsyncSession],
        redis_client: Redis,  # type: ignore[type-arg]
    ) -> None:
        self._queue = queue
        self._session_factory = session_factory
        self._redis = redis_client
        self._semaphore = asyncio.Semaphore(3)
        self._running = False
        # Maps batch_run_issue_id -> active asyncio.subprocess.Process
        # Shared with BatchImplHandler instances for cancel support.
        self._active_procs: dict[UUID, asyncio.subprocess.Process] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Main poll loop: dequeue batch_impl messages and process each batch.

        Follows MemoryWorker pattern: poll -> process -> ack/nack.
        Sleeps _POLL_INTERVAL_S on empty queue.
        """
        self._running = True
        logger.info("BatchImplWorker started, polling %s queue", QueueName.BATCH_IMPL)

        while self._running:
            try:
                messages = await self._queue.dequeue(
                    QueueName.BATCH_IMPL,
                    batch_size=_BATCH_SIZE,
                    visibility_timeout=_VISIBILITY_TIMEOUT_S,
                )
                if messages:
                    await self._handle_message(messages[0])
                else:
                    await asyncio.sleep(_POLL_INTERVAL_S)
            except asyncio.CancelledError:
                logger.info("BatchImplWorker cancelled")
                break
            except Exception:
                logger.exception("BatchImplWorker poll error")
                await asyncio.sleep(_SLEEP_ERROR_S)

    async def stop(self) -> None:
        """Signal the worker to stop and terminate all active subprocesses gracefully."""
        self._running = False
        logger.info(
            "BatchImplWorker stopping — terminating %d active procs",
            len(self._active_procs),
        )
        for issue_id, proc in list(self._active_procs.items()):
            try:
                proc.terminate()
                logger.info("BatchImplWorker.stop: terminated proc for issue %s", issue_id)
            except ProcessLookupError:
                pass  # Already dead

    # ------------------------------------------------------------------
    # Cancel API
    # ------------------------------------------------------------------

    async def cancel_issue(self, batch_run_issue_id: UUID) -> bool:
        """Send SIGTERM to the active subprocess for a single issue.

        The BatchImplHandler's finally block handles DB status update to CANCELLED.

        Args:
            batch_run_issue_id: UUID of the BatchRunIssue to cancel.

        Returns:
            True if a process was found and terminated, False otherwise.
        """
        proc = self._active_procs.get(batch_run_issue_id)
        if proc is None:
            logger.warning(
                "BatchImplWorker.cancel_issue: no active proc for %s",
                batch_run_issue_id,
            )
            return False
        try:
            proc.terminate()
            logger.info(
                "BatchImplWorker.cancel_issue: sent SIGTERM to proc for issue %s",
                batch_run_issue_id,
            )
            return True
        except ProcessLookupError:
            self._active_procs.pop(batch_run_issue_id, None)
            return False

    async def cancel_batch(self, batch_run_id: UUID) -> None:
        """Cancel all active subprocesses belonging to a batch run.

        Sends SIGTERM to each active proc. DB updates happen in each
        BatchImplHandler's finally block.

        Args:
            batch_run_id: The BatchRun UUID to cancel.
        """
        logger.info("BatchImplWorker.cancel_batch: cancelling batch %s", batch_run_id)
        # We don't track which batch each proc belongs to in _active_procs,
        # so we terminate all and let handlers update their own issue status.
        # This is acceptable because cancel_batch is a top-level emergency stop.
        for issue_id in list(self._active_procs.keys()):
            await self.cancel_issue(issue_id)

        # Update batch status to FAILED directly
        # (handler finalizers will update individual issue statuses)
        try:
            async with self._session_factory() as session:
                # Use execute without RLS for administrative cancel operation
                from sqlalchemy import update

                await session.execute(
                    update(BatchRun)
                    .where(BatchRun.id == batch_run_id)
                    .values(
                        status=BatchRunStatus.FAILED,
                        completed_at=datetime.now(tz=UTC),
                    )
                )
                await session.commit()
        except Exception:
            logger.exception(
                "BatchImplWorker.cancel_batch: failed to update batch status for %s",
                batch_run_id,
            )

    # ------------------------------------------------------------------
    # Message handling
    # ------------------------------------------------------------------

    async def _handle_message(self, message: Any) -> None:
        """Process a single batch_impl queue message.

        Extracts batch_run_id + workspace/actor context from payload,
        starts VT heartbeat, runs the batch, then acks or nacks.

        Args:
            message: QueueMessage with payload containing batch_run_id.
        """
        payload: dict[str, Any] = message.payload
        msg_id: str = message.id
        batch_run_id_raw = payload.get("batch_run_id")

        if not batch_run_id_raw:
            logger.error(
                "BatchImplWorker: message missing batch_run_id (msg %s) — dead-lettering",
                msg_id,
            )
            await self._queue.move_to_dead_letter(
                QueueName.BATCH_IMPL,
                msg_id,
                error="Missing batch_run_id in payload",
            )
            return

        batch_run_id = UUID(str(batch_run_id_raw))
        workspace_id_raw = payload.get("workspace_id")
        actor_user_id_raw = payload.get("actor_user_id")

        if not workspace_id_raw or not actor_user_id_raw:
            logger.error(
                "BatchImplWorker: message missing workspace_id/actor_user_id (msg %s)",
                msg_id,
            )
            await self._queue.move_to_dead_letter(
                QueueName.BATCH_IMPL,
                msg_id,
                error="Missing workspace_id or actor_user_id in payload",
            )
            return

        workspace_id = UUID(str(workspace_id_raw))
        actor_user_id = UUID(str(actor_user_id_raw))

        logger.info(
            "BatchImplWorker: processing batch %s for workspace %s",
            batch_run_id,
            workspace_id,
        )

        # Start VT heartbeat to prevent re-delivery during long batch
        heartbeat_task = asyncio.create_task(self._vt_heartbeat(msg_id))

        try:
            await self._process_batch(batch_run_id, workspace_id, actor_user_id)
            await self._queue.ack(QueueName.BATCH_IMPL, msg_id)
            logger.info("BatchImplWorker: completed batch %s", batch_run_id)
        except Exception as e:
            logger.exception(
                "BatchImplWorker: batch %s failed",
                batch_run_id,
            )
            attempts = getattr(message, "attempts", 0)
            if attempts < _MAX_NACK_ATTEMPTS:
                await self._queue.nack(QueueName.BATCH_IMPL, msg_id, error=str(e))
            else:
                await self._queue.move_to_dead_letter(
                    QueueName.BATCH_IMPL,
                    msg_id,
                    error=str(e),
                    original_payload=payload,
                )
        finally:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

    # ------------------------------------------------------------------
    # VT heartbeat
    # ------------------------------------------------------------------

    async def _vt_heartbeat(self, msg_id: str) -> None:
        """Extend pgmq visibility timeout every 90s to prevent re-delivery.

        Pattern from RESEARCH.md Pattern 3: VT heartbeat for long-running jobs.
        Runs until cancelled by the parent _handle_message task.

        Args:
            msg_id: pgmq message ID to keep visible.
        """
        while True:
            await asyncio.sleep(_VT_HEARTBEAT_INTERVAL_S)
            try:
                await self._queue.nack(
                    QueueName.BATCH_IMPL,
                    msg_id,
                    requeue=True,
                    delay_seconds=_VT_EXTENSION_S,
                )
                logger.debug(
                    "BatchImplWorker._vt_heartbeat: extended VT for msg %s by %ds",
                    msg_id,
                    _VT_EXTENSION_S,
                )
            except Exception:
                logger.warning(
                    "BatchImplWorker._vt_heartbeat: failed to extend VT for msg %s",
                    msg_id,
                )
                # Non-fatal — continue heartbeat loop

    # ------------------------------------------------------------------
    # Batch processing
    # ------------------------------------------------------------------

    async def _process_batch(
        self,
        batch_run_id: UUID,
        workspace_id: UUID,
        actor_user_id: UUID,
    ) -> None:
        """Drive a BatchRun to completion.

        Updates BatchRun to RUNNING, then runs the dispatch loop until all
        issues reach a terminal state (completed/failed/cancelled).

        Args:
            batch_run_id: The BatchRun UUID to execute.
            workspace_id: Workspace UUID for RLS context.
            actor_user_id: Actor UUID for RLS context.
        """
        # Mark batch as RUNNING
        async with self._session_factory() as session:
            await set_rls_context(session, user_id=actor_user_id, workspace_id=workspace_id)
            repo = BatchRunRepository(session)
            await repo.update_batch_run_status(
                batch_run_id,
                BatchRunStatus.RUNNING,
                started_at=datetime.now(tz=UTC),
            )
            await session.commit()

        logger.info("BatchImplWorker._process_batch: batch %s RUNNING", batch_run_id)

        # Dispatch loop: keep running until all issues are terminal
        while self._running:
            await self._dispatch_pending(batch_run_id, workspace_id, actor_user_id)

            # Check if batch is done
            all_terminal = await self._check_all_terminal(
                batch_run_id, workspace_id, actor_user_id
            )
            if all_terminal:
                logger.info(
                    "BatchImplWorker._process_batch: batch %s all issues terminal, done",
                    batch_run_id,
                )
                break

            await asyncio.sleep(_DISPATCH_INTERVAL_S)

    async def _check_all_terminal(
        self,
        batch_run_id: UUID,
        workspace_id: UUID,
        actor_user_id: UUID,
    ) -> bool:
        """Return True if all issues in the batch have reached a terminal state.

        Args:
            batch_run_id: The BatchRun UUID.
            workspace_id: Workspace UUID for RLS context.
            actor_user_id: Actor UUID for RLS context.

        Returns:
            True if there are no PENDING, QUEUED, or RUNNING issues.
        """
        try:
            async with self._session_factory() as session:
                await set_rls_context(session, user_id=actor_user_id, workspace_id=workspace_id)
                repo = BatchRunRepository(session)
                all_issues = await repo.get_batch_run_issues(batch_run_id)

            if not all_issues:
                return True

            non_terminal = [
                i for i in all_issues
                if i.status in (
                    BatchRunIssueStatus.PENDING,
                    BatchRunIssueStatus.QUEUED,
                    BatchRunIssueStatus.RUNNING,
                )
            ]
            return len(non_terminal) == 0
        except Exception:
            logger.exception(
                "BatchImplWorker._check_all_terminal: error checking batch %s",
                batch_run_id,
            )
            return False

    async def _dispatch_pending(
        self,
        batch_run_id: UUID,
        workspace_id: UUID,
        actor_user_id: UUID,
    ) -> None:
        """Query for dispatchable issues and launch Tasks for each one.

        Issues already in _active_procs are skipped to avoid double-dispatch.

        Args:
            batch_run_id: The BatchRun UUID.
            workspace_id: Workspace UUID for RLS context.
            actor_user_id: Actor UUID for RLS context.
        """
        try:
            async with self._session_factory() as session:
                await set_rls_context(session, user_id=actor_user_id, workspace_id=workspace_id)
                repo = BatchRunRepository(session)
                dispatchable = await repo.get_dispatchable_issues(batch_run_id)
        except Exception:
            logger.exception(
                "BatchImplWorker._dispatch_pending: error querying dispatchable issues for %s",
                batch_run_id,
            )
            return

        for issue in dispatchable:
            if issue.id in self._active_procs:
                continue  # Already running

            logger.info(
                "BatchImplWorker._dispatch_pending: launching issue %s (identifier=%s)",
                issue.id,
                self._get_issue_identifier(issue),
            )
            asyncio.create_task(
                self._run_issue_guarded(issue, batch_run_id, workspace_id, actor_user_id),
                name=f"batch_impl_{issue.id}",
            )

    async def _run_issue_guarded(
        self,
        issue: BatchRunIssue,
        batch_run_id: UUID,
        workspace_id: UUID,
        actor_user_id: UUID,
    ) -> None:
        """Acquire semaphore slot and run BatchImplHandler for one issue.

        The Semaphore(3) ensures at most 3 concurrent subprocess executions.

        Args:
            issue: The BatchRunIssue to implement.
            batch_run_id: Parent BatchRun UUID.
            workspace_id: Workspace UUID for RLS context.
            actor_user_id: Actor UUID for RLS context.
        """
        from pilot_space.infrastructure.queue.handlers.batch_impl_handler import (
            BatchImplHandler,
        )

        issue_identifier = self._get_issue_identifier(issue)

        async with self._semaphore:
            try:
                handler = BatchImplHandler(
                    session_factory=self._session_factory,
                    redis_client=self._redis,
                    active_procs=self._active_procs,
                )
                await handler.execute(
                    batch_run_issue_id=issue.id,
                    batch_run_id=batch_run_id,
                    issue_identifier=issue_identifier,
                    workspace_id=workspace_id,
                    actor_user_id=actor_user_id,
                )
            except Exception:
                logger.exception(
                    "BatchImplWorker._run_issue_guarded: unhandled error for issue %s",
                    issue.id,
                )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_issue_identifier(self, issue: BatchRunIssue) -> str:
        """Extract the human-readable issue identifier (e.g. 'PS-42').

        Uses the lazy-loaded issue.issue relationship if available, otherwise
        falls back to the raw issue_id string.

        Args:
            issue: The BatchRunIssue record with an optional loaded Issue.

        Returns:
            Issue identifier string for use with pilot implement.
        """
        try:
            # issue.issue is selectin-loaded -- access the identifier property
            return issue.issue.identifier  # type: ignore[return-value]
        except Exception:
            # Fallback: use issue_id raw (not ideal but non-fatal)
            logger.warning(
                "BatchImplWorker: could not resolve identifier for issue %s, using raw id",
                issue.id,
            )
            return str(issue.issue_id)
