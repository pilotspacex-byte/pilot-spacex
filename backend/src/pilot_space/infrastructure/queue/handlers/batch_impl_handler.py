"""BatchImplHandler -- subprocess lifecycle for a single batch issue.

Manages the full execution lifecycle of one issue in a sprint batch run:
1. Update DB status to RUNNING
2. Launch `pilot implement <identifier> --oneshot` as asyncio subprocess
3. Stream stdout, extract PR URL via regex
4. On success: COMPLETED + write pr_url
5. On failure: FAILED + cascade-cancel dependent issues
6. SIGTERM cancel support via active_procs dict

Phase 76 Plan 02 -- sprint batch implementation engine.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pilot_space.infrastructure.database.models.batch_run import BatchRunStatus
from pilot_space.infrastructure.database.models.batch_run_issue import BatchRunIssueStatus
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

__all__ = ["BatchImplHandler"]

logger = get_logger(__name__)

# 30-minute hard timeout per issue
TIMEOUT_S = 1800

# PR URL regex -- matches GitHub pull request URLs
PR_URL_PATTERN = re.compile(r"https://github\.com/[^\s]+/pull/\d+")

# Grace period after SIGTERM before SIGKILL
_SIGTERM_GRACE_S = 5

# Lines before advancing to 'implementing' stage
_IMPLEMENTING_LINE_THRESHOLD = 5


class BatchImplHandler:
    """Manages subprocess lifecycle for a single BatchRunIssue.

    Launched per-issue by BatchImplWorker. Delegates all DB and Redis I/O
    through the provided session_factory and redis_client.

    Args:
        session_factory: Async session factory for per-operation sessions.
        redis_client: Redis client for pub/sub status broadcasting.
        active_procs: Shared dict mapping batch_run_issue_id -> subprocess.
            Handler registers/deregisters itself so BatchImplWorker can send
            SIGTERM for cancel requests.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        redis_client: Redis,  # type: ignore[type-arg]
        active_procs: dict[UUID, asyncio.subprocess.Process],
        queue_client: SupabaseQueueClient | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._redis = redis_client
        self._active_procs = active_procs
        self._queue = queue_client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def execute(
        self,
        batch_run_issue_id: UUID,
        batch_run_id: UUID,
        issue_identifier: str,
        workspace_id: UUID,
        actor_user_id: UUID,
    ) -> None:
        """Run `pilot implement <identifier> --oneshot` for one issue.

        Updates DB status throughout and publishes Redis events. On failure
        cascades cancellation to dependent (higher-order) issues.

        Args:
            batch_run_issue_id: The BatchRunIssue UUID being executed.
            batch_run_id: Parent BatchRun UUID (for Redis channel + cascade).
            issue_identifier: Human-readable identifier e.g. "PS-42".
            workspace_id: Workspace UUID (for RLS context).
            actor_user_id: User UUID who triggered the batch (for RLS context).
        """
        proc: asyncio.subprocess.Process | None = None
        pr_url: str | None = None
        error_message: str | None = None
        succeeded = False

        try:
            # Mark RUNNING
            await self._update_status(
                batch_run_issue_id,
                workspace_id,
                actor_user_id,
                BatchRunIssueStatus.RUNNING,
                current_stage="cloning",
                started_at=datetime.now(tz=UTC),
            )
            await self._publish(batch_run_id, batch_run_issue_id, "running", "cloning")

            # Launch subprocess -- using create_subprocess_exec (not shell=True) for safety
            env = {**os.environ, "PILOT_BATCH_RUN_ID": str(batch_run_id)}
            proc = await asyncio.create_subprocess_exec(
                "pilot",
                "implement",
                issue_identifier,
                "--oneshot",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=env,
            )
            self._active_procs[batch_run_issue_id] = proc

            # Read stdout with timeout
            try:
                pr_url, error_message = await asyncio.wait_for(
                    self._stream_output(
                        proc,
                        batch_run_id,
                        batch_run_issue_id,
                        workspace_id,
                        actor_user_id,
                    ),
                    timeout=TIMEOUT_S,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "batch_impl_handler.timeout",
                    extra={
                        "batch_run_issue_id": str(batch_run_issue_id),
                        "issue_identifier": issue_identifier,
                        "timeout_s": TIMEOUT_S,
                    },
                )
                # Terminate gracefully, then SIGKILL after grace period
                try:
                    proc.terminate()
                    await asyncio.wait_for(proc.wait(), timeout=_SIGTERM_GRACE_S)
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()
                error_message = "Timeout after 30 minutes"

            # Determine outcome
            returncode = proc.returncode if proc.returncode is not None else -1
            if returncode == 0 and pr_url:
                succeeded = True
            else:
                if not error_message:
                    error_message = f"Exit code {returncode}"

        except Exception:
            logger.exception(
                "batch_impl_handler.unexpected_error",
                extra={
                    "batch_run_issue_id": str(batch_run_issue_id),
                    "issue_identifier": issue_identifier,
                },
            )
            if not error_message:
                error_message = "Unexpected handler error"
        finally:
            self._active_procs.pop(batch_run_issue_id, None)

        # Write final status
        if succeeded:
            await self._finalize_success(
                batch_run_issue_id,
                batch_run_id,
                workspace_id,
                actor_user_id,
                pr_url=pr_url,
            )
        else:
            await self._finalize_failure(
                batch_run_issue_id,
                batch_run_id,
                workspace_id,
                actor_user_id,
                error_message=error_message or "Unknown error",
            )

    # ------------------------------------------------------------------
    # Stdout streaming
    # ------------------------------------------------------------------

    async def _stream_output(
        self,
        proc: asyncio.subprocess.Process,
        batch_run_id: UUID,
        batch_run_issue_id: UUID,
        workspace_id: UUID,
        actor_user_id: UUID,
    ) -> tuple[str | None, str | None]:
        """Stream stdout line-by-line, extracting PR URL.

        Returns:
            (pr_url, error_message) -- pr_url is None if not found,
            error_message is None on clean exit.
        """
        pr_url: str | None = None
        line_count = 0
        stage = "cloning"

        if proc.stdout is None:
            await proc.wait()
            return None, None

        async for raw_line in proc.stdout:
            line = raw_line.decode("utf-8", errors="replace").rstrip()
            line_count += 1

            # Advance to 'implementing' stage after threshold lines
            if line_count == _IMPLEMENTING_LINE_THRESHOLD and stage == "cloning":
                stage = "implementing"
                await self._update_status(
                    batch_run_issue_id,
                    workspace_id,
                    actor_user_id,
                    BatchRunIssueStatus.RUNNING,
                    current_stage=stage,
                )
                await self._publish(batch_run_id, batch_run_issue_id, "running", stage)

            # Extract PR URL
            match = PR_URL_PATTERN.search(line)
            if match and pr_url is None:
                pr_url = match.group(0)
                stage = "creating_pr"
                await self._update_status(
                    batch_run_issue_id,
                    workspace_id,
                    actor_user_id,
                    BatchRunIssueStatus.RUNNING,
                    current_stage=stage,
                )
                await self._publish(
                    batch_run_id,
                    batch_run_issue_id,
                    "running",
                    stage,
                    pr_url=pr_url,
                )

        await proc.wait()
        return pr_url, None

    # ------------------------------------------------------------------
    # Finalization helpers
    # ------------------------------------------------------------------

    async def _finalize_success(
        self,
        batch_run_issue_id: UUID,
        batch_run_id: UUID,
        workspace_id: UUID,
        actor_user_id: UUID,
        *,
        pr_url: str | None,
    ) -> None:
        """Mark issue COMPLETED, increment counter, publish 'done'."""
        logger.info(
            "batch_impl_handler.completed",
            extra={
                "batch_run_issue_id": str(batch_run_issue_id),
                "pr_url": pr_url,
            },
        )
        await self._update_status(
            batch_run_issue_id,
            workspace_id,
            actor_user_id,
            BatchRunIssueStatus.COMPLETED,
            current_stage="done",
            pr_url=pr_url,
            completed_at=datetime.now(tz=UTC),
        )
        await self._publish(batch_run_id, batch_run_issue_id, "done", "done", pr_url=pr_url)

        async with self._session_factory() as session:
            await set_rls_context(session, user_id=actor_user_id, workspace_id=workspace_id)
            repo = BatchRunRepository(session)
            await repo.increment_completed(batch_run_id)

            # Check if all issues are terminal -> set batch COMPLETED
            all_issues = await repo.get_batch_run_issues(batch_run_id)
            if all_issues and all(issue.is_terminal for issue in all_issues):
                has_failures = any(
                    issue.status == BatchRunIssueStatus.FAILED for issue in all_issues
                )
                final_status = BatchRunStatus.FAILED if has_failures else BatchRunStatus.COMPLETED
                await repo.update_batch_run_status(
                    batch_run_id,
                    final_status,
                    completed_at=datetime.now(tz=UTC),
                )

            # Enqueue deviation_analysis if the issue has a source_note_id.
            # Non-fatal: queue failure must not affect the batch run outcome.
            if pr_url and self._queue is not None:
                try:
                    from sqlalchemy import select

                    from pilot_space.infrastructure.database.models.batch_run_issue import (
                        BatchRunIssue,
                    )
                    from pilot_space.infrastructure.database.models.issue import Issue

                    bri_stmt = (
                        select(Issue.id, Issue.source_note_id)
                        .join(BatchRunIssue, BatchRunIssue.issue_id == Issue.id)
                        .where(BatchRunIssue.id == batch_run_issue_id)
                    )
                    bri_result = await session.execute(bri_stmt)
                    bri_row = bri_result.one_or_none()
                    if bri_row is not None and bri_row[1] is not None:
                        issue_id, source_note_id = bri_row
                        await self._queue.enqueue(
                            QueueName.AI_NORMAL,
                            {
                                "task_type": "deviation_analysis",
                                "issue_id": str(issue_id),
                                "pr_url": pr_url,
                                "workspace_id": str(workspace_id),
                                "actor_user_id": str(actor_user_id),
                                "source_note_id": str(source_note_id),
                            },
                        )
                        logger.info(
                            "batch_impl_handler.deviation_analysis_enqueued",
                            extra={
                                "issue_id": str(issue_id),
                                "source_note_id": str(source_note_id),
                                "pr_url": pr_url,
                            },
                        )
                except Exception:
                    logger.warning(
                        "batch_impl_handler.deviation_analysis_enqueue_failed",
                        extra={
                            "batch_run_issue_id": str(batch_run_issue_id),
                            "pr_url": pr_url,
                        },
                        exc_info=True,
                    )

            await session.commit()

    async def _finalize_failure(
        self,
        batch_run_issue_id: UUID,
        batch_run_id: UUID,
        workspace_id: UUID,
        actor_user_id: UUID,
        *,
        error_message: str,
    ) -> None:
        """Mark issue FAILED, cascade-cancel dependents, increment counter, publish 'failed'."""
        logger.warning(
            "batch_impl_handler.failed",
            extra={
                "batch_run_issue_id": str(batch_run_issue_id),
                "error": error_message,
            },
        )
        await self._update_status(
            batch_run_issue_id,
            workspace_id,
            actor_user_id,
            BatchRunIssueStatus.FAILED,
            error_message=error_message,
            completed_at=datetime.now(tz=UTC),
        )
        await self._publish(
            batch_run_id,
            batch_run_issue_id,
            "failed",
            "failed",
            error=error_message,
        )

        async with self._session_factory() as session:
            await set_rls_context(session, user_id=actor_user_id, workspace_id=workspace_id)
            repo = BatchRunRepository(session)
            await repo.increment_failed(batch_run_id)

            # Load the failed issue to get its execution_order for cascade
            from pilot_space.infrastructure.database.models.batch_run_issue import (
                BatchRunIssue,
            )

            result = await session.get(BatchRunIssue, batch_run_issue_id)
            if result is not None:
                cancelled = await repo.cancel_pending_issues(
                    batch_run_id,
                    min_execution_order=result.execution_order + 1,
                )
                logger.info(
                    "batch_impl_handler.cascade_cancelled",
                    extra={
                        "batch_run_id": str(batch_run_id),
                        "cancelled_count": cancelled,
                    },
                )

            # Check if all issues are now terminal
            all_issues = await repo.get_batch_run_issues(batch_run_id)
            if all_issues and all(issue.is_terminal for issue in all_issues):
                await repo.update_batch_run_status(
                    batch_run_id,
                    BatchRunStatus.FAILED,
                    completed_at=datetime.now(tz=UTC),
                )
            await session.commit()

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    async def _update_status(
        self,
        batch_run_issue_id: UUID,
        workspace_id: UUID,
        actor_user_id: UUID,
        status: BatchRunIssueStatus,
        **kwargs: object,
    ) -> None:
        """Open a session and update BatchRunIssue status."""
        async with self._session_factory() as session:
            await set_rls_context(session, user_id=actor_user_id, workspace_id=workspace_id)
            repo = BatchRunRepository(session)
            await repo.update_issue_status(batch_run_issue_id, status, **kwargs)
            await session.commit()

    # ------------------------------------------------------------------
    # Redis pub/sub
    # ------------------------------------------------------------------

    async def _publish(
        self,
        batch_run_id: UUID,
        batch_run_issue_id: UUID,
        status: str,
        stage: str,
        *,
        pr_url: str | None = None,
        error: str | None = None,
    ) -> None:
        """Publish a status event to the Redis channel for this batch run."""
        channel = f"batch_runs:{batch_run_id}"
        payload = json.dumps(
            {
                "batch_run_issue_id": str(batch_run_issue_id),
                "status": status,
                "stage": stage,
                "pr_url": pr_url,
                "error": error,
                "timestamp": datetime.now(tz=UTC).isoformat(),
            }
        )
        try:
            await self._redis.publish(channel, payload)
        except Exception:
            logger.warning(
                "batch_impl_handler.redis_publish_failed",
                extra={"channel": channel, "batch_run_issue_id": str(batch_run_issue_id)},
            )
