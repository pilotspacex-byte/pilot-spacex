"""Workspace invitation router for Pilot Space API.

Provides endpoints for invitation management (invite, list, cancel).
Extracted from workspaces.py to keep files under 700 lines.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, status

from pilot_space.api.v1.dependencies import (
    WorkspaceInvitationServiceDep,
    WorkspaceServiceDep,
)
from pilot_space.api.v1.schemas.workspace import (
    InvitationCreateRequest,
    InvitationResponse,
    WorkspaceMemberResponse,
)
from pilot_space.application.services.workspace_invitation import (
    CancelInvitationPayload,
    ListInvitationsPayload,
)
from pilot_space.dependencies.auth import CurrentUser, SessionDep
from pilot_space.domain.exceptions import AppError
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/workspaces", tags=["workspaces", "invitations"])


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
    session: SessionDep,
    current_user: CurrentUser,
    workspace_service: WorkspaceServiceDep,
) -> WorkspaceMemberResponse | InvitationResponse:
    """Invite or add a member to workspace.

    If the email belongs to an existing user, adds them immediately.
    If not, creates a pending invitation for auto-accept on signup.
    Requires admin or owner role.

    Source: FR-014, FR-015, FR-016, US3.

    Note: Authorization check is now in service layer.
    """
    result = await workspace_service.invite_member(
        workspace_id=workspace_id,
        email=request.email,
        role=request.role,
        invited_by=current_user.user_id,
    )

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
        raise AppError("Unexpected error creating invitation")
    return InvitationResponse(
        id=invitation.id,
        email=invitation.email,
        role=invitation.role.value,
        status=invitation.status.value,
        invited_by=invitation.invited_by,
        suggested_sdlc_role=invitation.suggested_sdlc_role,
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
    session: SessionDep,
    current_user: CurrentUser,
    service: WorkspaceInvitationServiceDep,
) -> list[InvitationResponse]:
    """List invitations for a workspace.

    Requires admin or owner role.
    Source: plan.md API Contract Endpoint 2.
    """
    result = await service.list_invitations(
        ListInvitationsPayload(
            workspace_id=workspace_id,
            requesting_user_id=current_user.user_id,
        )
    )

    return [
        InvitationResponse(
            id=inv.id,
            email=inv.email,
            role=inv.role.value,
            status=inv.status.value,
            invited_by=inv.invited_by,
            suggested_sdlc_role=inv.suggested_sdlc_role,
            expires_at=inv.expires_at,
            created_at=inv.created_at,
        )
        for inv in result.invitations
    ]


@router.delete(
    "/{workspace_id}/invitations/{invitation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["workspaces", "invitations"],
)
async def cancel_workspace_invitation(
    workspace_id: UUID,
    invitation_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
    service: WorkspaceInvitationServiceDep,
) -> None:
    """Cancel a pending invitation.

    Requires admin or owner role.
    Source: plan.md API Contract Endpoint 3, US3 acceptance scenario 5.
    """
    await service.cancel_invitation(
        CancelInvitationPayload(
            workspace_id=workspace_id,
            invitation_id=invitation_id,
            actor_id=current_user.user_id,
        )
    )


__all__ = ["router"]
