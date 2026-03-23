"""Project router for Pilot Space API.

Provides endpoints for project CRUD operations.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from pilot_space.api.v1.dependencies import (
    ProjectRepositoryDep,
    WorkspaceRepositoryDep,
)
from pilot_space.api.v1.schemas.base import DeleteResponse, PaginatedResponse
from pilot_space.api.v1.schemas.project import (
    LeadBriefResponse,
    ProjectCreate,
    ProjectDetailResponse,
    ProjectResponse,
    ProjectUpdate,
    StateResponse,
)
from pilot_space.dependencies.auth import CurrentUser, SessionDep
from pilot_space.infrastructure.database.models.project import Project
from pilot_space.infrastructure.logging import get_logger
from pilot_space.infrastructure.queue.models import QueueName

logger = get_logger(__name__)

router = APIRouter(prefix="/projects", tags=["projects"])


async def _enqueue_kg_populate(project: Project) -> None:
    """Enqueue a KG populate job for a project (non-fatal)."""
    try:
        from pilot_space.container import get_container

        queue = get_container().queue_client()
        if queue is None:
            return

        await queue.enqueue(
            QueueName.AI_NORMAL,
            {
                "task_type": "kg_populate",
                "entity_type": "project",
                "entity_id": str(project.id),
                "workspace_id": str(project.workspace_id),
                "project_id": str(project.id),
            },
        )
    except Exception as exc:
        logger.warning("projects router: failed to enqueue kg_populate: %s", exc)


async def _project_to_response(
    project: Project,
    project_repo: ProjectRepositoryDep,
) -> ProjectDetailResponse:
    """Convert project model to response with real issue counts."""
    states = [
        StateResponse(
            id=state.id,
            name=state.name,
            group=state.group.value,
            color=state.color,
            sequence=state.sequence,
        )
        for state in sorted(project.states or [], key=lambda s: s.sequence)
    ]

    total_count, open_count = await project_repo.get_issue_counts(project.id)

    lead = None
    if project.lead:
        lead = LeadBriefResponse(
            id=project.lead.id,
            email=project.lead.email,
            display_name=project.lead.full_name,
        )

    return ProjectDetailResponse(
        id=project.id,
        created_at=project.created_at,
        updated_at=project.updated_at,
        name=project.name,
        identifier=project.identifier,
        description=project.description,
        workspace_id=project.workspace_id,
        lead_id=project.lead_id,
        lead=lead,
        icon=project.icon,
        issue_count=total_count,
        open_issue_count=open_count,
        settings=project.settings,
        states=states,
    )


async def _check_workspace_access(
    workspace_repo: WorkspaceRepositoryDep,
    workspace_id: UUID,
    user_id: UUID,
    require_admin: bool = False,
) -> None:
    """Check user has access to workspace.

    Args:
        workspace_repo: Workspace repository.
        workspace_id: Workspace identifier.
        user_id: User identifier.
        require_admin: Whether admin role is required.

    Raises:
        HTTPException: If workspace not found or access denied.
    """
    workspace = await workspace_repo.get_by_id(workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    member = next(
        (m for m in (workspace.members or []) if m.user_id == user_id),
        None,
    )
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )

    if require_admin and not member.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )


@router.get("", response_model=PaginatedResponse[ProjectResponse], tags=["projects"])
async def list_projects(
    workspace_id: Annotated[UUID, Query(description="Filter by workspace")],
    session: SessionDep,
    current_user: CurrentUser,
    project_repo: ProjectRepositoryDep,
    workspace_repo: WorkspaceRepositoryDep,
    cursor: Annotated[str | None, Query(description="Pagination cursor")] = None,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
) -> PaginatedResponse[ProjectResponse]:
    """List projects in a workspace.

    Args:
        workspace_id: Workspace to filter by.
        current_user: Authenticated user.
        project_repo: Project repository.
        workspace_repo: Workspace repository.
        cursor: Pagination cursor.
        page_size: Number of items per page.

    Returns:
        Paginated list of projects.
    """
    await _check_workspace_access(workspace_repo, workspace_id, current_user.user_id)

    page = await project_repo.paginate(
        cursor=cursor,
        page_size=page_size,
        filters={"workspace_id": workspace_id},
    )

    project_ids = [proj.id for proj in page.items]
    batch_counts = await project_repo.get_batch_issue_counts(project_ids)

    # NOTE: proj.lead access below relies on Project.lead having lazy="joined"
    # in the SQLAlchemy model. If changed to lazy="select", this becomes N+1.

    items = [
        ProjectResponse(
            id=proj.id,
            created_at=proj.created_at,
            updated_at=proj.updated_at,
            name=proj.name,
            identifier=proj.identifier,
            description=proj.description,
            workspace_id=proj.workspace_id,
            lead_id=proj.lead_id,
            lead=LeadBriefResponse(
                id=proj.lead.id,
                email=proj.lead.email,
                display_name=proj.lead.full_name,
            )
            if proj.lead
            else None,
            icon=proj.icon,
            issue_count=batch_counts.get(proj.id, (0, 0))[0],
            open_issue_count=batch_counts.get(proj.id, (0, 0))[1],
        )
        for proj in page.items
    ]

    return PaginatedResponse(
        items=items,
        total=page.total,
        next_cursor=page.next_cursor,
        prev_cursor=page.prev_cursor,
        has_next=page.has_next,
        has_prev=page.has_prev,
        page_size=page.page_size,
    )


@router.post(
    "",
    response_model=ProjectDetailResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["projects"],
)
async def create_project(
    request: ProjectCreate,
    session: SessionDep,
    current_user: CurrentUser,
    project_repo: ProjectRepositoryDep,
    workspace_repo: WorkspaceRepositoryDep,
) -> ProjectDetailResponse:
    """Create a new project with default workflow states.

    Requires admin role in the workspace.

    Args:
        request: Project creation data.
        current_user: Authenticated user.
        project_repo: Project repository.
        workspace_repo: Workspace repository.

    Returns:
        Created project.

    Raises:
        HTTPException: If identifier exists or access denied.
    """
    await _check_workspace_access(
        workspace_repo, request.workspace_id, current_user.user_id, require_admin=True
    )

    # Validate lead is a workspace member
    if request.lead_id is not None:
        workspace = await workspace_repo.get_by_id(request.workspace_id)
        is_member = (
            any(m.user_id == request.lead_id for m in (workspace.members or []))
            if workspace
            else False
        )
        if not is_member:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="lead_id must belong to a workspace member",
            )

    # Check identifier uniqueness within workspace
    existing = await project_repo.find_by(
        workspace_id=request.workspace_id,
        identifier=request.identifier,
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Project with identifier '{request.identifier}' already exists",
        )

    # Create project entity and add default states
    project_entity = Project(
        name=request.name,
        identifier=request.identifier,
        description=request.description,
        workspace_id=request.workspace_id,
        lead_id=request.lead_id,
        icon=request.icon,
    )
    project = await project_repo.create_with_default_states(project_entity)

    logger.info(
        "Project created",
        extra={
            "project_id": str(project.id),
            "identifier": project.identifier,
            "workspace_id": str(project.workspace_id),
        },
    )

    await _enqueue_kg_populate(project)

    return await _project_to_response(project, project_repo)


@router.get("/{project_id}", response_model=ProjectDetailResponse, tags=["projects"])
async def get_project(
    project_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
    project_repo: ProjectRepositoryDep,
    workspace_repo: WorkspaceRepositoryDep,
) -> ProjectDetailResponse:
    """Get project by ID.

    Args:
        project_id: Project identifier.
        current_user: Authenticated user.
        project_repo: Project repository.
        workspace_repo: Workspace repository.

    Returns:
        Project details.

    Raises:
        HTTPException: If project not found or access denied.
    """
    project = await project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    await _check_workspace_access(workspace_repo, project.workspace_id, current_user.user_id)

    return await _project_to_response(project, project_repo)


@router.patch("/{project_id}", response_model=ProjectDetailResponse, tags=["projects"])
async def update_project(
    project_id: UUID,
    request: ProjectUpdate,
    session: SessionDep,
    current_user: CurrentUser,
    project_repo: ProjectRepositoryDep,
    workspace_repo: WorkspaceRepositoryDep,
) -> ProjectDetailResponse:
    """Update project.

    Requires admin role.

    Args:
        project_id: Project identifier.
        request: Update data.
        current_user: Authenticated user.
        project_repo: Project repository.
        workspace_repo: Workspace repository.

    Returns:
        Updated project.

    Raises:
        HTTPException: If project not found or access denied.
    """
    project = await project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    await _check_workspace_access(
        workspace_repo, project.workspace_id, current_user.user_id, require_admin=True
    )

    # Validate lead is a workspace member
    if request.lead_id is not None:
        workspace = await workspace_repo.get_by_id(project.workspace_id)
        is_member = (
            any(m.user_id == request.lead_id for m in (workspace.members or []))
            if workspace
            else False
        )
        if not is_member:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="lead_id must belong to a workspace member",
            )

    # Update project
    update_data = request.model_dump(exclude_unset=True)
    if update_data:
        for key, value in update_data.items():
            setattr(project, key, value)
        project = await project_repo.update(project)

        # Enqueue KG populate on content-relevant changes
        kg_relevant_fields = {"name", "description"}
        if kg_relevant_fields & set(update_data.keys()):
            await _enqueue_kg_populate(project)

    logger.info("Project updated", extra={"project_id": str(project_id)})

    return await _project_to_response(project, project_repo)


@router.delete("/{project_id}", response_model=DeleteResponse, tags=["projects"])
async def delete_project(
    project_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
    project_repo: ProjectRepositoryDep,
    workspace_repo: WorkspaceRepositoryDep,
) -> DeleteResponse:
    """Soft delete project.

    Requires admin role.

    Args:
        project_id: Project identifier.
        current_user: Authenticated user.
        project_repo: Project repository.
        workspace_repo: Workspace repository.

    Returns:
        Delete confirmation.

    Raises:
        HTTPException: If project not found or access denied.
    """
    project = await project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    await _check_workspace_access(
        workspace_repo, project.workspace_id, current_user.user_id, require_admin=True
    )

    await project_repo.delete(project)

    logger.info("Project deleted", extra={"project_id": str(project_id)})

    return DeleteResponse(id=project_id, message="Project deleted successfully")


__all__ = ["router"]
