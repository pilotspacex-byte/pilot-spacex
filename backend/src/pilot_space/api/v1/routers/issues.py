"""Issues API router.

T142-T144: Create Issue CRUD, AI enhancement, and activity endpoints.
T330: Enhanced OpenAPI documentation for all endpoints.
"""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from pilot_space.api.v1.schemas.issue import (
    ActivityResponse,
    ActivityTimelineResponse,
    CommentCreateRequest,
    IssueCreateRequest,
    IssueListResponse,
    IssueResponse,
    IssueUpdateRequest,
)
from pilot_space.dependencies import (
    get_activity_service,
    get_create_issue_service,
    get_current_user,
    get_current_workspace_id,
    get_db_session_dep,
    get_get_issue_service,
    get_list_issues_service,
    get_update_issue_service,
)

logger = logging.getLogger(__name__)

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
# Issue CRUD Endpoints
# ============================================================================


@router.post(
    "",
    response_model=IssueResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new issue",
    description="""
Create a new issue in the specified project.

When `enhance_with_ai` is set to true, the issue description will be enhanced
with AI-generated suggestions including improved clarity, acceptance criteria,
and technical considerations.

**Required fields:**
- `name`: Issue title (1-255 characters)
- `project_id`: UUID of the project

**Optional fields:**
- `description`: Markdown description
- `priority`: none, low, medium, high, urgent
- `assignee_id`: User to assign the issue to
- `label_ids`: List of label UUIDs to attach
""",
    responses={
        201: {"description": "Issue created successfully"},
        400: {"description": "Invalid input data - validation error"},
        404: {"description": "Project or referenced entity not found"},
        422: {"description": "Unprocessable entity - validation error details"},
    },
)
async def create_issue(
    request: IssueCreateRequest,
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    user_id: Annotated[UUID, Depends(get_current_user)],
    create_service: Annotated[..., Depends(get_create_issue_service)],
) -> IssueResponse:
    """Create a new issue in the specified project with optional AI enhancement.

    - **name**: Required. Issue title (max 255 chars)
    - **project_id**: Required. UUID of the project
    - **description**: Optional. Markdown description
    - **enhance_with_ai**: Optional. If true, AI will enhance the description
    """
    from pilot_space.application.services.issue import CreateIssuePayload

    payload = CreateIssuePayload(
        workspace_id=workspace_id,
        project_id=request.project_id,
        reporter_id=user_id,
        name=request.name,
        description=request.description,
        description_html=request.description_html,
        priority=request.priority,
        state_id=request.state_id,
        assignee_id=request.assignee_id,
        cycle_id=request.cycle_id,
        module_id=request.module_id,
        parent_id=request.parent_id,
        estimate_points=request.estimate_points,
        start_date=request.start_date,
        target_date=request.target_date,
        label_ids=request.label_ids,
        ai_enhanced=request.enhance_with_ai,
    )

    result = await create_service.execute(payload)
    return IssueResponse.from_issue(result.issue)


@router.get(
    "",
    response_model=IssueListResponse,
    summary="List issues with filtering and pagination",
    description="""
Retrieve a paginated list of issues in the workspace with optional filtering.

**Filtering options:**
- Filter by project, states, assignees, labels, cycle, or module
- Full-text search across title and description
- Combine multiple filters for precise queries

**Pagination:**
- Cursor-based pagination for consistent results
- Default page size: 20, max: 100

**Sorting:**
- Sort by: created_at, updated_at, priority, name
- Order: asc or desc
""",
    responses={
        200: {"description": "Paginated list of issues"},
        400: {"description": "Invalid filter parameters"},
    },
)
async def list_issues(
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    list_service: Annotated[..., Depends(get_list_issues_service)],
    project_id: Annotated[UUID | None, Query(description="Filter by project ID")] = None,
    state_ids: Annotated[list[UUID] | None, Query(description="Filter by state IDs")] = None,
    assignee_ids: Annotated[list[UUID] | None, Query(description="Filter by assignee IDs")] = None,
    label_ids: Annotated[list[UUID] | None, Query(description="Filter by label IDs")] = None,
    cycle_id: Annotated[UUID | None, Query(description="Filter by cycle ID")] = None,
    module_id: Annotated[UUID | None, Query(description="Filter by module ID")] = None,
    search: Annotated[
        str | None, Query(description="Search term for title and description")
    ] = None,
    cursor: Annotated[
        str | None, Query(description="Pagination cursor from previous response")
    ] = None,
    page_size: Annotated[int, Query(ge=1, le=100, description="Number of items per page")] = 20,
    sort_by: Annotated[
        str, Query(description="Field to sort by (created_at, updated_at, priority, name)")
    ] = "created_at",
    sort_order: Annotated[
        str, Query(pattern="^(asc|desc)$", description="Sort order: asc or desc")
    ] = "desc",
) -> IssueListResponse:
    """List issues with filtering and cursor-based pagination.

    - **project_id**: Filter by project
    - **state_ids**: Filter by workflow states
    - **assignee_ids**: Filter by assigned users
    - **search**: Full-text search in title and description
    - **cursor**: Pagination cursor from previous response
    """
    from pilot_space.application.services.issue import ListIssuesPayload

    payload = ListIssuesPayload(
        workspace_id=workspace_id,
        project_id=project_id,
        state_ids=state_ids,
        assignee_ids=assignee_ids,
        label_ids=label_ids,
        cycle_id=cycle_id,
        module_id=module_id,
        search_term=search,
        cursor=cursor,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    result = await list_service.execute(payload)

    return IssueListResponse(
        items=[IssueResponse.from_issue(i) for i in result.items],
        total=result.total,
        next_cursor=result.next_cursor,
        prev_cursor=result.prev_cursor,
        has_next=result.has_next,
        has_prev=result.has_prev,
        page_size=result.page_size,
    )


@router.get(
    "/{issue_id}",
    response_model=IssueResponse,
    summary="Get issue by ID",
    description="Retrieve detailed information about a specific issue including related entities.",
    responses={
        200: {"description": "Issue details retrieved successfully"},
        404: {"description": "Issue not found"},
    },
)
async def get_issue(
    issue_id: Annotated[UUID, "Issue UUID"],
    get_service: Annotated[..., Depends(get_get_issue_service)],
) -> IssueResponse:
    """Get a specific issue by its UUID.

    Returns full issue details including project, state, assignee, labels, and AI metadata.
    """
    result = await get_service.execute(issue_id)
    if not result.found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Issue not found: {issue_id}",
        )
    return IssueResponse.from_issue(result.issue)


@router.get(
    "/identifier/{identifier}",
    response_model=IssueResponse,
    summary="Get issue by human-readable identifier",
    description="""
Retrieve an issue using its human-readable identifier (e.g., PILOT-123).

The identifier format is `{PROJECT_IDENTIFIER}-{SEQUENCE_NUMBER}`.
""",
    responses={
        200: {"description": "Issue details retrieved successfully"},
        400: {"description": "Invalid identifier format"},
        404: {"description": "Issue not found with the given identifier"},
    },
)
async def get_issue_by_identifier(
    identifier: Annotated[str, "Human-readable identifier (e.g., PILOT-123)"],
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    get_service: Annotated[..., Depends(get_get_issue_service)],
) -> IssueResponse:
    """Get an issue by human-readable identifier (e.g., PILOT-123).

    - **identifier**: Format is PROJECT-NUMBER (e.g., PILOT-123)
    """
    try:
        result = await get_service.execute_by_identifier(workspace_id, identifier)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    if not result.found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Issue not found: {identifier}",
        )
    return IssueResponse.from_issue(result.issue)


@router.patch(
    "/{issue_id}",
    response_model=IssueResponse,
    summary="Update an issue",
    description="""
Update one or more fields of an existing issue.

Only fields included in the request body will be updated.
Use `clear_*` flags to explicitly remove optional values.

**Clear flags:**
- `clear_assignee`: Remove assignee
- `clear_cycle`: Remove from cycle
- `clear_module`: Remove from module
- `clear_parent`: Remove parent issue
- `clear_estimate`: Clear estimate points
- `clear_start_date`: Clear start date
- `clear_target_date`: Clear target date
""",
    responses={
        200: {"description": "Issue updated successfully"},
        400: {"description": "Invalid update data"},
        404: {"description": "Issue not found"},
        422: {"description": "Validation error in update data"},
    },
)
async def update_issue(
    issue_id: Annotated[UUID, "Issue UUID to update"],
    request: IssueUpdateRequest,
    user_id: Annotated[UUID, Depends(get_current_user)],
    update_service: Annotated[..., Depends(get_update_issue_service)],
) -> IssueResponse:
    """Update an existing issue with partial data.

    - Only included fields are updated
    - Use clear_* flags to remove optional values
    """
    from pilot_space.application.services.issue.update_issue_service import (
        UNCHANGED,
        UpdateIssuePayload,
    )

    # Build payload with explicit handling of clear flags
    payload = UpdateIssuePayload(
        issue_id=issue_id,
        actor_id=user_id,
        name=request.name if request.name is not None else UNCHANGED,
        description=request.description if request.description is not None else UNCHANGED,
        description_html=request.description_html
        if request.description_html is not None
        else UNCHANGED,
        priority=request.priority if request.priority is not None else UNCHANGED,
        state_id=request.state_id if request.state_id is not None else UNCHANGED,
        assignee_id=None
        if request.clear_assignee
        else (request.assignee_id if request.assignee_id is not None else UNCHANGED),
        cycle_id=None
        if request.clear_cycle
        else (request.cycle_id if request.cycle_id is not None else UNCHANGED),
        module_id=None
        if request.clear_module
        else (request.module_id if request.module_id is not None else UNCHANGED),
        parent_id=None
        if request.clear_parent
        else (request.parent_id if request.parent_id is not None else UNCHANGED),
        estimate_points=None
        if request.clear_estimate
        else (request.estimate_points if request.estimate_points is not None else UNCHANGED),
        start_date=None
        if request.clear_start_date
        else (request.start_date if request.start_date is not None else UNCHANGED),
        target_date=None
        if request.clear_target_date
        else (request.target_date if request.target_date is not None else UNCHANGED),
        sort_order=request.sort_order if request.sort_order is not None else UNCHANGED,
        label_ids=request.label_ids if request.label_ids is not None else UNCHANGED,
    )

    try:
        result = await update_service.execute(payload)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    return IssueResponse.from_issue(result.issue)


@router.delete(
    "/{issue_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an issue (soft delete)",
    description="""
Soft delete an issue. The issue is marked as deleted but not permanently removed.

Deleted issues can be restored by an administrator if needed.
""",
    responses={
        204: {"description": "Issue deleted successfully"},
        404: {"description": "Issue not found"},
    },
)
async def delete_issue(
    issue_id: Annotated[UUID, "Issue UUID to delete"],
    user_id: Annotated[UUID, Depends(get_current_user)],
    session: Annotated[..., Depends(get_db_session_dep)],
) -> None:
    """Soft delete an issue by marking it as deleted."""
    from pilot_space.infrastructure.database.repositories import IssueRepository

    repo = IssueRepository(session)
    issue = await repo.get_by_id(issue_id)
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Issue not found: {issue_id}",
        )

    await repo.delete(issue)
    await session.commit()


# ============================================================================
# Activity Endpoints
# ============================================================================


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
    activity_service: Annotated[..., Depends(get_activity_service)],
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
                actor=a.actor,
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
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    user_id: Annotated[UUID, Depends(get_current_user)],
    activity_service: Annotated[..., Depends(get_activity_service)],
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
        actor=activity.actor,
    )


__all__ = ["router"]
