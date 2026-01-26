"""AI API router.

Main router that aggregates AI-powered feature endpoints:
- Cost tracking and analytics (ai_costs.py)
- Approval queue management (ai_approvals.py)
- Note analysis and margin annotations (ai_annotations.py)
- Issue extraction from notes (ai_extraction.py)
- PR review status

T096: AI router implementation.
T091-T094: Cost tracking endpoints.
T069: Margin annotations.
T058-T059: Issue extraction and approval.
T073-T075: Approval queue endpoints.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Path, status
from pydantic import BaseModel, Field

from pilot_space.api.v1.routers.ai_annotations import router as annotations_router
from pilot_space.api.v1.routers.ai_approvals import router as approvals_router
from pilot_space.api.v1.routers.ai_costs import router as costs_router
from pilot_space.api.v1.routers.ai_extraction import router as extraction_router

router = APIRouter(prefix="/ai", tags=["AI"])

# Include sub-routers
router.include_router(costs_router)
router.include_router(approvals_router)
router.include_router(annotations_router)
router.include_router(extraction_router)


# Shared schemas for deprecated endpoints


class ChatRequest(BaseModel):
    """DEPRECATED: Chat request schema."""

    message: str = Field(description="User message")
    context: dict[str, Any] | None = Field(default=None, description="Optional context")


class ChatResponse(BaseModel):
    """DEPRECATED: Chat response schema."""

    response: str = Field(description="AI response")


class HealthResponse(BaseModel):
    """DEPRECATED: Health check response schema."""

    status: str = Field(description="Overall status")
    providers: dict[str, Any] = Field(description="Provider status details")


# PR Review Status (T199)


@router.get(
    "/pr-review/{job_id}",
    summary="Get PR review status",
    description="Check status of a PR review job.",
)
async def get_pr_review_status(
    job_id: Annotated[str, Path(description="Job ID from trigger response")],
) -> dict[str, Any]:
    """Get status of a PR review job.

    Args:
        job_id: Job identifier from trigger response.

    Returns:
        Job status and results (if completed).
    """
    from pilot_space.application.services.ai import (
        GetPRReviewStatusService,
    )
    from pilot_space.container import get_container

    container = get_container()
    cache_client = container.redis_client() if container.redis_client else None

    service = GetPRReviewStatusService(cache_client=cache_client)
    result = await service.execute(job_id)

    if not result.found or not result.job_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    job_info = result.job_info

    # Calculate progress estimate
    progress_percent = 0
    if job_info.status.value == "queued":
        progress_percent = 10
    elif job_info.status.value == "processing":
        progress_percent = 50
    elif job_info.status.value in {"completed", "failed"}:
        progress_percent = 100

    # Build response
    response_data: dict[str, Any] = {
        "job_id": job_info.job_id,
        "status": job_info.status.value,
        "repository": job_info.repository,
        "pr_number": job_info.pr_number,
        "queued_at": job_info.queued_at.isoformat(),
        "started_at": job_info.started_at.isoformat() if job_info.started_at else None,
        "completed_at": job_info.completed_at.isoformat() if job_info.completed_at else None,
        "progress_percent": progress_percent,
        "error": job_info.error,
    }

    # Add result data if available
    if job_info.result:
        response_data["summary"] = {
            "summary": job_info.result.get("review_summary", ""),
            "approval_recommendation": job_info.result.get("approval_recommendation", "comment"),
            "critical_count": job_info.result.get("critical_count", 0),
            "warning_count": job_info.result.get("warning_count", 0),
        }

    return response_data


__all__ = ["router"]
