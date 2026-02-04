"""AI Chat Reconnection Endpoints.

Handles reconnection scenarios when users navigate away and return.
"""

from __future__ import annotations

import logging
from datetime import UTC
from typing import TYPE_CHECKING, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from pilot_space.api.v1.dependencies import get_current_user
from pilot_space.infrastructure.database.repositories import (
    AgentSessionRepository,
    ApprovalRequestRepository,
    ConversationTurnRepository,
)

if TYPE_CHECKING:
    from pilot_space.domain.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/chat", tags=["ai-chat-reconnect"])


class JobStatus(BaseModel):
    """Job status response for reconnection."""

    job_id: UUID
    conversation_id: UUID
    status: str  # QUEUED, PROCESSING, WAITING_APPROVAL, COMPLETED, FAILED, CANCELLED
    can_reconnect: bool

    # For active jobs
    stream_url: str | None = None
    estimated_completion_seconds: int | None = None

    # For completed jobs
    response: str | None = None
    token_usage: dict | None = None
    processing_time_ms: int | None = None

    # For approval jobs
    pending_approval: dict | None = None

    # For failed jobs
    error: dict | None = None

    # Recovery info
    partial_response: str | None = None  # What was generated before disconnect
    resume_from_event: int | None = None  # Event index to resume from


class ConversationSnapshot(BaseModel):
    """Full conversation state for reconnection."""

    conversation_id: UUID
    session_status: str
    total_turns: int
    last_activity_at: str

    # Recent turns (last 5)
    recent_turns: list[dict]

    # Active job if any
    active_job: JobStatus | None = None

    # Pending approvals
    pending_approvals: list[dict] = []


@router.get("/conversations/{conversation_id}/status")
async def get_conversation_status(
    conversation_id: UUID,
    user: User = Depends(get_current_user),
    session_repo: AgentSessionRepository = Depends(),
    turn_repo: ConversationTurnRepository = Depends(),
    approval_repo: ApprovalRequestRepository = Depends(),
) -> ConversationSnapshot:
    """Get full conversation status for reconnection.

    Use this endpoint when user navigates to conversation page to determine:
    - Is there an active job running?
    - Are there pending approvals?
    - What's the conversation history?

    Frontend logic:
    ```typescript
    const snapshot = await getConversationStatus(conversationId);

    if (snapshot.active_job?.status === 'PROCESSING') {
        // Reconnect to SSE stream
        connectSSE(snapshot.active_job.stream_url);
    } else if (snapshot.pending_approvals.length > 0) {
        // Show approval UI
        showApprovalDialog(snapshot.pending_approvals[0]);
    } else {
        // Just show conversation history
        displayHistory(snapshot.recent_turns);
    }
    ```
    """
    # Get session
    session = await session_repo.get_by_conversation_id(conversation_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found",
        )

    # Verify user access
    if session.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Get recent turns
    recent_turns = await turn_repo.get_recent_turns(conversation_id=conversation_id, limit=5)

    # Check for active job (turn with completed_at = NULL)
    active_turn = await turn_repo.get_active_turn(conversation_id)
    active_job = None

    if active_turn:
        # Job is still running
        active_job = JobStatus(
            job_id=active_turn.job_id,
            conversation_id=conversation_id,
            status="PROCESSING",
            can_reconnect=True,
            stream_url=f"/api/v1/ai/chat/stream/{active_turn.job_id}",
            estimated_completion_seconds=_estimate_completion_time(active_turn),
            partial_response=await _get_partial_response(active_turn.job_id),
        )

    # Check for pending approvals
    pending_approvals = await approval_repo.get_pending_approvals(conversation_id=conversation_id)

    if pending_approvals:
        # Update active_job status if waiting for approval
        if active_job:
            active_job.status = "WAITING_APPROVAL"
            active_job.pending_approval = {
                "approval_id": str(pending_approvals[0].id),
                "tool_name": pending_approvals[0].tool_name,
                "tool_params": pending_approvals[0].tool_params,
                "risk_level": pending_approvals[0].risk_level,
                "requested_at": pending_approvals[0].requested_at.isoformat(),
                "timeout_at": pending_approvals[0].timeout_at.isoformat(),
            }

    return ConversationSnapshot(
        conversation_id=conversation_id,
        session_status=session.status,
        total_turns=await turn_repo.count_turns(conversation_id),
        last_activity_at=session.updated_at.isoformat(),
        recent_turns=[
            {
                "id": str(turn.id),
                "role": turn.role,
                "content": turn.content,
                "tool_calls": turn.tool_calls or [],
                "timestamp": turn.created_at.isoformat(),
                "completed": turn.completed_at is not None,
            }
            for turn in recent_turns
        ],
        active_job=active_job,
        pending_approvals=[
            {
                "id": str(approval.id),
                "tool_name": approval.tool_name,
                "risk_level": approval.risk_level,
                "requested_at": approval.requested_at.isoformat(),
            }
            for approval in pending_approvals
        ],
    )


@router.get("/jobs/{job_id}/status")
async def get_job_status(
    job_id: UUID,
    user: User = Depends(get_current_user),
    turn_repo: ConversationTurnRepository = Depends(),
    approval_repo: ApprovalRequestRepository = Depends(),
) -> JobStatus:
    """Get status of a specific job.

    Lightweight endpoint for polling job status without full conversation context.

    Use cases:
    - Poll while waiting for job completion
    - Check if SSE reconnection is possible
    - Get partial results if job was interrupted
    """
    turn = await turn_repo.get_by_job_id(job_id)
    if not turn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found")

    # Verify user access
    session = await turn_repo.get_session_for_turn(turn.id)
    if session.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Determine status
    if turn.completed_at:
        # Job finished
        return JobStatus(
            job_id=job_id,
            conversation_id=turn.conversation_id,
            status="COMPLETED",
            can_reconnect=False,
            response=turn.content,
            token_usage=turn.token_usage,
            processing_time_ms=turn.processing_time_ms,
        )

    # Job still running - check for approval
    pending_approval = await approval_repo.get_pending_for_turn(turn.id)

    if pending_approval:
        return JobStatus(
            job_id=job_id,
            conversation_id=turn.conversation_id,
            status="WAITING_APPROVAL",
            can_reconnect=True,
            stream_url=f"/api/v1/ai/chat/stream/{job_id}",
            pending_approval={
                "approval_id": str(pending_approval.id),
                "tool_name": pending_approval.tool_name,
                "tool_params": pending_approval.tool_params,
                "risk_level": pending_approval.risk_level,
            },
            partial_response=await _get_partial_response(job_id),
        )

    # Job still processing
    return JobStatus(
        job_id=job_id,
        conversation_id=turn.conversation_id,
        status="PROCESSING",
        can_reconnect=True,
        stream_url=f"/api/v1/ai/chat/stream/{job_id}",
        estimated_completion_seconds=_estimate_completion_time(turn),
        partial_response=await _get_partial_response(job_id),
    )


@router.get("/stream/{job_id}/events")
async def get_stream_events(
    job_id: UUID,
    after_event: int = 0,  # Resume from this event index
    user: User = Depends(get_current_user),
    turn_repo: ConversationTurnRepository = Depends(),
) -> dict:
    """Get historical stream events for a job.

    Use this to catch up on events that were missed during disconnect.

    Frontend usage:
    ```typescript
    // User reconnects after disconnect
    const lastEventIndex = localStorage.getItem(`last_event_${jobId}`);
    const missedEvents = await getStreamEvents(jobId, lastEventIndex);

    // Replay missed events
    missedEvents.events.forEach(event => {
        handleSSEEvent(event);
    });

    // Then reconnect to live stream
    connectSSE(jobId);
    ```
    """
    import json

    from pilot_space.infrastructure.cache.redis_client import get_redis

    try:
        redis = get_redis()

        # Get events from Redis (we store them for 5 minutes)
        events_key = f"stream:events:{job_id}"
        all_events = await redis.lrange(events_key, 0, -1)
    except Exception:
        logger.warning("Redis error fetching stream events for job %s", job_id)
        all_events = []

    # Parse and filter events after the specified index
    missed_events = []
    for i, event_json in enumerate(all_events):
        if i > after_event:
            missed_events.append(json.loads(event_json))

    return {
        "job_id": str(job_id),
        "total_events": len(all_events),
        "missed_events": len(missed_events),
        "events": missed_events,
        "can_resume_stream": await _can_resume_stream(job_id),
    }


# Helper functions


def _estimate_completion_time(turn: Any) -> int:
    """Estimate time until job completion based on average processing time.

    Args:
        turn: A conversation turn object with a created_at datetime attribute.

    Returns:
        Estimated seconds until completion.
    """
    from datetime import datetime

    elapsed = (datetime.now(UTC) - turn.created_at).total_seconds()

    # Simple heuristic: most jobs complete in 30s
    # Future: use historical data based on message length, context, etc.
    avg_completion_time = 30
    remaining = max(0, avg_completion_time - elapsed)

    return int(remaining)


async def _get_partial_response(job_id: UUID) -> str | None:
    """Get partial response generated before disconnect.

    We store partial responses in Redis as they stream.
    Returns None gracefully on Redis errors.
    """
    try:
        from pilot_space.infrastructure.cache.redis_client import get_redis

        redis = get_redis()
        partial_key = f"partial:response:{job_id}"
        partial = await redis.get(partial_key)

        return partial.decode() if partial else None
    except Exception:
        logger.warning("Redis error fetching partial response for job %s", job_id)
        return None


async def _can_resume_stream(job_id: UUID) -> bool:
    """Check if SSE stream can still be resumed.

    Returns False gracefully on Redis errors.
    """
    try:
        from pilot_space.infrastructure.cache.redis_client import get_redis

        redis = get_redis()

        # Check if worker is still processing
        stream_active_key = f"stream:active:{job_id}"
        return await redis.exists(stream_active_key) > 0
    except Exception:
        logger.warning("Redis error checking stream status for job %s", job_id)
        return False
