"""Custom RBAC role management router — AUTH-05.

Endpoints for workspace admins to manage custom roles.
All routes require workspace ADMIN or OWNER role.

Endpoints:
  GET    /workspaces/{workspace_slug}/roles                        — list all custom roles
  POST   /workspaces/{workspace_slug}/roles                        — create custom role
  GET    /workspaces/{workspace_slug}/roles/{role_id}              — get single role
  PATCH  /workspaces/{workspace_slug}/roles/{role_id}              — update role (partial)
  DELETE /workspaces/{workspace_slug}/roles/{role_id}              — delete role
  PUT    /workspaces/{workspace_slug}/roles/members/{user_id}/role — assign/clear custom role
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, status

from pilot_space.api.v1.dependencies import RbacServiceDep, WorkspaceRepositoryDep
from pilot_space.api.v1.schemas.rbac import (
    AssignRoleRequest,
    CustomRoleCreate,
    CustomRoleResponse,
    CustomRoleUpdate,
)
from pilot_space.dependencies import SyncedUserId
from pilot_space.dependencies.auth import SessionDep, WorkspaceAdminId
from pilot_space.domain.exceptions import NotFoundError
from pilot_space.infrastructure.database.rls import set_rls_context
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["rbac"])

WorkspaceSlugPath = Annotated[str, Path(description="Workspace slug or UUID")]
RoleIdPath = Annotated[UUID, Path(description="Custom role UUID")]
UserIdPath = Annotated[UUID, Path(description="Member user UUID")]


# ---------------------------------------------------------------------------
# Workspace resolver helper
# ---------------------------------------------------------------------------


async def _resolve_workspace_id(
    workspace_slug: str,
    workspace_repo: WorkspaceRepositoryDep,
) -> UUID:
    """Resolve workspace slug (or UUID) to workspace.id.

    Args:
        workspace_slug: URL path parameter (slug or UUID string).
        workspace_repo: WorkspaceRepository from DI.

    Returns:
        Workspace UUID.

    Raises:
        HTTPException: 404 if workspace not found.
    """
    try:
        as_uuid = UUID(workspace_slug)
        workspace = await workspace_repo.get_by_id_scalar(as_uuid)
    except ValueError:
        workspace = await workspace_repo.get_by_slug_scalar(workspace_slug)

    if workspace is None:
        raise NotFoundError("Workspace not found")
    return workspace.id


# ---------------------------------------------------------------------------
# GET /workspaces/{workspace_slug}/roles
# ---------------------------------------------------------------------------


@router.get(
    "/workspaces/{workspace_slug}/roles",
    response_model=list[CustomRoleResponse],
    summary="List custom roles for a workspace",
)
async def list_custom_roles(
    workspace_slug: WorkspaceSlugPath,
    session: SessionDep,
    current_user_id: SyncedUserId,
    workspace_repo: WorkspaceRepositoryDep,
    rbac_service: RbacServiceDep,
    _admin: WorkspaceAdminId,
) -> list[CustomRoleResponse]:
    """List all custom roles defined in the workspace.

    Requires workspace ADMIN or OWNER role.
    """
    workspace_id = await _resolve_workspace_id(workspace_slug, workspace_repo)
    await set_rls_context(session, current_user_id, workspace_id)

    roles = await rbac_service.list_roles(workspace_id=workspace_id, session=session)
    return [CustomRoleResponse.model_validate(r) for r in roles if not r.is_deleted]


# ---------------------------------------------------------------------------
# POST /workspaces/{workspace_slug}/roles
# ---------------------------------------------------------------------------


@router.post(
    "/workspaces/{workspace_slug}/roles",
    response_model=CustomRoleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a custom role",
)
async def create_custom_role(
    workspace_slug: WorkspaceSlugPath,
    body: CustomRoleCreate,
    session: SessionDep,
    current_user_id: SyncedUserId,
    workspace_repo: WorkspaceRepositoryDep,
    rbac_service: RbacServiceDep,
    _admin: WorkspaceAdminId,
) -> CustomRoleResponse:
    """Create a new custom role in the workspace.

    Returns 409 if role name already exists; 422 if permissions are invalid.
    """
    workspace_id = await _resolve_workspace_id(workspace_slug, workspace_repo)
    await set_rls_context(session, current_user_id, workspace_id)

    role = await rbac_service.create_role(
        workspace_id=workspace_id,
        name=body.name,
        description=body.description,
        permissions=body.permissions,
        session=session,
    )

    await session.commit()
    return CustomRoleResponse.model_validate(role)


# ---------------------------------------------------------------------------
# GET /workspaces/{workspace_slug}/roles/{role_id}
# ---------------------------------------------------------------------------


@router.get(
    "/workspaces/{workspace_slug}/roles/{role_id}",
    response_model=CustomRoleResponse,
    summary="Get a single custom role",
)
async def get_custom_role(
    workspace_slug: WorkspaceSlugPath,
    role_id: RoleIdPath,
    session: SessionDep,
    current_user_id: SyncedUserId,
    workspace_repo: WorkspaceRepositoryDep,
    rbac_service: RbacServiceDep,
    _admin: WorkspaceAdminId,
) -> CustomRoleResponse:
    """Get a single custom role by ID, scoped to the workspace.

    Returns 404 if role not found or belongs to a different workspace.
    """
    workspace_id = await _resolve_workspace_id(workspace_slug, workspace_repo)
    await set_rls_context(session, current_user_id, workspace_id)

    role = await rbac_service.get_role(
        role_id=role_id,
        workspace_id=workspace_id,
        session=session,
    )
    if role is None:
        raise NotFoundError(f"Custom role {role_id} not found")
    return CustomRoleResponse.model_validate(role)


# ---------------------------------------------------------------------------
# PATCH /workspaces/{workspace_slug}/roles/{role_id}
# ---------------------------------------------------------------------------


@router.patch(
    "/workspaces/{workspace_slug}/roles/{role_id}",
    response_model=CustomRoleResponse,
    summary="Update a custom role (partial)",
)
async def update_custom_role(
    workspace_slug: WorkspaceSlugPath,
    role_id: RoleIdPath,
    body: CustomRoleUpdate,
    session: SessionDep,
    current_user_id: SyncedUserId,
    workspace_repo: WorkspaceRepositoryDep,
    rbac_service: RbacServiceDep,
    _admin: WorkspaceAdminId,
) -> CustomRoleResponse:
    """Partially update a custom role.

    Only provided fields are updated. Returns 404 if role not found,
    409 if new name conflicts, 422 if permissions are invalid.
    """
    workspace_id = await _resolve_workspace_id(workspace_slug, workspace_repo)
    await set_rls_context(session, current_user_id, workspace_id)

    role = await rbac_service.update_role(
        role_id=role_id,
        workspace_id=workspace_id,
        name=body.name,
        description=body.description,
        permissions=body.permissions,
        session=session,
    )

    await session.commit()
    return CustomRoleResponse.model_validate(role)


# ---------------------------------------------------------------------------
# DELETE /workspaces/{workspace_slug}/roles/{role_id}
# ---------------------------------------------------------------------------


@router.delete(
    "/workspaces/{workspace_slug}/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a custom role",
)
async def delete_custom_role(
    workspace_slug: WorkspaceSlugPath,
    role_id: RoleIdPath,
    session: SessionDep,
    current_user_id: SyncedUserId,
    workspace_repo: WorkspaceRepositoryDep,
    rbac_service: RbacServiceDep,
    _admin: WorkspaceAdminId,
) -> None:
    """Soft-delete a custom role.

    Member assignments for this role are cleared before deletion.
    Returns 204 No Content on success.
    """
    workspace_id = await _resolve_workspace_id(workspace_slug, workspace_repo)
    await set_rls_context(session, current_user_id, workspace_id)

    await rbac_service.delete_role(
        role_id=role_id,
        workspace_id=workspace_id,
        session=session,
    )

    await session.commit()


# ---------------------------------------------------------------------------
# PUT /workspaces/{workspace_slug}/roles/members/{user_id}/role
# ---------------------------------------------------------------------------


@router.put(
    "/workspaces/{workspace_slug}/roles/members/{user_id}/role",
    response_model=None,
    status_code=status.HTTP_200_OK,
    summary="Assign or clear custom role for a workspace member",
)
async def assign_member_role(
    workspace_slug: WorkspaceSlugPath,
    user_id: UserIdPath,
    body: AssignRoleRequest,
    session: SessionDep,
    current_user_id: SyncedUserId,
    workspace_repo: WorkspaceRepositoryDep,
    rbac_service: RbacServiceDep,
    _admin: WorkspaceAdminId,
) -> dict[str, str]:
    """Assign or clear a custom role for a workspace member.

    Pass custom_role_id=null to revert to built-in WorkspaceRole permissions.
    Returns 404 if user is not a member of the workspace.
    """
    workspace_id = await _resolve_workspace_id(workspace_slug, workspace_repo)
    await set_rls_context(session, current_user_id, workspace_id)

    await rbac_service.assign_role_to_member(
        user_id=user_id,
        workspace_id=workspace_id,
        custom_role_id=body.custom_role_id,
        session=session,
    )

    await session.commit()
    return {"detail": "Role assignment updated"}
