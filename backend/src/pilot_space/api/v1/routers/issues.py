"""Issues API router - Activities & Comments.

Provides cross-workspace activity feeds and comment endpoints.
All issue CRUD operations are handled via workspace-scoped routes in workspace_issues.py.

This router handles:
- GET /issues/{issue_id}/activities - Activity timeline (cross-workspace with header)
- POST /issues/{issue_id}/comments - Add comment (cross-workspace with header)
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from pilot_space.api.v1.dependencies import (
    ActivityServiceDep,
)
from pilot_space.api.v1.schemas.issue import (
    ActivityResponse,
    ActivityTimelineResponse,
    CommentCreateRequest,
    UserBriefSchema,
)
from pilot_space.dependencies.auth import SessionDep, get_current_user_id
from pilot_space.dependencies.workspace import get_current_workspace_id
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/issues",
    tags=["Issues"],
    responses={
        401: {"description": "Not authenticated - missing or invalid JWT token"},
        403: {"description": "Not authorized to access this resource"},
        500: {"description": "Internal server error"},
    },
)


# ============================================================================
# Activity & Comment Endpoints (Cross-Workspace)
# ============================================================================
#
# Note: All issue CRUD operations should use workspace-scoped routes:
# - POST /api/v1/workspaces/{workspace_id}/issues
# - GET /api/v1/workspaces/{workspace_id}/issues
# - GET /api/v1/workspaces/{workspace_id}/issues/{issue_id}
# - PATCH /api/v1/workspaces/{workspace_id}/issues/{issue_id}
# - DELETE /api/v1/workspaces/{workspace_id}/issues/{issue_id}
#
# These endpoints handle cross-workspace activity feeds and comments.


@router.get(
    "/{issue_id}/activities",
    response_model=ActivityTimelineResponse,
    summary="Get issue activity timeline",
    description="""
Retrieve the activity timeline for an issue, including:

- Field changes (state, priority, assignee, etc.)
- Comments
- AI suggestion decisions
- Integration events (commits, PRs linked)

Activities are ordered by creation time (newest first).
""",
    responses={
        200: {"description": "Activity timeline retrieved"},
        404: {"description": "Issue not found"},
    },
)
async def get_issue_activities(
    issue_id: Annotated[UUID, "Issue UUID"],
    session: SessionDep,
    activity_service: ActivityServiceDep,
    limit: Annotated[
        int, Query(ge=1, le=100, description="Maximum number of activities to return")
    ] = 50,
    offset: Annotated[int, Query(ge=0, description="Number of activities to skip")] = 0,
    include_comments: Annotated[bool, Query(description="Include comment activities")] = True,
) -> ActivityTimelineResponse:
    """Get activity timeline for an issue including changes and comments."""
    result = await activity_service.get_timeline(
        issue_id,
        limit=limit,
        offset=offset,
        include_comments=include_comments,
    )

    return ActivityTimelineResponse(
        activities=[
            ActivityResponse(
                id=a.id,
                activity_type=a.activity_type.value,
                field=a.field,
                old_value=a.old_value,
                new_value=a.new_value,
                comment=a.comment,
                metadata=a.activity_metadata,
                created_at=a.created_at,
                actor=UserBriefSchema.model_validate(a.actor) if a.actor else None,
            )
            for a in result.activities
        ],
        total=result.total,
    )


@router.post(
    "/{issue_id}/comments",
    response_model=ActivityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a comment",
)
async def add_comment(
    issue_id: UUID,
    request: CommentCreateRequest,
    session: SessionDep,
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    activity_service: ActivityServiceDep,
) -> ActivityResponse:
    """Add a comment to an issue.

    Args:
        issue_id: Issue UUID.
        request: Comment request.
        workspace_id: Current workspace.
        user_id: Current user.
        activity_service: Activity service.

    Returns:
        Created comment activity.
    """
    activity = await activity_service.add_comment(
        workspace_id=workspace_id,
        issue_id=issue_id,
        actor_id=user_id,
        comment_text=request.content,
    )

    return ActivityResponse(
        id=activity.id,
        activity_type=activity.activity_type.value,
        field=activity.field,
        old_value=activity.old_value,
        new_value=activity.new_value,
        comment=activity.comment,
        metadata=activity.activity_metadata,
        created_at=activity.created_at,
        actor=UserBriefSchema.model_validate(activity.actor) if activity.actor else None,
    )


__all__ = ["router"]
