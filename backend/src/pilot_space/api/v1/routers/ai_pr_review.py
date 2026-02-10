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

**MVP STATUS: NOT IMPLEMENTED - Phase 2 Feature**
This endpoint requires GitHub API integration to fetch PR details.
See: specs/002-github-integration/spec.md
"""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from pydantic import BaseModel, Field

from pilot_space.dependencies import PilotSpaceAgentDep, get_current_user_id

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
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="[Phase 2] Stream PR review with aspect progress",
    description=(
        "**NOT IMPLEMENTED - Phase 2 Feature**\n\n"
        "This endpoint is pending GitHub API integration. "
        "Current MVP does not support automated PR reviews.\n\n"
        "Phase 2 implementation will:\n"
        "- Fetch PR diff, files, and metadata from GitHub API\n"
        "- Generate aspect-by-aspect reviews (architecture, security, quality, performance, docs)\n"
        "- Return SSE stream with progressive updates\n\n"
        "See: specs/002-github-integration/spec.md"
    ),
)
async def stream_pr_review(
    request: Request,
    repo_id: Annotated[UUID, Path(description="Repository UUID")],
    pr_number: Annotated[int, Path(description="PR number", ge=1)],
    review_request: StreamPRReviewRequest,
    agent: PilotSpaceAgentDep,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
):
    """Stream PR review generation with aspect-by-aspect progress.

    **MVP LIMITATION: This endpoint is not yet implemented.**

    Phase 2 will integrate GitHub API to fetch PR details and generate reviews.

    Args:
        request: FastAPI request for workspace context and disconnect detection.
        repo_id: Repository UUID.
        pr_number: Pull request number.
        review_request: Request body with repository and force_refresh.
        agent: PilotSpaceAgent instance.
        user_id: Current user ID from auth.

    Raises:
        HTTPException: 501 NOT_IMPLEMENTED (always, pending Phase 2).
    """
    # MVP: This endpoint is not yet implemented - pending GitHub API integration
    # Original implementation available in git history - will be restored in Phase 2
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
            "message": "PR review endpoint pending GitHub integration (Phase 2)",
            "status": "not_implemented",
            "feature": "ai_pr_review",
            "phase": 2,
            "documentation": "specs/002-github-integration/spec.md",
            "workaround": "Use GitHub's native PR review features until Phase 2 implementation",
        },
    )


__all__ = ["router"]
