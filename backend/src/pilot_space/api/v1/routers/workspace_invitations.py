"""Workspace invitation router for Pilot Space API.

Provides endpoints for invitation management (invite, list, cancel).
Extracted from workspaces.py to keep files under 700 lines.
"""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from pilot_space.api.v1.schemas.workspace import (
    InvitationCreateRequest,
    InvitationResponse,
    WorkspaceMemberResponse,
)
from pilot_space.application.services.workspace import WorkspaceService
from pilot_space.dependencies import CurrentUser, DbSession
from pilot_space.infrastructure.database.repositories.invitation_repository import (
    InvitationRepository,
)
from pilot_space.infrastructure.database.repositories.user_repository import (
    UserRepository,
)
from pilot_space.infrastructure.database.repositories.workspace_repository import (
    WorkspaceRepository,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspaces", tags=["workspaces", "invitations"])


def get_workspace_repository(session: DbSession) -> WorkspaceRepository:
    """Get workspace repository with session."""
    return WorkspaceRepository(session=session)


WorkspaceRepo = Annotated[WorkspaceRepository, Depends(get_workspace_repository)]


def get_user_repository(session: DbSession) -> UserRepository:
    """Get user repository with session."""
    return UserRepository(session=session)


UserRepo = Annotated[UserRepository, Depends(get_user_repository)]


def get_invitation_repository(session: DbSession) -> InvitationRepository:
    """Get invitation repository with session."""
    return InvitationRepository(session=session)


InvitationRepo = Annotated[InvitationRepository, Depends(get_invitation_repository)]


@router.post(
    "/{workspace_id}/members",
    # H-7 fix: add response_model for proper OpenAPI docs and response validation
    response_model=WorkspaceMemberResponse | InvitationResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["workspaces", "invitations"],
)
async def add_workspace_member(
    workspace_id: UUID,
    request: InvitationCreateRequest,
    current_user: CurrentUser,
    workspace_repo: WorkspaceRepo,
    user_repo: UserRepo,
    invitation_repo: InvitationRepo,
) -> WorkspaceMemberResponse | InvitationResponse:
    """Invite or add a member to workspace.

    If the email belongs to an existing user, adds them immediately.
    If not, creates a pending invitation for auto-accept on signup.
    Requires admin or owner role.

    Source: FR-014, FR-015, FR-016, US3.
    """
    # H-3 fix: use get_with_members to eagerly load members (avoids MissingGreenlet)
    workspace = await workspace_repo.get_with_members(workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    # Check admin/owner role
    current_member = next(
        (m for m in (workspace.members or []) if m.user_id == current_user.user_id),
        None,
    )
    if not current_member or not current_member.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )

    service = WorkspaceService(workspace_repo, user_repo, invitation_repo)

    try:
        result = await service.invite_member(
            workspace_id=workspace_id,
            email=request.email,
            role=request.role,
            invited_by=current_user.user_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e

    if result.is_immediate and result.member:
        member = result.member
        return WorkspaceMemberResponse(
            user_id=member.user_id,
            email=member.user.email if member.user else "",
            full_name=member.user.full_name if member.user else None,
            avatar_url=member.user.avatar_url if member.user else None,
            role=member.role.value,
            joined_at=member.created_at,
        )

    invitation = result.invitation
    if invitation is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error creating invitation",
        )
    return InvitationResponse(
        id=invitation.id,
        email=invitation.email,
        role=invitation.role.value,
        status=invitation.status.value,
        invited_by=invitation.invited_by,
        expires_at=invitation.expires_at,
        created_at=invitation.created_at,
    )


@router.get(
    "/{workspace_id}/invitations",
    response_model=list[InvitationResponse],
    tags=["workspaces", "invitations"],
)
async def list_workspace_invitations(
    workspace_id: UUID,
    current_user: CurrentUser,
    workspace_repo: WorkspaceRepo,
    invitation_repo: InvitationRepo,
) -> list[InvitationResponse]:
    """List invitations for a workspace.

    Requires admin or owner role.
    Source: plan.md API Contract Endpoint 2.
    """
    # H-3 fix: use get_with_members to eagerly load members (avoids MissingGreenlet)
    workspace = await workspace_repo.get_with_members(workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    current_member = next(
        (m for m in (workspace.members or []) if m.user_id == current_user.user_id),
        None,
    )
    if not current_member or not current_member.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )

    invitations = await invitation_repo.get_by_workspace(workspace_id)
    return [
        InvitationResponse(
            id=inv.id,
            email=inv.email,
            role=inv.role.value,
            status=inv.status.value,
            invited_by=inv.invited_by,
            expires_at=inv.expires_at,
            created_at=inv.created_at,
        )
        for inv in invitations
    ]


@router.delete(
    "/{workspace_id}/invitations/{invitation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["workspaces", "invitations"],
)
async def cancel_workspace_invitation(
    workspace_id: UUID,
    invitation_id: UUID,
    current_user: CurrentUser,
    workspace_repo: WorkspaceRepo,
    invitation_repo: InvitationRepo,
) -> None:
    """Cancel a pending invitation.

    Requires admin or owner role.
    Source: plan.md API Contract Endpoint 3, US3 acceptance scenario 5.
    """
    # H-3 fix: use get_with_members to eagerly load members (avoids MissingGreenlet)
    workspace = await workspace_repo.get_with_members(workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    current_member = next(
        (m for m in (workspace.members or []) if m.user_id == current_user.user_id),
        None,
    )
    if not current_member or not current_member.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )

    result = await invitation_repo.cancel(invitation_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found or already processed",
        )

    # H-5 fix: verify invitation belongs to this workspace (cross-workspace security)
    if result.workspace_id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found or already processed",
        )


__all__ = ["router"]
