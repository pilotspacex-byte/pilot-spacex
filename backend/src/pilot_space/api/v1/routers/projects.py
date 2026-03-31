"""Project router for Pilot Space API.

Thin HTTP shell -- business logic delegated to ProjectDetailService.
Provides endpoints for project CRUD operations.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from pilot_space.api.v1.dependencies import (
    ProjectDetailServiceDep,
    ProjectRbacServiceDep,
    ProjectRepositoryDep,
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

logger = get_logger(__name__)

router = APIRouter(prefix="/projects", tags=["projects"])


def _build_detail_response(
    project: Project,
    total_count: int,
    open_count: int,
) -> ProjectDetailResponse:
    """Build ProjectDetailResponse from domain model and counts."""
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


@router.get("", response_model=PaginatedResponse[ProjectResponse], tags=["projects"])
async def list_projects(
    workspace_id: Annotated[UUID, Query(description="Filter by workspace")],
    session: SessionDep,
    current_user: CurrentUser,
    project_repo: ProjectRepositoryDep,
    detail_service: ProjectDetailServiceDep,
    rbac_svc: ProjectRbacServiceDep,
    cursor: Annotated[str | None, Query(description="Pagination cursor")] = None,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
) -> PaginatedResponse[ProjectResponse]:
    """List projects in a workspace."""
    await detail_service.check_workspace_access(workspace_id, current_user.user_id)

    page = await project_repo.paginate(
        cursor=cursor,
        page_size=page_size,
        filters={"workspace_id": workspace_id},
    )

    project_ids = [proj.id for proj in page.items]
    accessible_ids = await rbac_svc.get_accessible_project_ids(
        workspace_id, current_user.user_id, project_ids
    )
    accessible_projects = [proj for proj in page.items if proj.id in accessible_ids]
    batch_counts = await detail_service.get_batch_issue_counts([p.id for p in accessible_projects])

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
        for proj in accessible_projects
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
    detail_service: ProjectDetailServiceDep,
) -> ProjectDetailResponse:
    """Create a new project with default workflow states.

    Requires admin role in the workspace.
    """
    await detail_service.check_workspace_access(
        request.workspace_id, current_user.user_id, require_admin=True
    )

    if request.lead_id is not None:
        await detail_service.validate_lead_membership(request.workspace_id, request.lead_id)

    await detail_service.validate_identifier_unique(request.workspace_id, request.identifier)

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

    await detail_service.enqueue_kg_populate(project)

    total_count, open_count = await detail_service.get_issue_counts(project.id)
    return _build_detail_response(project, total_count, open_count)


@router.get("/{project_id}", response_model=ProjectDetailResponse, tags=["projects"])
async def get_project(
    project_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
    detail_service: ProjectDetailServiceDep,
    rbac_svc: ProjectRbacServiceDep,
) -> ProjectDetailResponse:
    """Get project by ID."""
    project = await detail_service.get_project_or_raise(project_id)
    await detail_service.check_workspace_access(project.workspace_id, current_user.user_id)
    await rbac_svc.check_project_access(project_id, project.workspace_id, current_user.user_id)

    total_count, open_count = await detail_service.get_issue_counts(project.id)
    return _build_detail_response(project, total_count, open_count)


@router.patch("/{project_id}", response_model=ProjectDetailResponse, tags=["projects"])
async def update_project(
    project_id: UUID,
    request: ProjectUpdate,
    session: SessionDep,
    current_user: CurrentUser,
    project_repo: ProjectRepositoryDep,
    detail_service: ProjectDetailServiceDep,
) -> ProjectDetailResponse:
    """Update project. Requires admin role."""
    project = await detail_service.get_project_or_raise(project_id)

    await detail_service.check_workspace_access(
        project.workspace_id, current_user.user_id, require_admin=True
    )

    if request.lead_id is not None:
        await detail_service.validate_lead_membership(project.workspace_id, request.lead_id)

    update_data = request.model_dump(exclude_unset=True)
    if update_data:
        for key, value in update_data.items():
            setattr(project, key, value)
        project = await project_repo.update(project)

        kg_relevant_fields = {"name", "description"}
        if kg_relevant_fields & set(update_data.keys()):
            await detail_service.enqueue_kg_populate(project)

    logger.info("Project updated", extra={"project_id": str(project_id)})

    total_count, open_count = await detail_service.get_issue_counts(project.id)
    return _build_detail_response(project, total_count, open_count)


@router.delete("/{project_id}", response_model=DeleteResponse, tags=["projects"])
async def delete_project(
    project_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
    project_repo: ProjectRepositoryDep,
    detail_service: ProjectDetailServiceDep,
) -> DeleteResponse:
    """Soft delete project. Requires admin role."""
    project = await detail_service.get_project_or_raise(project_id)

    await detail_service.check_workspace_access(
        project.workspace_id, current_user.user_id, require_admin=True
    )

    await project_repo.delete(project)

    logger.info("Project deleted", extra={"project_id": str(project_id)})

    return DeleteResponse(id=project_id, message="Project deleted successfully")


__all__ = ["router"]
