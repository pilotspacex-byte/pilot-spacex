"""My Projects router — US5, US7.

Endpoints for the member dashboard "My Projects" section and
last-active-project management for AI context scoping.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from pilot_space.api.v1.schemas.project_member import MyProjectCard, MyProjectsResponse
from pilot_space.container import Container
from pilot_space.dependencies.auth import CurrentUser, SessionDep
from pilot_space.infrastructure.database.models.workspace_member import WorkspaceRole
from pilot_space.infrastructure.database.repositories.workspace_member_repository import (
    WorkspaceMemberRepository,
)
from pilot_space.infrastructure.database.rls import set_rls_context
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "/{workspace_id}/my-projects",
    response_model=MyProjectsResponse,
    tags=["my-projects"],
)
@inject
async def list_my_projects(
    workspace_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
    wm_repo: WorkspaceMemberRepository = Depends(
        Provide[Container.workspace_member_rbac_repository]
    ),
) -> MyProjectsResponse:
    """Return projects accessible to the current user.

    - Regular Members (MEMBER/GUEST): only non-archived projects where they have
      an active project_member row.
    - Admins and Owners: all non-archived projects in the workspace.

    Projects are ordered by name. Issue counts are not yet implemented
    (returns 0) — wire into separate query when issues endpoint is stable.
    """
    from sqlalchemy import and_, select

    from pilot_space.infrastructure.database.models.project import Project
    from pilot_space.infrastructure.database.models.project_member import ProjectMember

    await set_rls_context(session, current_user.user_id, workspace_id)

    wm = await wm_repo.get_by_user_workspace(current_user.user_id, workspace_id)
    if not wm:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this workspace.",
        )

    is_admin_or_owner = wm.role in (WorkspaceRole.ADMIN, WorkspaceRole.OWNER)

    if is_admin_or_owner:
        # Admins see all non-archived projects
        q = select(Project).where(
            and_(
                Project.workspace_id == workspace_id,
                Project.is_deleted == False,  # noqa: E712
                Project.is_archived == False,  # noqa: E712
            )
        )
        result = await session.execute(q)
        projects = result.scalars().all()

        items = [
            MyProjectCard(
                project_id=p.id,
                name=p.name,
                identifier=p.identifier,
                description=p.description,
                icon=p.icon,
                is_archived=p.is_archived,
                role="admin",
                assigned_at=None,
                last_activity_at=p.updated_at,
                open_issues_count=0,
                total_issues_count=0,
            )
            for p in projects
        ]
    else:
        # Members see only projects they're explicitly assigned to
        q = (
            select(ProjectMember, Project)
            .join(Project, Project.id == ProjectMember.project_id)
            .where(
                and_(
                    ProjectMember.user_id == current_user.user_id,
                    ProjectMember.is_active == True,  # noqa: E712
                    ProjectMember.is_deleted == False,  # noqa: E712
                    Project.workspace_id == workspace_id,
                    Project.is_deleted == False,  # noqa: E712
                    Project.is_archived == False,  # noqa: E712
                )
            )
        )
        result = await session.execute(q)
        rows = result.all()

        items = [
            MyProjectCard(
                project_id=project.id,
                name=project.name,
                identifier=project.identifier,
                description=project.description,
                icon=project.icon,
                is_archived=project.is_archived,
                role="member",
                assigned_at=pm.assigned_at,
                last_activity_at=project.updated_at,
                open_issues_count=0,
                total_issues_count=0,
            )
            for pm, project in rows
        ]

    return MyProjectsResponse(items=items, total=len(items))


class LastActiveProjectRequest(BaseModel):
    """Request body for PATCH .../me/last-active-project."""

    project_id: UUID | None


@router.patch(
    "/{workspace_id}/members/me/last-active-project",
    tags=["my-projects"],
)
@inject
async def update_last_active_project(
    workspace_id: UUID,
    request: LastActiveProjectRequest,
    session: SessionDep,
    current_user: CurrentUser,
    wm_repo: WorkspaceMemberRepository = Depends(
        Provide[Container.workspace_member_rbac_repository]
    ),
) -> dict[str, Any]:
    """Update the current user's last-active project for AI context persistence.

    - Validates user is a member of the workspace.
    - If project_id provided, validates user is an active member of that project
      (or is admin/owner).
    - Rejects archived projects.
    """
    from sqlalchemy import select

    from pilot_space.infrastructure.database.models.project import Project
    from pilot_space.infrastructure.database.models.project_member import ProjectMember

    await set_rls_context(session, current_user.user_id, workspace_id)

    wm = await wm_repo.get_by_user_workspace(current_user.user_id, workspace_id)
    if not wm:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this workspace.",
        )

    if request.project_id is not None:
        # Validate the project exists and is not archived
        proj_result = await session.execute(
            select(Project).where(
                Project.id == request.project_id,
                Project.workspace_id == workspace_id,
                Project.is_deleted == False,  # noqa: E712
            )
        )
        project = proj_result.scalar_one_or_none()
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
        if project.is_archived:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cannot set an archived project as last-active.",
            )

        # Regular members must have explicit project membership
        is_admin_or_owner = wm.role in (WorkspaceRole.ADMIN, WorkspaceRole.OWNER)
        if not is_admin_or_owner:
            pm_result = await session.execute(
                select(ProjectMember).where(
                    ProjectMember.project_id == request.project_id,
                    ProjectMember.user_id == current_user.user_id,
                    ProjectMember.is_active == True,  # noqa: E712
                    ProjectMember.is_deleted == False,  # noqa: E712
                )
            )
            if not pm_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not a member of this project.",
                )

    wm.last_active_project_id = request.project_id
    await session.flush()

    return {
        "user_id": str(current_user.user_id),
        "last_active_project_id": str(request.project_id) if request.project_id else None,
    }
