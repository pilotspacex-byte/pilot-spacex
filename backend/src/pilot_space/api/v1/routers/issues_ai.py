"""Issues AI API router.

AI-related issue endpoints extracted from issues.py to meet 700 line limit.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from pilot_space.api.v1.schemas.ai_suggestion import (
    SuggestionDecisionRequest,
    SuggestionDecisionResponse,
)
from pilot_space.dependencies import (
    CurrentUserId,
    get_activity_service,
    get_current_workspace_id,
)

router = APIRouter(prefix="/issues", tags=["issues-ai"])


@router.post(
    "/{issue_id}/ai/suggestion-decision",
    response_model=SuggestionDecisionResponse,
    summary="Record suggestion decision",
)
async def record_suggestion_decision(
    issue_id: UUID,
    request: SuggestionDecisionRequest,
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    user_id: CurrentUserId,
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
