"""MCP tools for sprint batch implementation via PilotSpaceAgent chat.

Provides two tools for the PM approval workflow (DD-003):
- preview_sprint_implementation: Shows DAG preview before PM approves
- implement_sprint: Triggers batch run after PM approval

Phase 76 Plan 05 — MCP tool wiring for chat-triggered sprint execution.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pilot_space.ai.tools.mcp_server import ToolContext, register_tool
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)


@register_tool("issue")
async def preview_sprint_implementation(
    cycle_id: str,
    ctx: ToolContext,
) -> dict[str, Any]:
    """Preview the execution plan for implementing all issues in a sprint cycle.

    Shows dependency DAG, execution order, and parallel tracks. Call this
    before implement_sprint to let the PM review the plan (DD-003).

    Args:
        cycle_id: UUID of the sprint cycle to preview.
        ctx: Tool context with db_session, workspace_id, and user_id.

    Returns:
        Dict with issues list (identifier, title, execution_order),
        parallel_tracks count, cycle_issues warnings, and total count.
    """
    try:
        cycle_uuid = UUID(cycle_id)
    except ValueError:
        logger.warning("preview_sprint_implementation: invalid cycle_id %s", cycle_id)
        return {"error": f"Invalid cycle_id: {cycle_id}", "found": False}

    try:
        workspace_uuid = UUID(ctx.workspace_id)
    except (ValueError, TypeError):
        logger.warning(
            "preview_sprint_implementation: invalid workspace_id %s", ctx.workspace_id
        )
        return {"error": "Invalid workspace_id in tool context", "found": False}

    try:
        from pilot_space.application.services.batch_run_service import BatchRunService

        service = BatchRunService(session=ctx.db_session)
        preview = await service.get_dag_preview(
            cycle_id=cycle_uuid,
            workspace_id=workspace_uuid,
        )

        logger.info(
            "preview_sprint_implementation: cycle=%s issues=%d tracks=%d cycles=%d",
            cycle_id,
            len(preview.issues),
            preview.parallel_tracks,
            len(preview.cycle_issues),
        )

        return {
            "found": True,
            "cycle_id": cycle_id,
            "total_issues": len(preview.issues),
            "parallel_tracks": preview.parallel_tracks,
            "has_cycle_warnings": len(preview.cycle_issues) > 0,
            "cycle_issues": preview.cycle_issues,
            "issues": [
                {
                    "id": issue["id"],
                    "title": issue["title"],
                    "execution_order": preview.execution_order.get(issue["id"], 0),
                }
                for issue in preview.issues
            ],
            "message": (
                f"Found {len(preview.issues)} issues across {preview.parallel_tracks} "
                "parallel execution track(s). "
                + (
                    f"WARNING: {len(preview.cycle_issues)} issue(s) have circular dependencies "
                    "and will be skipped. "
                    if preview.cycle_issues
                    else ""
                )
                + "Call implement_sprint with this cycle_id to start autonomous implementation "
                "after PM approval."
            ),
        }
    except Exception as exc:
        logger.error(
            "preview_sprint_implementation: error for cycle %s: %s",
            cycle_id,
            exc,
            exc_info=True,
        )
        return {
            "error": f"Failed to preview sprint: {exc}",
            "found": False,
        }


@register_tool("issue")
async def implement_sprint(
    cycle_id: str,
    ctx: ToolContext,
) -> dict[str, Any]:
    """Start autonomous implementation of all issues in a sprint cycle.

    Issues execute in dependency order with max 3 concurrent subprocesses.
    Each issue gets a PR. Requires PM approval (DD-003) — PilotSpaceAgent
    MUST invoke this only AFTER PM has reviewed the preview_sprint_implementation
    output and explicitly approved.

    Args:
        cycle_id: UUID of the sprint cycle to implement.
        ctx: Tool context with db_session, workspace_id, and user_id.

    Returns:
        Dict with batch_run_id, total_issues, and status.
    """
    try:
        cycle_uuid = UUID(cycle_id)
    except ValueError:
        logger.warning("implement_sprint: invalid cycle_id %s", cycle_id)
        return {"error": f"Invalid cycle_id: {cycle_id}", "started": False}

    try:
        workspace_uuid = UUID(ctx.workspace_id)
    except (ValueError, TypeError):
        logger.warning("implement_sprint: invalid workspace_id %s", ctx.workspace_id)
        return {"error": "Invalid workspace_id in tool context", "started": False}

    try:
        actor_user_id = UUID(ctx.user_id) if ctx.user_id else None
    except (ValueError, TypeError):
        logger.warning("implement_sprint: invalid user_id %s", ctx.user_id)
        actor_user_id = None

    if actor_user_id is None:
        return {"error": "User ID is required to trigger sprint implementation", "started": False}

    try:
        from pilot_space.application.services.batch_run_service import (
            BatchRunService,
            CreateBatchRunPayload,
        )
        from pilot_space.infrastructure.queue.models import QueueName

        service = BatchRunService(session=ctx.db_session)
        payload = CreateBatchRunPayload(
            workspace_id=workspace_uuid,
            cycle_id=cycle_uuid,
            triggered_by_id=actor_user_id,
        )
        batch_run = await service.create_batch_run(payload)

        # Commit so the worker can read the batch run
        await ctx.db_session.commit()

        logger.info(
            "implement_sprint: created batch_run=%s cycle=%s total_issues=%d",
            batch_run.id,
            cycle_id,
            batch_run.total_issues,
        )

        # Enqueue pgmq trigger for BatchImplWorker (non-fatal if queue unavailable)
        try:
            from pilot_space.container.container import get_container

            queue_client = get_container().queue_client()
            if queue_client is not None:
                await queue_client.enqueue(
                    QueueName.BATCH_IMPL,
                    {
                        "batch_run_id": str(batch_run.id),
                        "workspace_id": str(workspace_uuid),
                        "actor_user_id": str(actor_user_id),
                    },
                )
                logger.info(
                    "implement_sprint: enqueued BATCH_IMPL trigger for batch_run=%s",
                    batch_run.id,
                )
            else:
                logger.warning(
                    "implement_sprint: queue_client unavailable, BATCH_IMPL not enqueued for "
                    "batch_run=%s — worker will not start automatically",
                    batch_run.id,
                )
        except Exception as queue_exc:
            # Enqueue failure is non-fatal: batch run is persisted, worker can be triggered manually
            logger.error(
                "implement_sprint: failed to enqueue BATCH_IMPL for batch_run=%s: %s",
                batch_run.id,
                queue_exc,
                exc_info=True,
            )

        return {
            "started": True,
            "batch_run_id": str(batch_run.id),
            "cycle_id": cycle_id,
            "total_issues": batch_run.total_issues,
            "status": "PENDING",
            "message": (
                f"Sprint implementation started. Batch run {batch_run.id} created with "
                f"{batch_run.total_issues} issue(s). The BatchImplWorker will process them "
                "in dependency order with up to 3 concurrent subprocesses. "
                "Monitor progress via the batch runs API."
            ),
        }
    except Exception as exc:
        logger.error(
            "implement_sprint: error for cycle %s: %s",
            cycle_id,
            exc,
            exc_info=True,
        )
        return {
            "error": f"Failed to start sprint implementation: {exc}",
            "started": False,
        }


__all__ = [
    "preview_sprint_implementation",
    "implement_sprint",
]
