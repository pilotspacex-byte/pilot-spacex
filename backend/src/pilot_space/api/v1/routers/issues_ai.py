"""Issues AI API router.

AI-related issue endpoints extracted from issues.py to meet 700 line limit.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from pilot_space.api.v1.schemas.ai_suggestion import (
    AssigneeRecommendationRequest,
    AssigneeRecommendationsResponse,
    DuplicateCheckRequest,
    DuplicateCheckResponse,
    IssueEnhancementRequest,
    IssueEnhancementResponse,
    SuggestionDecisionRequest,
    SuggestionDecisionResponse,
)
from pilot_space.dependencies import (
    CurrentUserIdOrDemo,
    DbSession,
    get_activity_service,
    get_ai_config_or_demo,
    get_current_workspace_id,
)

router = APIRouter(prefix="/issues", tags=["issues-ai"])


@router.post("/ai/enhance", response_model=IssueEnhancementResponse, summary="Enhance issue (DEPRECATED)")
async def enhance_issue(
    request: IssueEnhancementRequest,
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    user_id: CurrentUserIdOrDemo,
    session: DbSession,
    ai_config: Annotated[..., Depends(get_ai_config_or_demo)],
) -> IssueEnhancementResponse:
    """Get AI suggestions for issue enhancement.

    DEPRECATED: This endpoint needs migration to SDK orchestrator pattern.
    Currently returns empty results until migration is complete.
    """
    from fastapi import HTTPException

    # TODO: Migrate to SDK orchestrator pattern
    # See get_sdk_orchestrator dependency and SDKOrchestrator.execute()
    raise HTTPException(
        status_code=501,
        detail="Issue enhancement endpoint requires SDK migration. Use manual enhancement for now."
    )


@router.post(
    "/ai/check-duplicates",
    response_model=DuplicateCheckResponse,
    summary="Check for duplicates (DEPRECATED)",
)
async def check_duplicates(
    request: DuplicateCheckRequest,
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    user_id: CurrentUserIdOrDemo,
    session: DbSession,
    ai_config: Annotated[..., Depends(get_ai_config_or_demo)],
) -> DuplicateCheckResponse:
    """Check for potential duplicate issues using vector similarity.

    DEPRECATED: This endpoint needs migration to SDK orchestrator pattern.
    Currently returns empty results until migration is complete.
    """
    from fastapi import HTTPException

    # TODO: Migrate to SDK orchestrator pattern
    # See get_sdk_orchestrator dependency and SDKOrchestrator.execute()
    raise HTTPException(
        status_code=501,
        detail="Duplicate detection endpoint requires SDK migration. Use manual search for now."
    )


@router.post(
    "/ai/recommend-assignee",
    response_model=AssigneeRecommendationsResponse,
    summary="Get assignee recommendations (DEPRECATED)",
)
async def recommend_assignee(
    request: AssigneeRecommendationRequest,
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    user_id: CurrentUserIdOrDemo,
    session: DbSession,
) -> AssigneeRecommendationsResponse:
    """Get AI-powered assignee recommendations based on expertise and workload.

    DEPRECATED: This endpoint needs migration to SDK orchestrator pattern.
    Currently returns empty results until migration is complete.
    """
    from fastapi import HTTPException

    # TODO: Migrate to SDK orchestrator pattern
    # See get_sdk_orchestrator dependency and SDKOrchestrator.execute()
    raise HTTPException(
        status_code=501,
        detail="Assignee recommendation endpoint requires SDK migration. Use manual assignment for now."
    )


@router.post(
    "/{issue_id}/ai/suggestion-decision",
    response_model=SuggestionDecisionResponse,
    summary="Record suggestion decision",
)
async def record_suggestion_decision(
    issue_id: UUID,
    request: SuggestionDecisionRequest,
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    user_id: CurrentUserIdOrDemo,
    activity_service: Annotated[..., Depends(get_activity_service)],
) -> SuggestionDecisionResponse:
    """Record user's decision on an AI suggestion for analytics."""
    activity = await activity_service.log_suggestion_decision(
        workspace_id=workspace_id,
        issue_id=issue_id,
        actor_id=user_id,
        suggestion_type=request.suggestion_type,
        accepted=request.accepted,
        suggestion_details={"value": request.suggestion_value},
    )

    return SuggestionDecisionResponse(recorded=True, activity_id=activity.id)


__all__ = ["router"]
