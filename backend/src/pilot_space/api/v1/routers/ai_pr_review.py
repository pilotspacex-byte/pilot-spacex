"""PR Review Streaming Router.

T202: Add SSE streaming endpoint for PR review with aspect-by-aspect progress.

Provides:
- SSE streaming endpoint with aspect progress events
- Integration with PRReviewAgent via SDKOrchestrator
- Structured output with 5 review aspects
- Token usage and cost tracking

Events emitted:
- 'aspect': { aspect: str, status: 'pending'|'in_progress'|'complete' }
- 'complete': { result: PRReviewResult, tokenUsage: TokenUsage }
- 'error': { message: str, type: str }

Frontend integration: PRReviewStore expects events at URL:
  POST /api/v1/ai/repos/{repo_id}/prs/{pr_number}/review
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from pilot_space.ai.agents.agent_base import AgentContext
from pilot_space.ai.agents.pr_review_agent import (
    PRReviewInput,
)
from pilot_space.api.v1.streaming import format_sse_event
from pilot_space.dependencies import get_current_user_id, get_sdk_orchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI", "PR Review"])


# ============================================================================
# Schemas
# ============================================================================


class StreamPRReviewRequest(BaseModel):
    """Request body for streaming PR review.

    Attributes:
        repository: Repository in owner/repo format.
        force_refresh: If true, bypass cache and re-review.
    """

    repository: str = Field(
        ...,
        pattern=r"^[^/]+/[^/]+$",
        description="Repository in owner/repo format",
        examples=["owner/repo"],
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
    summary="Stream PR review with aspect progress",
    description=(
        "Stream PR review generation with aspect-by-aspect progress. "
        "Returns SSE events for each review aspect (architecture, security, "
        "quality, performance, documentation) plus final result."
    ),
)
async def stream_pr_review(
    request: Request,
    repo_id: Annotated[UUID, Path(description="Repository UUID")],
    pr_number: Annotated[int, Path(description="PR number", ge=1)],
    review_request: StreamPRReviewRequest,
    orchestrator: Annotated[..., Depends(get_sdk_orchestrator)],
    user_id: Annotated[UUID, Depends(get_current_user_id)],
):
    """Stream PR review generation with aspect-by-aspect progress.

    This endpoint integrates with the frontend PRReviewStore which expects:
    1. Initial 'aspect' events with status='pending' for all aspects
    2. Progressive 'aspect' events with status='in_progress'/'complete'
    3. Final 'complete' event with full result and token usage
    4. 'error' event if anything fails

    Args:
        request: FastAPI request for workspace context and disconnect detection.
        repo_id: Repository UUID.
        pr_number: Pull request number.
        review_request: Request body with repository and force_refresh.
        orchestrator: SDK orchestrator with registered agents.
        user_id: Current user ID from auth.

    Returns:
        StreamingResponse with SSE events.

    Raises:
        HTTPException: If workspace context missing or agent not found.
    """
    # Get workspace ID from request state
    workspace_id = getattr(request.state, "workspace_id", None)
    if workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Workspace-ID header required",
        )

    async def aspect_generator() -> AsyncIterator[str]:
        """Generate SSE events with aspect progress."""
        aspects: list[str] = [
            "architecture",
            "security",
            "quality",
            "performance",
            "documentation",
        ]

        try:
            # Yield initial pending status for all aspects
            for aspect in aspects:
                yield format_sse_event("aspect", {"aspect": aspect, "status": "pending"})

            # Check for client disconnect early
            if await request.is_disconnected():
                logger.info("Client disconnected before review started")
                return

            # Prepare agent context
            context = AgentContext(
                workspace_id=workspace_id,
                user_id=user_id,
                metadata={
                    "repo_id": str(repo_id),
                    "pr_number": pr_number,
                    "repository": review_request.repository,
                },
            )

            # TODO: Fetch PR details from GitHub integration
            # For now, create minimal input for testing
            # In production, this should fetch diff and files via GitHub API
            input_data = PRReviewInput(
                pr_number=pr_number,
                pr_title=f"PR #{pr_number}",
                pr_description="PR review request",
                diff="# TODO: Fetch actual diff from GitHub",
                file_contents={},
                changed_files=[],
                project_context={"repository": review_request.repository},
            )

            # Stream from PR review agent
            result_chunks: list[str] = []
            current_aspect_idx = 0
            aspect_markers = [
                ("architecture", ["## Architecture", "### Architecture"]),
                ("security", ["## Security", "### Security"]),
                ("quality", ["## Code Quality", "## Quality", "### Quality"]),
                ("performance", ["## Performance", "### Performance"]),
                ("documentation", ["## Documentation", "### Documentation"]),
            ]

            logger.info(
                "Starting PR review stream",
                extra={
                    "repo_id": str(repo_id),
                    "pr_number": pr_number,
                    "workspace_id": str(workspace_id),
                    "user_id": str(user_id),
                },
            )

            # Stream tokens from agent
            try:
                async for chunk in orchestrator.stream("pr_review", input_data, context):
                    # Check for client disconnect during streaming
                    if await request.is_disconnected():
                        logger.info("Client disconnected during review")
                        return

                    # Detect aspect transitions in output
                    chunk_lower = chunk.lower()
                    for i, (aspect_name, markers) in enumerate(aspect_markers):
                        if any(marker.lower() in chunk_lower for marker in markers):
                            # Mark previous aspects as complete
                            if current_aspect_idx < i:
                                for j in range(current_aspect_idx, i):
                                    yield format_sse_event(
                                        "aspect",
                                        {
                                            "aspect": aspect_markers[j][0],
                                            "status": "complete",
                                        },
                                    )

                                current_aspect_idx = i
                                yield format_sse_event(
                                    "aspect",
                                    {"aspect": aspect_name, "status": "in_progress"},
                                )
                            break

                    result_chunks.append(chunk)

                # Mark all remaining aspects complete
                for i in range(current_aspect_idx, len(aspects)):
                    yield format_sse_event(
                        "aspect",
                        {"aspect": aspects[i], "status": "complete"},
                    )

                # Build complete result
                full_result = "".join(result_chunks)

                # Parse result into structured format
                # TODO: Implement proper parsing logic
                # For now, return basic structure
                result_data = {
                    "summary": full_result[:500] if full_result else "Review completed",
                    "architecture": [],
                    "security": [],
                    "quality": [],
                    "performance": [],
                    "documentation": [],
                }

                # Estimate token usage (actual tracking via cost_tracker)
                token_usage = {
                    "inputTokens": 0,  # TODO: Track actual input tokens
                    "outputTokens": len(full_result),
                    "estimatedCostUsd": 0.0,
                }

                # Yield complete event
                yield format_sse_event(
                    "complete",
                    {
                        "result": result_data,
                        "tokenUsage": token_usage,
                    },
                )

                logger.info(
                    "PR review completed successfully",
                    extra={
                        "repo_id": str(repo_id),
                        "pr_number": pr_number,
                        "output_length": len(full_result),
                    },
                )

            except Exception as stream_error:
                logger.exception(
                    "Error during PR review stream",
                    extra={
                        "repo_id": str(repo_id),
                        "pr_number": pr_number,
                        "error": str(stream_error),
                    },
                )
                yield format_sse_event(
                    "error",
                    {
                        "message": f"Review stream error: {stream_error}",
                        "type": type(stream_error).__name__,
                    },
                )

        except Exception as e:
            logger.exception(
                "Error initializing PR review",
                extra={
                    "repo_id": str(repo_id),
                    "pr_number": pr_number,
                    "error": str(e),
                },
            )
            yield format_sse_event(
                "error",
                {
                    "message": f"Failed to initialize review: {e}",
                    "type": type(e).__name__,
                },
            )

    return StreamingResponse(
        aspect_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


__all__ = ["router"]
