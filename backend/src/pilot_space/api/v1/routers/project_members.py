"""Project members router — US1, US4, US6.

Provides endpoints for project-scoped membership management.

Routes mounted under /workspaces/{workspace_id}/projects/{project_id}/members.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from pilot_space.api.v1.dependencies import ProjectMemberServiceDep
from pilot_space.api.v1.schemas.project_member import (
    AddProjectMemberRequest,
    ArchiveProjectRequest,
    ProjectMemberListResponse,
    ProjectMemberResponse,
    RemoveProjectMemberResponse,
)
from pilot_space.application.services.project_member import (
    AddMemberPayload,
    AlreadyProjectMemberError,
    ListMembersPayload,
    RemoveMemberPayload,
    UnauthorizedError,
)
from pilot_space.dependencies.auth import CurrentUser, SessionDep
from pilot_space.infrastructure.database.rls import set_rls_context
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "/{workspace_id}/projects/{project_id}/members",
    response_model=ProjectMemberListResponse,
    tags=["project-members"],
)
async def list_project_members(
    workspace_id: UUID,
    project_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
    service: ProjectMemberServiceDep,
    search: str | None = Query(default=None, description="Search by name or email"),
    cursor: str | None = Query(default=None, description="Pagination cursor"),
    page_size: int = Query(default=20, ge=1, le=100),
    is_active: bool = Query(default=True, description="Filter by active status"),
) -> ProjectMemberListResponse:
    """List members assigned to a project.

    All workspace members (admin or not) may view the member list.
    """
    await set_rls_context(session, current_user.user_id, workspace_id)

    result = await service.list_members(
        ListMembersPayload(
            project_id=project_id,
            search=search,
            is_active=is_active,
            cursor=cursor,
            page_size=page_size,
        )
    )

    items = [ProjectMemberResponse.model_validate(m) for m in result.members]

    return ProjectMemberListResponse(
        items=items,
        total=result.total,
        next_cursor=result.next_cursor,
        has_next=result.has_next,
    )


@router.post(
    "/{workspace_id}/projects/{project_id}/members",
    response_model=ProjectMemberResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["project-members"],
)
async def add_project_member(
    workspace_id: UUID,
    project_id: UUID,
    request: AddProjectMemberRequest,
    session: SessionDep,
    current_user: CurrentUser,
    service: ProjectMemberServiceDep,
) -> ProjectMemberResponse:
    """Add a workspace member to a project.

    Requires Admin or Owner workspace role.
    """
    await set_rls_context(session, current_user.user_id, workspace_id)

    # Resolve the requesting user's workspace role (from token claims or DB lookup)
    # We pass workspace role via a lazy lookup — the service will enforce admin gate.
    from pilot_space.dependencies.auth import get_current_session
    from pilot_space.infrastructure.database.repositories.workspace_member_repository import (
        WorkspaceMemberRepository,
    )

    ws_member_repo = WorkspaceMemberRepository(session=get_current_session())
    wm = await ws_member_repo.get_by_user_workspace(current_user.user_id, workspace_id)
    if not wm:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this workspace.",
        )

    try:
        member = await service.add_member(
            AddMemberPayload(
                workspace_id=workspace_id,
                project_id=project_id,
                user_id=request.user_id,
                requesting_user_id=current_user.user_id,
                requesting_user_role=wm.role.value,
            )
        )
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except AlreadyProjectMemberError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e

    return ProjectMemberResponse(
        id=member.id,
        project_id=member.project_id,
        user_id=member.user_id,
        email=member.user.email if member.user else "",
        full_name=member.user.full_name if member.user else None,
        avatar_url=member.user.avatar_url if member.user else None,
        assigned_at=member.assigned_at,
        assigned_by=member.assigned_by,
        is_active=member.is_active,
    )


@router.delete(
    "/{workspace_id}/projects/{project_id}/members/{user_id}",
    response_model=RemoveProjectMemberResponse,
    tags=["project-members"],
)
async def remove_project_member(
    workspace_id: UUID,
    project_id: UUID,
    user_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
    service: ProjectMemberServiceDep,
) -> RemoveProjectMemberResponse:
    """Remove a member from a project (deactivate their membership).

    Requires Admin or Owner workspace role.
    """
    await set_rls_context(session, current_user.user_id, workspace_id)

    from pilot_space.dependencies.auth import get_current_session
    from pilot_space.infrastructure.database.repositories.workspace_member_repository import (
        WorkspaceMemberRepository,
    )

    ws_member_repo = WorkspaceMemberRepository(session=get_current_session())
    wm = await ws_member_repo.get_by_user_workspace(current_user.user_id, workspace_id)
    if not wm:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this workspace.",
        )

    try:
        removed = await service.remove_member(
            RemoveMemberPayload(
                workspace_id=workspace_id,
                project_id=project_id,
                user_id=user_id,
                requesting_user_id=current_user.user_id,
                requesting_user_role=wm.role.value,
            )
        )
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e

    return RemoveProjectMemberResponse(removed=removed, user_id=user_id)


@router.patch(
    "/{workspace_id}/projects/{project_id}/archive",
    tags=["project-members"],
)
async def archive_project(
    workspace_id: UUID,
    project_id: UUID,
    request: ArchiveProjectRequest,
    session: SessionDep,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """Archive or unarchive a project.

    Sets is_archived and archived_at. Requires Admin or Owner.
    """
    from datetime import UTC, datetime

    from sqlalchemy import select

    from pilot_space.dependencies.auth import get_current_session
    from pilot_space.infrastructure.database.models.project import Project
    from pilot_space.infrastructure.database.models.workspace_member import WorkspaceRole
    from pilot_space.infrastructure.database.repositories.workspace_member_repository import (
        WorkspaceMemberRepository,
    )

    await set_rls_context(session, current_user.user_id, workspace_id)
    _session = get_current_session()

    ws_member_repo = WorkspaceMemberRepository(session=_session)
    wm = await ws_member_repo.get_by_user_workspace(current_user.user_id, workspace_id)
    if not wm or wm.role not in (WorkspaceRole.ADMIN, WorkspaceRole.OWNER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and owners can archive projects.",
        )

    result = await _session.execute(
        select(Project).where(
            Project.id == project_id,
            Project.workspace_id == workspace_id,
            Project.is_deleted == False,  # noqa: E712
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    project.is_archived = request.is_archived
    project.archived_at = datetime.now(tz=UTC) if request.is_archived else None
    await _session.flush()

    archived_at = project.archived_at
    return {
        "project_id": str(project.id),
        "is_archived": project.is_archived,
        "archived_at": archived_at.isoformat() if archived_at else None,
    }
