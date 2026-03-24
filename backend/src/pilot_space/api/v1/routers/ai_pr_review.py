"""PR Review Streaming Router.

T202: SSE streaming endpoint for PR review with aspect-by-aspect progress.

Provides:
- SSE streaming endpoint with aspect progress events
- Integration with PRReviewSubagent via Claude Agent SDK
- Structured output with 5 review aspects
- Token usage and cost tracking

Events emitted by PRReviewSubagent (pre-formatted SSE strings):
- 'text_delta': { messageId: str, delta: str }
- 'message_stop': { messageId: str, stopReason: str }
- 'error': { type: str, error_type: str, message: str }

Frontend integration: PRReviewStore expects events at URL:
  POST /api/v1/ai/repos/{repo_id}/prs/{pr_number}/review
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from pilot_space.ai.agents.agent_base import AgentContext
from pilot_space.ai.agents.subagents.pr_review_subagent import PRReviewInput, PRReviewSubagent
from pilot_space.api.v1.streaming import format_sse_event
from pilot_space.dependencies import (
    CurrentUserId,
    DbSession,
    get_current_workspace_id,
)
from pilot_space.domain.exceptions import ServiceUnavailableError
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/ai", tags=["AI", "PR Review"])


# ============================================================================
# Schemas
# ============================================================================


class StreamPRReviewRequest(BaseModel):
    """Request body for streaming PR review.

    Attributes:
        include_architecture: Include architecture review aspect.
        include_security: Include security scanning aspect.
        include_performance: Include performance analysis aspect.
        post_comments: Post review comments back to GitHub PR.
        force_refresh: If true, bypass cache and re-review.
    """

    include_architecture: bool = Field(
        default=True,
        description="Include architecture review",
    )
    include_security: bool = Field(
        default=True,
        description="Include security scanning",
    )
    include_performance: bool = Field(
        default=True,
        description="Include performance analysis",
    )
    post_comments: bool = Field(
        default=False,
        description="Post review comments to GitHub PR (MVP: disabled by default)",
    )
    force_refresh: bool = Field(
        default=False,
        description="Force refresh, bypass cache",
    )


# ============================================================================
# Streaming Endpoint
# ============================================================================


@router.post(
    "/repos/{repo_id}/prs/{pr_number}/review",
    response_class=StreamingResponse,
    status_code=status.HTTP_200_OK,
    summary="Stream PR review with aspect progress",
    description=(
        "Stream an AI-powered PR review via Server-Sent Events.\n\n"
        "Fetches PR details and diff from GitHub using the workspace GitHub integration, "
        "then runs a multi-aspect review (architecture, security, performance, quality, docs) "
        "via PRReviewSubagent and streams findings as SSE events.\n\n"
        "**SSE Events**:\n"
        "- `text_delta`: Incremental review text chunks\n"
        "- `message_stop`: Review completed\n"
        "- `error`: Review failed\n\n"
        "**Auth**: Requires `Authorization: Bearer <token>` and `X-Workspace-Id` header."
    ),
)
async def stream_pr_review(
    request: Request,
    session: DbSession,
    user_id: CurrentUserId,
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    repo_id: Annotated[UUID, Path(description="Repository UUID")],
    pr_number: Annotated[int, Path(description="PR number", ge=1)],
    review_request: StreamPRReviewRequest,
) -> StreamingResponse:
    """Stream PR review generation with aspect-by-aspect progress.

    Looks up the active GitHub integration for the workspace, constructs
    PRReviewSubagent with DI-provided infrastructure, and streams SSE events.

    Args:
        request: FastAPI request for container access and disconnect detection.
        session: Async database session (scoped to request).
        user_id: Current authenticated user ID.
        workspace_id: Current workspace ID from X-Workspace-Id header or middleware.
        repo_id: Repository UUID (used as repository_id in PRReviewInput).
        pr_number: Pull request number.
        review_request: Request body with review aspect flags.

    Returns:
        StreamingResponse with text/event-stream content type.
    """
    from pilot_space.ai.infrastructure.cost_tracker import CostTracker
    from pilot_space.infrastructure.database.repositories.integration_repository import (
        IntegrationRepository,
    )

    # Resolve AI infrastructure from DI container
    if not hasattr(request.app.state, "container"):
        raise ServiceUnavailableError("Service temporarily unavailable")

    container = request.app.state.container
    provider_selector = container.provider_selector()
    resilient_executor = container.resilient_executor()
    cost_tracker = CostTracker(session=session)

    # Look up active GitHub integration for this workspace
    integration_repo = IntegrationRepository(session)
    integration = await integration_repo.get_active_github(workspace_id)

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events from PRReviewSubagent stream."""
        if integration is None:
            logger.warning(
                "No active GitHub integration for workspace %s — cannot stream PR review",
                workspace_id,
            )
            yield format_sse_event(
                "error",
                {
                    "type": "error",
                    "error_type": "integration_not_found",
                    "message": (
                        "No active GitHub integration found for this workspace. "
                        "Connect GitHub in workspace settings to enable PR reviews."
                    ),
                },
            )
            return

        subagent = PRReviewSubagent(
            provider_selector=provider_selector,
            cost_tracker=cost_tracker,
            resilient_executor=resilient_executor,
        )

        pr_input = PRReviewInput(
            repository_id=repo_id,
            pr_number=pr_number,
            include_architecture=review_request.include_architecture,
            include_security=review_request.include_security,
            include_performance=review_request.include_performance,
        )

        context = AgentContext(
            workspace_id=workspace_id,
            user_id=user_id,
            metadata={"db_session": session},
        )

        try:
            async for chunk in subagent.stream(pr_input, context):
                if await request.is_disconnected():
                    logger.debug(
                        "Client disconnected during PR review stream for PR #%d", pr_number
                    )
                    return
                yield chunk
        except Exception:
            logger.exception(
                "Unhandled error streaming PR review for repo %s PR #%d",
                repo_id,
                pr_number,
            )
            yield format_sse_event(
                "error",
                {
                    "type": "error",
                    "error_type": "stream_error",
                    "message": "PR review stream failed. Please try again.",
                },
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


__all__ = ["router"]
