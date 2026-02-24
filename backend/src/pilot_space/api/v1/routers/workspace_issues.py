"""Workspace-scoped Issues API router.

Provides nested routes for issues under workspaces.
GET /workspaces/{workspace_id}/issues
GET /workspaces/{workspace_id}/issues/{issue_id}
POST /workspaces/{workspace_id}/issues
etc.

Supports both UUID and slug for workspace identification.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select

from pilot_space.api.v1.dependencies import (
    CreateIssueServiceDep,
    DeleteIssueServiceDep,
    GetIssueServiceDep,
    ListIssuesServiceDep,
    UpdateIssueServiceDep,
    WorkspaceRepositoryDep,
)
from pilot_space.api.v1.schemas.base import BaseSchema, DeleteResponse, PaginatedResponse
from pilot_space.api.v1.schemas.issue import IssueResponse
from pilot_space.dependencies import DbSession, SyncedUserId
from pilot_space.dependencies.auth import SessionDep
from pilot_space.infrastructure.database.models.issue import Issue, IssuePriority
from pilot_space.infrastructure.database.models.state import State
from pilot_space.infrastructure.database.models.workspace import Workspace
from pilot_space.infrastructure.database.rls import set_rls_context
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ============================================================================
# Schemas for workspace-scoped issues (matching frontend types)
# ============================================================================


class WorkspaceIssueResponse(BaseSchema):
    """Issue response matching frontend Issue type."""

    id: UUID
    identifier: str
    name: str
    description: str | None = None
    state: str
    priority: str
    type: str = Field(default="task")
    project_id: UUID | None = None
    assignee_id: UUID | None = None
    reporter_id: UUID
    labels: list[dict[str, Any]] = Field(default_factory=list)
    due_date: str | None = None
    estimated_hours: float | None = None
    ai_generated: bool = False
    source_note_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class WorkspaceIssueCreateRequest(BaseSchema):
    """Create issue request matching frontend CreateIssueData."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    project_id: UUID | None = None
    state: str = Field(default="backlog")
    priority: str = Field(default="none")
    type: str = Field(default="task")
    assignee_id: UUID | None = None
    labels: list[str] = Field(default_factory=list)
    due_date: str | None = None
    estimated_hours: float | None = None
    source_note_id: UUID | None = None

    @field_validator("project_id", "assignee_id", "source_note_id", mode="before")
    @classmethod
    def empty_string_to_none(cls, v: Any) -> Any:
        """Convert empty strings to None for optional UUID fields."""
        if v == "":
            return None
        return v


class WorkspaceIssueUpdateRequest(BaseSchema):
    """Update issue request matching frontend UpdateIssueData."""

    name: str | None = None
    description: str | None = None
    description_html: str | None = None
    priority: str | None = None
    state_id: UUID | None = None
    assignee_id: UUID | None = None
    cycle_id: UUID | None = None
    estimate_points: int | None = None
    # T-245: Time estimate in hours (0.5 increments)
    estimate_hours: float | None = None
    start_date: str | None = None
    target_date: str | None = None
    sort_order: int | None = None
    label_ids: list[UUID] | None = None

    # Clear flags
    clear_assignee: bool = False
    clear_cycle: bool = False
    clear_estimate: bool = False
    clear_start_date: bool = False
    clear_target_date: bool = False


class StateUpdateRequest(BaseModel):
    """Request body for state update."""

    state: str


# ============================================================================
# Helper functions
# ============================================================================


# Repository dependencies are now centralized in api/v1/dependencies.py

# Accept string to support both UUID and slug
WorkspaceIdOrSlug = Annotated[str, Path(description="Workspace ID (UUID) or slug")]
IssueIdPath = Annotated[UUID, Path(description="Issue ID")]


def _is_valid_uuid(value: str) -> bool:
    """Check if a string is a valid UUID."""
    try:
        UUID(value)
        return True
    except ValueError:
        return False


async def _resolve_workspace(
    workspace_id_or_slug: str,
    workspace_repo: WorkspaceRepositoryDep,
) -> Workspace:
    """Resolve workspace by UUID or slug (scalar-only, no relationships).

    Uses lazyload to prevent the Workspace model's 7 default selectin
    relationships from firing. Only scalar columns (id, slug, name, etc.)
    are loaded. Use this for validation/ownership checks.
    """
    if _is_valid_uuid(workspace_id_or_slug):
        workspace = await workspace_repo.get_by_id_scalar(UUID(workspace_id_or_slug))
    else:
        workspace = await workspace_repo.get_by_slug_scalar(workspace_id_or_slug)

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    return workspace


def _issue_to_response(issue: Issue) -> WorkspaceIssueResponse:
    """Convert Issue model to WorkspaceIssueResponse schema."""
    # Get state name from relationship or default to "backlog"
    state_name = "backlog"
    if hasattr(issue, "state") and issue.state:
        state_name = issue.state.name.lower().replace(" ", "_")

    return WorkspaceIssueResponse(
        id=issue.id,
        identifier=issue.identifier or f"ISSUE-{issue.sequence_id}",
        name=issue.name,
        description=issue.description,
        state=state_name,
        priority=issue.priority.value if issue.priority else "none",
        type="task",  # Default type
        project_id=issue.project_id,
        assignee_id=issue.assignee_id,
        reporter_id=issue.reporter_id,
        labels=[],  # TODO: Add label relations
        due_date=issue.target_date.isoformat() if issue.target_date else None,
        estimated_hours=float(issue.estimate_hours) if issue.estimate_hours is not None else None,
        ai_generated=issue.has_ai_enhancements,
        source_note_id=None,
        created_at=issue.created_at,
        updated_at=issue.updated_at,
    )


# ============================================================================
# Endpoints
# ============================================================================


@router.get(
    "/{workspace_id}/issues",
    response_model=PaginatedResponse[WorkspaceIssueResponse],
    tags=["workspace-issues"],
    summary="List issues in workspace",
)
async def list_workspace_issues(
    workspace_id: WorkspaceIdOrSlug,
    current_user_id: SyncedUserId,
    list_service: ListIssuesServiceDep,
    workspace_repo: WorkspaceRepositoryDep,
    session: SessionDep,
    project_id: Annotated[UUID | None, Query(description="Filter by project")] = None,
    state: Annotated[str | None, Query(description="Filter by state")] = None,
    priority: Annotated[str | None, Query(description="Filter by priority")] = None,
    assignee_id: Annotated[UUID | None, Query(description="Filter by assignee")] = None,
    search: Annotated[str | None, Query(description="Search query")] = None,
    cursor: Annotated[str | None, Query(description="Pagination cursor")] = None,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
) -> PaginatedResponse[WorkspaceIssueResponse]:
    """List all issues in a workspace."""
    from pilot_space.application.services.issue import ListIssuesPayload

    workspace = await _resolve_workspace(workspace_id, workspace_repo)
    await set_rls_context(session, current_user_id, workspace.id)

    # Build service payload
    payload = ListIssuesPayload(
        workspace_id=workspace.id,
        project_id=project_id,
        assignee_ids=[assignee_id] if assignee_id else None,
        search_term=search,
        cursor=cursor,
        page_size=page_size,
        sort_by="created_at",
        sort_order="desc",
    )

    # Execute service
    result = await list_service.execute(payload)

    items = [_issue_to_response(issue) for issue in result.items]

    return PaginatedResponse(
        items=items,
        total=result.total,
        next_cursor=result.next_cursor,
        prev_cursor=result.prev_cursor,
        has_next=result.has_next,
        has_prev=result.has_prev,
        page_size=page_size,
    )


@router.get(
    "/{workspace_id}/issues/{issue_id}",
    response_model=IssueResponse,
    tags=["workspace-issues"],
    summary="Get issue by ID",
)
async def get_workspace_issue(
    session: SessionDep,
    workspace_id: WorkspaceIdOrSlug,
    issue_id: IssueIdPath,
    current_user_id: SyncedUserId,
    get_service: GetIssueServiceDep,
    workspace_repo: WorkspaceRepositoryDep,
) -> IssueResponse:
    """Get a specific issue by ID."""
    workspace = await _resolve_workspace(workspace_id, workspace_repo)
    await set_rls_context(session, current_user_id, workspace.id)

    # Execute service
    result = await get_service.execute(issue_id)
    if not result.found or not result.issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )

    # Verify workspace ownership
    if result.issue.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )

    return IssueResponse.from_issue(result.issue)


@router.post(
    "/{workspace_id}/issues",
    response_model=WorkspaceIssueResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["workspace-issues"],
    summary="Create a new issue",
)
async def create_workspace_issue(
    workspace_id: WorkspaceIdOrSlug,
    issue_data: WorkspaceIssueCreateRequest,
    current_user_id: SyncedUserId,
    session: DbSession,
    create_service: CreateIssueServiceDep,
    workspace_repo: WorkspaceRepositoryDep,
) -> WorkspaceIssueResponse:
    """Create a new issue in the workspace."""
    from pilot_space.application.services.issue import CreateIssuePayload

    workspace = await _resolve_workspace(workspace_id, workspace_repo)
    await set_rls_context(session, current_user_id, workspace.id)

    # Validate project_id is provided (required by service)
    if not issue_data.project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="project_id is required",
        )

    # Map priority string to enum for service payload
    priority_map = {
        "urgent": IssuePriority.URGENT,
        "high": IssuePriority.HIGH,
        "medium": IssuePriority.MEDIUM,
        "low": IssuePriority.LOW,
        "none": IssuePriority.NONE,
    }
    priority = priority_map.get(issue_data.priority.lower(), IssuePriority.NONE)

    # Convert label strings to UUIDs if provided
    label_uuids: list[UUID] = []
    if issue_data.labels:
        try:
            label_uuids = [UUID(label) for label in issue_data.labels]
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid label UUID format: {e}",
            ) from e

    # Build service payload
    payload = CreateIssuePayload(
        workspace_id=workspace.id,
        project_id=issue_data.project_id,
        reporter_id=current_user_id,
        name=issue_data.name,
        description=issue_data.description,
        description_html=None,
        priority=priority,
        state_id=None,  # Service will resolve default state
        assignee_id=issue_data.assignee_id,
        cycle_id=None,
        module_id=None,
        parent_id=None,
        estimate_points=None,
        estimate_hours=issue_data.estimated_hours,
        start_date=None,
        target_date=None,
        label_ids=label_uuids,
        ai_enhanced=False,
    )

    # Execute service
    result = await create_service.execute(payload)

    logger.info(
        "Issue created",
        extra={"issue_id": str(result.issue.id), "workspace_id": str(workspace.id)},
    )

    return _issue_to_response(result.issue)


@router.patch(
    "/{workspace_id}/issues/{issue_id}",
    response_model=IssueResponse,
    tags=["workspace-issues"],
    summary="Update an issue",
)
async def update_workspace_issue(
    workspace_id: WorkspaceIdOrSlug,
    issue_id: IssueIdPath,
    issue_data: WorkspaceIssueUpdateRequest,
    current_user_id: SyncedUserId,
    update_service: UpdateIssueServiceDep,
    workspace_repo: WorkspaceRepositoryDep,
    session: SessionDep,
) -> IssueResponse:
    """Update an existing issue."""
    from pilot_space.application.services.issue.update_issue_service import (
        UNCHANGED,
        UpdateIssuePayload,
    )

    workspace = await _resolve_workspace(workspace_id, workspace_repo)
    await set_rls_context(session, current_user_id, workspace.id)

    # Map priority string to enum if provided
    priority = UNCHANGED
    if issue_data.priority is not None:
        priority_map = {
            "urgent": IssuePriority.URGENT,
            "high": IssuePriority.HIGH,
            "medium": IssuePriority.MEDIUM,
            "low": IssuePriority.LOW,
            "none": IssuePriority.NONE,
        }
        priority = priority_map.get(issue_data.priority.lower(), IssuePriority.NONE)

    # Handle date conversions
    from datetime import date as date_type

    start_date_value = UNCHANGED
    if issue_data.clear_start_date:
        start_date_value = None
    elif issue_data.start_date is not None:
        try:
            start_date_value = date_type.fromisoformat(issue_data.start_date)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid start_date format: {e}",
            ) from e

    target_date_value = UNCHANGED
    if issue_data.clear_target_date:
        target_date_value = None
    elif issue_data.target_date is not None:
        try:
            target_date_value = date_type.fromisoformat(issue_data.target_date)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid target_date format: {e}",
            ) from e

    # Build service payload with explicit handling of clear flags
    payload = UpdateIssuePayload(
        issue_id=issue_id,
        actor_id=current_user_id,
        name=issue_data.name if issue_data.name is not None else UNCHANGED,
        description=issue_data.description if issue_data.description is not None else UNCHANGED,
        description_html=issue_data.description_html
        if issue_data.description_html is not None
        else UNCHANGED,
        priority=priority,
        state_id=issue_data.state_id if issue_data.state_id is not None else UNCHANGED,
        assignee_id=None
        if issue_data.clear_assignee
        else (issue_data.assignee_id if issue_data.assignee_id is not None else UNCHANGED),
        cycle_id=None
        if issue_data.clear_cycle
        else (issue_data.cycle_id if issue_data.cycle_id is not None else UNCHANGED),
        module_id=UNCHANGED,
        parent_id=UNCHANGED,
        estimate_points=None
        if issue_data.clear_estimate
        else (issue_data.estimate_points if issue_data.estimate_points is not None else UNCHANGED),
        estimate_hours=None
        if issue_data.clear_estimate
        else (issue_data.estimate_hours if issue_data.estimate_hours is not None else UNCHANGED),
        start_date=start_date_value,
        target_date=target_date_value,
        sort_order=issue_data.sort_order if issue_data.sort_order is not None else UNCHANGED,
        label_ids=issue_data.label_ids if issue_data.label_ids is not None else UNCHANGED,
    )

    try:
        # Execute service with workspace validation
        result = await update_service.execute(payload)

        # Verify workspace ownership
        if result.issue.workspace_id != workspace.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Issue not found",
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    logger.info(
        "Issue updated",
        extra={"issue_id": str(issue_id), "workspace_id": str(workspace.id)},
    )

    return IssueResponse.from_issue(result.issue)


@router.patch(
    "/{workspace_id}/issues/{issue_id}/state",
    response_model=IssueResponse,
    tags=["workspace-issues"],
    summary="Update issue state",
)
async def update_workspace_issue_state(
    workspace_id: WorkspaceIdOrSlug,
    issue_id: IssueIdPath,
    body: StateUpdateRequest,
    current_user_id: SyncedUserId,
    session: DbSession,
    update_service: UpdateIssueServiceDep,
    workspace_repo: WorkspaceRepositoryDep,
) -> IssueResponse:
    """Update issue state (for Kanban drag/drop)."""
    from pilot_space.application.services.issue.update_issue_service import (
        UNCHANGED,
        UpdateIssuePayload,
    )

    workspace = await _resolve_workspace(workspace_id, workspace_repo)
    await set_rls_context(session, current_user_id, workspace.id)

    # Look up state by name
    state_name = body.state
    state_name_map = {
        "backlog": "Backlog",
        "todo": "Todo",
        "in_progress": "In Progress",
        "in-progress": "In Progress",
        "in_review": "In Review",
        "in-review": "In Review",
        "done": "Done",
        "cancelled": "Cancelled",
        "canceled": "Cancelled",
    }
    normalized_state = state_name_map.get(state_name.lower(), state_name)

    state_result = await session.execute(
        select(State)
        .where(
            State.workspace_id == workspace.id,
            State.name == normalized_state,
            State.is_deleted.is_(False),
        )
        .limit(1)
    )
    new_state = state_result.scalar_one_or_none()
    if not new_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"State '{state_name}' not found",
        )

    # Build service payload (only updating state)
    payload = UpdateIssuePayload(
        issue_id=issue_id,
        actor_id=current_user_id,
        name=UNCHANGED,
        description=UNCHANGED,
        description_html=UNCHANGED,
        priority=UNCHANGED,
        state_id=new_state.id,
        assignee_id=UNCHANGED,
        cycle_id=UNCHANGED,
        module_id=UNCHANGED,
        parent_id=UNCHANGED,
        estimate_points=UNCHANGED,
        start_date=UNCHANGED,
        target_date=UNCHANGED,
        sort_order=UNCHANGED,
        label_ids=UNCHANGED,
    )

    try:
        # Execute service
        result = await update_service.execute(payload)

        # Verify workspace ownership
        if result.issue.workspace_id != workspace.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Issue not found",
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    return IssueResponse.from_issue(result.issue)


@router.delete(
    "/{workspace_id}/issues/{issue_id}",
    response_model=DeleteResponse,
    tags=["workspace-issues"],
    summary="Delete an issue",
)
async def delete_workspace_issue(
    workspace_id: WorkspaceIdOrSlug,
    issue_id: IssueIdPath,
    current_user_id: SyncedUserId,
    delete_service: DeleteIssueServiceDep,
    workspace_repo: WorkspaceRepositoryDep,
    session: SessionDep,
) -> DeleteResponse:
    """Soft delete an issue with activity tracking."""
    from pilot_space.application.services.issue import DeleteIssuePayload

    workspace = await _resolve_workspace(workspace_id, workspace_repo)
    await set_rls_context(session, current_user_id, workspace.id)

    # Verify issue belongs to this workspace BEFORE deleting (prevents IDOR)
    result_row = await session.execute(select(Issue.workspace_id).where(Issue.id == issue_id))
    issue_workspace_id = result_row.scalar_one_or_none()
    if issue_workspace_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")
    if issue_workspace_id != workspace.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    try:
        result = await delete_service.execute(
            DeleteIssuePayload(
                issue_id=issue_id,
                actor_id=current_user_id,
            )
        )

        logger.info(
            "Issue deleted",
            extra={"issue_id": str(issue_id), "workspace_id": str(workspace.id)},
        )

        return DeleteResponse(id=result.issue_id, message="Issue deleted successfully")

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


__all__ = ["router"]
