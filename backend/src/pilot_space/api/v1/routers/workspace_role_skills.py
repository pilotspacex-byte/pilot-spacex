"""Workspace role skill admin API endpoints (WRSKL-01..02).

Admin-only CRUD + generate endpoints for workspace-level role skills.
- POST /{workspace_id}/workspace-role-skills         -> generate + create (201)
- GET  /{workspace_id}/workspace-role-skills         -> list skills (200)
- POST /{workspace_id}/workspace-role-skills/{id}/activate -> activate (200)
- DELETE /{workspace_id}/workspace-role-skills/{id}  -> soft-delete (204)

All endpoints require ADMIN or OWNER role in the workspace.

Source: Phase 16, WRSKL-01..02
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, status
from sqlalchemy import select

from pilot_space.api.middleware.request_context import WorkspaceId
from pilot_space.api.v1.schemas.workspace_role_skill import (
    GenerateWorkspaceSkillRequest,
    WorkspaceRoleSkillListResponse,
    WorkspaceRoleSkillResponse,
)
from pilot_space.dependencies import CurrentUserId, DbSession
from pilot_space.domain.exceptions import ForbiddenError
from pilot_space.infrastructure.database.models.workspace_member import (
    WorkspaceMember,
    WorkspaceRole,
)
from pilot_space.infrastructure.database.rls import set_rls_context
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/{workspace_id}/workspace-role-skills",
    tags=["Workspace Role Skills"],
)


async def _require_admin(
    user_id: UUID,
    workspace_id: UUID,
    session: DbSession,
) -> None:
    """Verify the requesting user is an ADMIN or OWNER in the workspace.

    Args:
        user_id: Authenticated user UUID.
        workspace_id: Workspace UUID to check.
        session: Database session.

    Raises:
        HTTPException: 403 if user is not a member or lacks ADMIN/OWNER role.
    """
    stmt = select(WorkspaceMember.role).where(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id,
        WorkspaceMember.is_deleted == False,  # noqa: E712
    )
    result = await session.execute(stmt)
    row = result.scalar()

    if row is None:
        raise ForbiddenError("Not a member of this workspace")

    role = row.value if hasattr(row, "value") else str(row).upper()

    if role not in (WorkspaceRole.ADMIN.value, WorkspaceRole.OWNER.value):
        raise ForbiddenError("Admin or owner role required")


@router.post(
    "",
    response_model=WorkspaceRoleSkillResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate and create a workspace role skill",
    description=(
        "AI-generates skill content using the experience description, then persists "
        "the skill as inactive (is_active=False). Admin or owner role required."
    ),
)
async def create_workspace_skill(
    workspace_id: WorkspaceId,
    request: GenerateWorkspaceSkillRequest,
    session: DbSession,
    current_user_id: CurrentUserId,
) -> WorkspaceRoleSkillResponse:
    """Generate + create a workspace role skill.

    Args:
        workspace_id: Workspace UUID from request context.
        request: Role type, name, and experience description for generation.
        session: Database session.
        current_user_id: Authenticated user UUID.

    Returns:
        Created WorkspaceRoleSkillResponse with is_active=False,
        or RFC 7807 problem response on error.
    """
    await set_rls_context(session, current_user_id, workspace_id)
    await _require_admin(current_user_id, workspace_id, session)

    from pilot_space.application.services.workspace_role_skill import (
        CreateWorkspaceSkillPayload,
        CreateWorkspaceSkillService,
    )

    svc = CreateWorkspaceSkillService(session=session)
    skill = await svc.execute(
        CreateWorkspaceSkillPayload(
            workspace_id=workspace_id,
            created_by=current_user_id,
            role_type=request.role_type,
            role_name=request.role_name,
            experience_description=request.experience_description,
        )
    )

    logger.info(
        "[WorkspaceRoleSkills] Created skill workspace=%s role_type=%s user=%s",
        workspace_id,
        request.role_type,
        current_user_id,
    )

    return WorkspaceRoleSkillResponse.model_validate(skill)


@router.get(
    "",
    response_model=WorkspaceRoleSkillListResponse,
    status_code=status.HTTP_200_OK,
    summary="List workspace role skills",
    description="Return all non-deleted workspace role skills. Admin or owner role required.",
)
async def list_workspace_skills(
    workspace_id: WorkspaceId,
    session: DbSession,
    current_user_id: CurrentUserId,
) -> WorkspaceRoleSkillListResponse:
    """List all non-deleted workspace role skills.

    Args:
        workspace_id: Workspace UUID from request context.
        session: Database session.
        current_user_id: Authenticated user UUID.

    Returns:
        WorkspaceRoleSkillListResponse with all non-deleted skills.

    Raises:
        HTTPException: 403 if not admin/owner.
    """
    await set_rls_context(session, current_user_id, workspace_id)
    await _require_admin(current_user_id, workspace_id, session)

    from pilot_space.application.services.workspace_role_skill import (
        ListWorkspaceSkillsPayload,
        ListWorkspaceSkillsService,
    )

    svc = ListWorkspaceSkillsService(session=session)
    skills = await svc.execute(ListWorkspaceSkillsPayload(workspace_id=workspace_id))

    return WorkspaceRoleSkillListResponse(
        skills=[WorkspaceRoleSkillResponse.model_validate(s) for s in skills]
    )


@router.post(
    "/{skill_id}/activate",
    response_model=WorkspaceRoleSkillResponse,
    status_code=status.HTTP_200_OK,
    summary="Activate a workspace role skill",
    description=(
        "Set is_active=True on a workspace role skill, making it available for "
        "materializer injection (WRSKL-02 approval gate). Admin or owner role required."
    ),
)
async def activate_workspace_skill(
    workspace_id: WorkspaceId,
    skill_id: UUID,
    session: DbSession,
    current_user_id: CurrentUserId,
) -> WorkspaceRoleSkillResponse:
    """Activate a workspace role skill.

    Args:
        workspace_id: Workspace UUID from request context.
        skill_id: UUID of the skill to activate.
        session: Database session.
        current_user_id: Authenticated user UUID.

    Returns:
        Updated WorkspaceRoleSkillResponse with is_active=True.

    Raises:
        HTTPException: 403 if not admin/owner; 404 if skill not found; 422 on conflict.
    """
    await set_rls_context(session, current_user_id, workspace_id)
    await _require_admin(current_user_id, workspace_id, session)

    from pilot_space.application.services.workspace_role_skill import (
        ActivateWorkspaceSkillPayload,
        ActivateWorkspaceSkillService,
    )

    svc = ActivateWorkspaceSkillService(session=session)
    skill = await svc.execute(
        ActivateWorkspaceSkillPayload(
            skill_id=skill_id,
            workspace_id=workspace_id,
        )
    )

    logger.info(
        "[WorkspaceRoleSkills] Activated skill=%s workspace=%s user=%s",
        skill_id,
        workspace_id,
        current_user_id,
    )

    return WorkspaceRoleSkillResponse.model_validate(skill)


@router.delete(
    "/{skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a workspace role skill",
    description="Soft-delete a workspace role skill. Admin or owner role required.",
)
async def delete_workspace_skill(
    workspace_id: WorkspaceId,
    skill_id: UUID,
    session: DbSession,
    current_user_id: CurrentUserId,
) -> None:
    """Soft-delete a workspace role skill.

    Args:
        workspace_id: Workspace UUID from request context.
        skill_id: UUID of the skill to delete.
        session: Database session.
        current_user_id: Authenticated user UUID.

    Raises:
        HTTPException: 403 if not admin/owner; 404 if skill not found.
    """
    await set_rls_context(session, current_user_id, workspace_id)
    await _require_admin(current_user_id, workspace_id, session)

    from pilot_space.application.services.workspace_role_skill import (
        DeleteWorkspaceSkillPayload,
        DeleteWorkspaceSkillService,
    )

    svc = DeleteWorkspaceSkillService(session=session)
    await svc.execute(
        DeleteWorkspaceSkillPayload(
            skill_id=skill_id,
            workspace_id=workspace_id,
        )
    )

    logger.info(
        "[WorkspaceRoleSkills] Deleted skill=%s workspace=%s user=%s",
        skill_id,
        workspace_id,
        current_user_id,
    )


__all__ = ["router"]
