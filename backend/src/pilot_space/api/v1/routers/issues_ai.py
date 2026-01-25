"""Issues AI API router.

AI-related issue endpoints extracted from issues.py to meet 700 line limit.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from pilot_space.api.v1.schemas.ai_suggestion import (
    AssigneeRecommendationRequest,
    AssigneeRecommendationResponse,
    AssigneeRecommendationsResponse,
    DuplicateCandidateResponse,
    DuplicateCheckRequest,
    DuplicateCheckResponse,
    IssueEnhancementRequest,
    IssueEnhancementResponse,
    LabelSuggestion,
    PrioritySuggestion,
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


@router.post("/ai/enhance", response_model=IssueEnhancementResponse, summary="Enhance issue")
async def enhance_issue(
    request: IssueEnhancementRequest,
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    user_id: CurrentUserIdOrDemo,
    session: DbSession,
    ai_config: Annotated[..., Depends(get_ai_config_or_demo)],
) -> IssueEnhancementResponse:
    """Get AI suggestions for issue enhancement."""
    from pilot_space.ai.agents import (
        AgentContext,
        IssueEnhancementInput,
        IssueEnhancerAgent,
        Provider,
    )
    from pilot_space.infrastructure.database.repositories import LabelRepository

    label_repo = LabelRepository(session)
    labels = await label_repo.get_workspace_labels(workspace_id, project_id=request.project_id)
    label_names = [label.name for label in labels]

    context = AgentContext(
        workspace_id=workspace_id,
        user_id=user_id,
        correlation_id=str(user_id),
        api_keys={Provider.CLAUDE: ai_config.anthropic_key if ai_config else ""},
    )

    agent = IssueEnhancerAgent()
    input_data = IssueEnhancementInput(
        title=request.title,
        description=request.description,
        available_labels=label_names,
    )

    result = await agent.execute(input_data, context)
    output = result.output

    return IssueEnhancementResponse(
        enhanced_title=output.enhanced_title,
        enhanced_description=output.enhanced_description,
        suggested_labels=[
            LabelSuggestion(
                name=str(label["name"]),
                confidence=float(label["confidence"]),
                is_existing=str(label["name"]) in label_names,
            )
            for label in output.suggested_labels
        ],
        suggested_priority=PrioritySuggestion(
            priority=str(output.suggested_priority["priority"]),
            confidence=float(output.suggested_priority["confidence"]),
        )
        if output.suggested_priority
        else None,
        title_enhanced=output.title_enhanced,
        description_expanded=output.description_expanded,
    )


@router.post(
    "/ai/check-duplicates",
    response_model=DuplicateCheckResponse,
    summary="Check for duplicates",
)
async def check_duplicates(
    request: DuplicateCheckRequest,
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    user_id: CurrentUserIdOrDemo,
    session: DbSession,
    ai_config: Annotated[..., Depends(get_ai_config_or_demo)],
) -> DuplicateCheckResponse:
    """Check for potential duplicate issues using vector similarity."""
    from pilot_space.ai.agents import (
        AgentContext,
        DuplicateDetectionInput,
        DuplicateDetectorAgent,
        Provider,
    )

    context = AgentContext(
        workspace_id=workspace_id,
        user_id=user_id,
        correlation_id=str(user_id),
        api_keys={Provider.OPENAI: ai_config.openai_key if ai_config else ""},
    )

    agent = DuplicateDetectorAgent(session)
    input_data = DuplicateDetectionInput(
        title=request.title,
        description=request.description,
        workspace_id=workspace_id,
        project_id=request.project_id,
        exclude_issue_id=request.exclude_issue_id,
        threshold=request.threshold,
    )

    result = await agent.execute(input_data, context)
    output = result.output

    return DuplicateCheckResponse(
        candidates=[
            DuplicateCandidateResponse(
                issue_id=c.issue_id,
                identifier=c.identifier,
                title=c.title,
                similarity=c.similarity,
                explanation=c.explanation,
            )
            for c in output.candidates
        ],
        has_likely_duplicate=output.has_likely_duplicate,
        highest_similarity=output.highest_similarity,
    )


@router.post(
    "/ai/recommend-assignee",
    response_model=AssigneeRecommendationsResponse,
    summary="Get assignee recommendations",
)
async def recommend_assignee(
    request: AssigneeRecommendationRequest,
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    user_id: CurrentUserIdOrDemo,
    session: DbSession,
) -> AssigneeRecommendationsResponse:
    """Get AI-powered assignee recommendations based on expertise and workload."""
    from pilot_space.ai.agents import (
        AgentContext,
        AssigneeRecommendationInput,
        AssigneeRecommenderAgent,
    )

    context = AgentContext(
        workspace_id=workspace_id,
        user_id=user_id,
        correlation_id=str(user_id),
    )

    agent = AssigneeRecommenderAgent(session)
    input_data = AssigneeRecommendationInput(
        issue_title=request.title,
        issue_description=request.description,
        issue_labels=request.label_names,
        workspace_id=workspace_id,
        project_id=request.project_id,
    )

    result = await agent.execute(input_data, context)
    output = result.output

    return AssigneeRecommendationsResponse(
        recommendations=[
            AssigneeRecommendationResponse(
                user_id=r.user_id,
                name=r.name,
                confidence=r.confidence,
                reason=r.reason,
            )
            for r in output.recommendations
        ],
        has_strong_match=output.has_strong_match,
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
