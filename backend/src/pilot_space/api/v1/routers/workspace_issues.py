"""Workspace-scoped Issues API router.

Provides nested routes for issues under workspaces.
GET /workspaces/{workspace_id}/issues
GET /workspaces/{workspace_id}/issues/{issue_id}
POST /workspaces/{workspace_id}/issues
etc.

Supports both UUID and slug for workspace identification.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select

from pilot_space.api.v1.schemas.base import BaseSchema, DeleteResponse, PaginatedResponse
from pilot_space.api.v1.schemas.issue import IssueResponse
from pilot_space.dependencies import DbSession, SyncedUserId
from pilot_space.infrastructure.database.models.issue import Issue, IssuePriority
from pilot_space.infrastructure.database.models.project import Project
from pilot_space.infrastructure.database.models.state import State
from pilot_space.infrastructure.database.models.workspace import Workspace
from pilot_space.infrastructure.database.repositories.issue_repository import (
    IssueFilters,
    IssueRepository,
)
from pilot_space.infrastructure.database.repositories.workspace_repository import (
    WorkspaceRepository,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Schemas for workspace-scoped issues (matching frontend types)
# ============================================================================


class WorkspaceIssueResponse(BaseSchema):
    """Issue response matching frontend Issue type."""

    id: UUID
    identifier: str
    title: str
    description: str | None = None
    state: str
    priority: str
    type: str = Field(default="task")
    project_id: UUID | None = None
    assignee_id: UUID | None = None
    reporter_id: UUID
    labels: list[dict[str, Any]] = Field(default_factory=list)
    due_date: str | None = None
    estimated_hours: int | None = None
    ai_generated: bool = False
    source_note_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class WorkspaceIssueCreateRequest(BaseSchema):
    """Create issue request matching frontend CreateIssueData."""

    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    project_id: UUID | None = None
    state: str = Field(default="backlog")
    priority: str = Field(default="none")
    type: str = Field(default="task")
    assignee_id: UUID | None = None
    labels: list[str] = Field(default_factory=list)
    due_date: str | None = None
    estimated_hours: int | None = None
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


def get_issue_repository(session: DbSession) -> IssueRepository:
    """Get issue repository with session."""
    return IssueRepository(session=session)


def get_workspace_repository(session: DbSession) -> WorkspaceRepository:
    """Get workspace repository with session."""
    return WorkspaceRepository(session=session)


IssueRepo = Annotated[IssueRepository, Depends(get_issue_repository)]
WorkspaceRepo = Annotated[WorkspaceRepository, Depends(get_workspace_repository)]

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
    workspace_repo: WorkspaceRepository,
) -> Workspace:
    """Resolve workspace by UUID or slug."""
    if _is_valid_uuid(workspace_id_or_slug):
        workspace = await workspace_repo.get_by_id(UUID(workspace_id_or_slug))
    else:
        workspace = await workspace_repo.get_by_slug(workspace_id_or_slug)

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
        title=issue.name,
        description=issue.description,
        state=state_name,
        priority=issue.priority.value if issue.priority else "none",
        type="task",  # Default type
        project_id=issue.project_id,
        assignee_id=issue.assignee_id,
        reporter_id=issue.reporter_id,
        labels=[],  # TODO: Add label relations
        due_date=issue.target_date.isoformat() if issue.target_date else None,
        estimated_hours=issue.estimate_points,
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
    issue_repo: IssueRepo,
    workspace_repo: WorkspaceRepo,
    project_id: Annotated[UUID | None, Query(description="Filter by project")] = None,
    state: Annotated[str | None, Query(description="Filter by state")] = None,
    priority: Annotated[str | None, Query(description="Filter by priority")] = None,
    assignee_id: Annotated[UUID | None, Query(description="Filter by assignee")] = None,
    search: Annotated[str | None, Query(description="Search query")] = None,
    cursor: Annotated[str | None, Query(description="Pagination cursor")] = None,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
) -> PaginatedResponse[WorkspaceIssueResponse]:
    """List all issues in a workspace."""
    workspace = await _resolve_workspace(workspace_id, workspace_repo)

    # Build filters
    filters = IssueFilters(
        project_id=project_id,
        assignee_ids=[assignee_id] if assignee_id else None,
        search_term=search,
    )

    # Get issues using repository method
    page = await issue_repo.get_workspace_issues(
        workspace.id,
        filters=filters,
        cursor=cursor,
        page_size=page_size,
    )

    items = [_issue_to_response(issue) for issue in page.items]

    return PaginatedResponse(
        items=items,
        total=page.total,
        next_cursor=page.next_cursor,
        prev_cursor=page.prev_cursor,
        has_next=page.has_next,
        has_prev=page.has_prev,
        page_size=page_size,
    )


@router.get(
    "/{workspace_id}/issues/{issue_id}",
    response_model=IssueResponse,
    tags=["workspace-issues"],
    summary="Get issue by ID",
)
async def get_workspace_issue(
    workspace_id: WorkspaceIdOrSlug,
    issue_id: IssueIdPath,
    current_user_id: SyncedUserId,
    issue_repo: IssueRepo,
    workspace_repo: WorkspaceRepo,
) -> IssueResponse:
    """Get a specific issue by ID."""
    workspace = await _resolve_workspace(workspace_id, workspace_repo)

    issue = await issue_repo.get_by_id_with_relations(issue_id)
    if not issue or issue.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )

    return IssueResponse.from_issue(issue)


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
    issue_repo: IssueRepo,
    workspace_repo: WorkspaceRepo,
) -> WorkspaceIssueResponse:
    """Create a new issue in the workspace."""
    workspace = await _resolve_workspace(workspace_id, workspace_repo)

    # Look up state by name (case-insensitive match)
    state_name = issue_data.state or "Backlog"
    # Normalize common frontend state names to DB names
    state_name_map = {
        "backlog": "Backlog",
        "todo": "Todo",
        "in_progress": "In Progress",
        "in-progress": "In Progress",
        "inprogress": "In Progress",
        "in_review": "In Review",
        "in-review": "In Review",
        "inreview": "In Review",
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
    state = state_result.scalar_one_or_none()
    if not state:
        # Fall back to first state (Backlog)
        state_result = await session.execute(
            select(State)
            .where(State.workspace_id == workspace.id, State.is_deleted.is_(False))
            .order_by(State.sequence)
            .limit(1)
        )
        state = state_result.scalar_one_or_none()
        if not state:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No workflow states configured for this workspace",
            )

    # Get project - use provided or first available
    project_id = issue_data.project_id
    if not project_id:
        proj_result = await session.execute(
            select(Project)
            .where(Project.workspace_id == workspace.id, Project.is_deleted.is_(False))
            .limit(1)
        )
        project = proj_result.scalar_one_or_none()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No projects configured for this workspace",
            )
        project_id = project.id

    # Get next sequence ID for this project
    next_seq = await issue_repo.get_next_sequence_id(project_id)

    # Map priority string to enum
    priority_map = {
        "urgent": IssuePriority.URGENT,
        "high": IssuePriority.HIGH,
        "medium": IssuePriority.MEDIUM,
        "low": IssuePriority.LOW,
        "none": IssuePriority.NONE,
    }
    priority = priority_map.get(issue_data.priority.lower(), IssuePriority.NONE)

    # Create issue
    issue = Issue(
        workspace_id=workspace.id,
        project_id=project_id,
        name=issue_data.title,
        description=issue_data.description,
        priority=priority,
        state_id=state.id,
        sequence_id=next_seq,
        reporter_id=current_user_id,
        assignee_id=issue_data.assignee_id,
        estimate_points=issue_data.estimated_hours,
    )
    issue = await issue_repo.create(issue)
    await session.commit()

    # Reload with relations for response
    await session.refresh(issue, ["project", "state"])

    logger.info(
        "Issue created",
        extra={"issue_id": str(issue.id), "workspace_id": str(workspace.id)},
    )

    return _issue_to_response(issue)


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
    session: DbSession,
    issue_repo: IssueRepo,
    workspace_repo: WorkspaceRepo,
) -> IssueResponse:
    """Update an existing issue."""
    workspace = await _resolve_workspace(workspace_id, workspace_repo)

    issue = await issue_repo.get_by_id_with_relations(issue_id)
    if not issue or issue.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )

    # Update fields from request (exclude_unset respects only fields sent)
    update_data = issue_data.model_dump(exclude_unset=True)

    if "name" in update_data:
        issue.name = update_data["name"]
    if "description" in update_data:
        issue.description = update_data["description"]
    if "description_html" in update_data:
        issue.description_html = update_data["description_html"]
    if "priority" in update_data:
        priority_map = {
            "urgent": IssuePriority.URGENT,
            "high": IssuePriority.HIGH,
            "medium": IssuePriority.MEDIUM,
            "low": IssuePriority.LOW,
            "none": IssuePriority.NONE,
        }
        issue.priority = priority_map.get(update_data["priority"].lower(), IssuePriority.NONE)
    if "state_id" in update_data:
        issue.state_id = update_data["state_id"]
    if "sort_order" in update_data:
        issue.sort_order = update_data["sort_order"]

    # Assignee: handle clear flag or update
    if update_data.get("clear_assignee"):
        issue.assignee_id = None
    elif "assignee_id" in update_data:
        issue.assignee_id = update_data["assignee_id"]

    # Cycle: handle clear flag or update
    if update_data.get("clear_cycle"):
        issue.cycle_id = None
    elif "cycle_id" in update_data:
        issue.cycle_id = update_data["cycle_id"]

    # Estimate: handle clear flag or update
    if update_data.get("clear_estimate"):
        issue.estimate_points = None
    elif "estimate_points" in update_data:
        issue.estimate_points = update_data["estimate_points"]

    # Start date: handle clear flag or update
    if update_data.get("clear_start_date"):
        issue.start_date = None
    elif start_date_val := update_data.get("start_date"):
        from datetime import date as date_type

        issue.start_date = date_type.fromisoformat(start_date_val)

    # Target date: handle clear flag or update
    if update_data.get("clear_target_date"):
        issue.target_date = None
    elif target_date_val := update_data.get("target_date"):
        from datetime import date as date_type

        issue.target_date = date_type.fromisoformat(target_date_val)

    # Labels: replace all labels for this issue
    if "label_ids" in update_data:
        label_ids = update_data["label_ids"]
        await issue_repo.bulk_update_labels(issue.id, label_ids)

    issue = await issue_repo.update(issue)
    await session.commit()

    # Reload with all relations for response
    issue = await issue_repo.get_by_id_with_relations(issue_id)

    logger.info(
        "Issue updated",
        extra={"issue_id": str(issue_id), "workspace_id": str(workspace.id)},
    )

    return IssueResponse.from_issue(issue)


@router.patch(
    "/{workspace_id}/issues/{issue_id}/state",
    response_model=WorkspaceIssueResponse,
    tags=["workspace-issues"],
    summary="Update issue state",
)
async def update_workspace_issue_state(
    workspace_id: WorkspaceIdOrSlug,
    issue_id: IssueIdPath,
    body: StateUpdateRequest,
    current_user_id: SyncedUserId,
    session: DbSession,
    issue_repo: IssueRepo,
    workspace_repo: WorkspaceRepo,
) -> WorkspaceIssueResponse:
    """Update issue state (for Kanban drag/drop)."""
    workspace = await _resolve_workspace(workspace_id, workspace_repo)

    issue = await issue_repo.get_by_id(issue_id)
    if not issue or issue.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )

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
        select(State).where(
            State.workspace_id == workspace.id,
            State.name == normalized_state,
            State.is_deleted.is_(False),
        )
    )
    new_state = state_result.scalar_one_or_none()
    if not new_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"State '{state_name}' not found",
        )

    # Update state
    issue.state_id = new_state.id

    issue = await issue_repo.update(issue)
    await session.commit()

    # Reload with relations for response
    await session.refresh(issue, ["project", "state"])

    return _issue_to_response(issue)


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
    session: DbSession,
    issue_repo: IssueRepo,
    workspace_repo: WorkspaceRepo,
) -> DeleteResponse:
    """Soft delete an issue."""
    workspace = await _resolve_workspace(workspace_id, workspace_repo)

    issue = await issue_repo.get_by_id(issue_id)
    if not issue or issue.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )

    # Soft delete
    await issue_repo.delete(issue)
    await session.commit()

    logger.info(
        "Issue deleted",
        extra={"issue_id": str(issue_id), "workspace_id": str(workspace.id)},
    )

    return DeleteResponse(id=issue_id, message="Issue deleted successfully")


__all__ = ["router"]
