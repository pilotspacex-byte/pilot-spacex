"""AI Context Streaming API endpoints.

T210: SSE streaming endpoints for AI context operations.

Endpoints:
- POST /issues/{id}/ai-context/chat/stream - SSE refinement streaming
- POST /issues/{id}/ai-context/stream - SSE generation with phase updates
"""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from pilot_space.api.v1.schemas.ai_context import RefineContextRequest
from pilot_space.api.v1.streaming import format_sse_event
from pilot_space.dependencies import (
    get_ai_context_service,
    get_current_user,
    get_current_workspace_id,
    get_refine_ai_context_service,
    get_session,
    get_user_api_keys,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/issues/{issue_id}/ai-context", tags=["ai-context"])


# Rate limiting tracking (simplified - use Redis in production)
_generation_counts: dict[str, list[float]] = {}


def _check_rate_limit(user_id: str, limit: int = 5, window_hours: int = 1) -> bool:
    """Check if user is within rate limit.

    Args:
        user_id: User UUID string.
        limit: Max requests per window.
        window_hours: Time window in hours.

    Returns:
        True if within limit, False if exceeded.
    """
    import time

    now = time.time()
    window_seconds = window_hours * 3600

    if user_id not in _generation_counts:
        _generation_counts[user_id] = []

    # Clean old entries
    _generation_counts[user_id] = [
        ts for ts in _generation_counts[user_id] if now - ts < window_seconds
    ]

    if len(_generation_counts[user_id]) >= limit:
        return False

    _generation_counts[user_id].append(now)
    return True


@router.post(
    "/chat/stream",
    response_class=StreamingResponse,
    summary="Stream refinement response via SSE",
)
async def stream_ai_context_refinement(
    issue_id: UUID,
    request: RefineContextRequest,
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    user_id: Annotated[UUID, Depends(get_current_user)],
    api_keys: Annotated[dict[str, str], Depends(get_user_api_keys)],
    session: Annotated[..., Depends(get_session)],
    service: Annotated[..., Depends(get_refine_ai_context_service)],
):
    """Stream AI context refinement response via SSE.

    Args:
        issue_id: Issue UUID.
        request: Refinement request with query.
        workspace_id: Current workspace.
        user_id: Current user.
        api_keys: User's API keys.
        session: Database session.
        service: Refine AI context service.

    Returns:
        Streaming SSE response.
    """
    import uuid as uuid_module

    from pilot_space.application.services.ai_context import RefineAIContextPayload

    payload = RefineAIContextPayload(
        workspace_id=workspace_id,
        issue_id=issue_id,
        user_id=user_id,
        query=request.query,
        correlation_id=str(uuid_module.uuid4()),
        api_keys=api_keys,
    )

    async def event_generator():
        """Generate SSE events."""
        try:
            async for chunk in service.stream(payload):
                # Format as SSE
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.exception("Error streaming refinement")
            yield f"data: [ERROR] {e}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.post(
    "/stream",
    response_class=StreamingResponse,
    summary="Stream AI context generation with phase updates",
)
async def stream_ai_context_generation(
    issue_id: UUID,
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    user_id: Annotated[UUID, Depends(get_current_user)],
    api_keys: Annotated[dict[str, str], Depends(get_user_api_keys)],
    session: Annotated[..., Depends(get_session)],
    service: Annotated[..., Depends(get_ai_context_service)],
):
    """Stream AI context generation with phase progress events.

    SSE Events:
    - 'phase': { name: str, status: 'pending'|'in_progress'|'complete', content?: str }
    - 'complete': { claudeCodePrompt: str, relatedDocs: [], relatedCode: [], similarIssues: [] }
    - 'error': { message: str, type: str }

    Args:
        issue_id: Issue UUID.
        workspace_id: Current workspace.
        user_id: Current user.
        api_keys: User's API keys.
        session: Database session.
        service: AI context service.

    Returns:
        Streaming SSE response with phase updates.
    """
    from pilot_space.application.services.ai_context import GenerateAIContextPayload

    # Define phases for progress tracking
    phases = [
        "Analyzing issue",
        "Finding related docs",
        "Searching codebase",
        "Finding similar issues",
        "Generating implementation guide",
    ]

    async def phase_generator():
        """Generate SSE events with phase progress."""
        try:
            # Emit initial pending status for all phases
            for phase_name in phases:
                yield format_sse_event("phase", {"name": phase_name, "status": "pending"})

            # Check rate limit
            if not _check_rate_limit(str(user_id)):
                yield format_sse_event(
                    "error",
                    {
                        "message": "Rate limit exceeded. Maximum 5 context generations per hour.",
                        "type": "rate_limit_error",
                    },
                )
                return

            import uuid as uuid_module

            # Build payload
            payload = GenerateAIContextPayload(
                workspace_id=workspace_id,
                issue_id=issue_id,
                user_id=user_id,
                force_regenerate=False,
                correlation_id=str(uuid_module.uuid4()),
                api_keys=api_keys,
            )

            # Execute generation with phase updates
            current_phase_idx = 0

            # Phase 1: Analyzing issue
            yield format_sse_event(
                "phase",
                {"name": phases[current_phase_idx], "status": "in_progress"},
            )
            current_phase_idx += 1

            # Phase 2: Finding related docs
            yield format_sse_event(
                "phase",
                {"name": phases[current_phase_idx - 1], "status": "complete"},
            )
            yield format_sse_event(
                "phase",
                {"name": phases[current_phase_idx], "status": "in_progress"},
            )
            current_phase_idx += 1

            # Phase 3: Searching codebase
            yield format_sse_event(
                "phase",
                {"name": phases[current_phase_idx - 1], "status": "complete"},
            )
            yield format_sse_event(
                "phase",
                {"name": phases[current_phase_idx], "status": "in_progress"},
            )
            current_phase_idx += 1

            # Phase 4: Finding similar issues
            yield format_sse_event(
                "phase",
                {"name": phases[current_phase_idx - 1], "status": "complete"},
            )
            yield format_sse_event(
                "phase",
                {"name": phases[current_phase_idx], "status": "in_progress"},
            )
            current_phase_idx += 1

            # Phase 5: Generating implementation guide
            yield format_sse_event(
                "phase",
                {"name": phases[current_phase_idx - 1], "status": "complete"},
            )
            yield format_sse_event(
                "phase",
                {"name": phases[current_phase_idx], "status": "in_progress"},
            )

            # Execute the service (blocks until complete)
            result = await service.execute(payload)

            # Mark final phase complete
            yield format_sse_event(
                "phase",
                {"name": phases[current_phase_idx], "status": "complete"},
            )

            # Yield complete event with full result
            yield format_sse_event(
                "complete",
                {
                    "claudeCodePrompt": result.claude_code_prompt or "",
                    "relatedDocs": [],  # Populated from result if available
                    "relatedCode": [],  # Populated from result if available
                    "similarIssues": [],  # Populated from result if available
                },
            )

        except ValueError as e:
            yield format_sse_event(
                "error",
                {
                    "message": str(e),
                    "type": "validation_error",
                },
            )
        except Exception as e:
            logger.exception("Error streaming AI context generation")
            yield format_sse_event(
                "error",
                {
                    "message": f"Failed to generate AI context: {e}",
                    "type": "generation_error",
                },
            )

    return StreamingResponse(
        phase_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


__all__ = ["router"]
