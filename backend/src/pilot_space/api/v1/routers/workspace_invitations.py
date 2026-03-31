"""Workspace invitation router for Pilot Space API.

Provides endpoints for invitation management (invite, list, cancel, rescind).
Extracted from workspaces.py to keep files under 700 lines.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Query, status
from sqlalchemy import and_, select

from pilot_space.api.v1.dependencies import (
    WorkspaceInvitationServiceDep,
    WorkspaceServiceDep,
)
from pilot_space.api.v1.schemas.base import PaginatedResponse
from pilot_space.api.v1.schemas.workspace import (
    InvitationAcceptResponse,
    InvitationCreateRequest,
    InvitationPublicDetailResponse,
    InvitationResponse,
    WorkspaceMemberResponse,
)
from pilot_space.application.services.workspace_invitation import (
    AcceptInvitationPayload,
    CancelInvitationPayload,
    ListInvitationsPayload,
)
from pilot_space.config import get_settings
from pilot_space.dependencies.auth import CurrentUser, CurrentUserId, SessionDep
from pilot_space.domain.exceptions import AppError, ValidationError
from pilot_space.infrastructure.database.models.project import Project
from pilot_space.infrastructure.database.repositories.project_member import (
    ProjectMemberRepository,
)
from pilot_space.infrastructure.database.rls import set_rls_context
from pilot_space.infrastructure.logging import get_logger
from pilot_space.infrastructure.supabase_client import get_supabase_client

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
    await set_rls_context(session, current_user.user_id, workspace_id)

    assignments = request.project_assignments or []

    # Validate all project_ids belong to this workspace and are not archived (if provided)
    if assignments:
        project_ids = [UUID(str(a["project_id"])) for a in assignments if "project_id" in a]
        rows = await session.execute(
            select(Project.id, Project.is_archived).where(
                and_(
                    Project.id.in_(project_ids),
                    Project.workspace_id == workspace_id,
                    Project.is_deleted == False,  # noqa: E712
                )
            )
        )
        found = {row.id: row.is_archived for row in rows.all()}
        missing = [pid for pid in project_ids if pid not in found]
        if missing:
            raise ValidationError(f"Projects not found in workspace: {[str(p) for p in missing]}")
        archived = [pid for pid, is_arch in found.items() if is_arch]
        if archived:
            raise ValidationError(
                f"Cannot assign to archived projects: {[str(p) for p in archived]}"
            )

    result = await workspace_service.invite_member(
        workspace_id=workspace_id,
        email=request.email,
        role=request.role,
        invited_by=current_user.user_id,
    )

    if result.is_immediate and result.member:
        member = result.member

        # FR-03: materialize project assignments for immediately added user
        if assignments:
            from pilot_space.application.services.project_member import (
                InviteAssignmentsPayload,
                ProjectMemberService,
            )

            pm_repo = ProjectMemberRepository(session=session)
            pm_svc = ProjectMemberService(project_member_repository=pm_repo)
            await pm_svc.materialize_invite_assignments(
                InviteAssignmentsPayload(
                    workspace_id=workspace_id,
                    user_id=member.user_id,
                    assigned_by=current_user.user_id,
                    project_assignments=assignments,
                )
            )

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

    # Store project_assignments on the invitation object for later materialization
    if assignments:
        invitation.project_assignments = assignments
        await session.flush()

    # Send Supabase magic-link invite for new (never registered) users.
    # Only send once — skip if already sent (retry safety).
    if invitation.supabase_invite_sent_at is None:
        try:
            settings = get_settings()
            supabase_client = await get_supabase_client()
            redirect_url = (
                f"{settings.frontend_url}/invite"
                f"?invitation_id={invitation.id}"
                f"&workspace_id={workspace_id}"
            )
            await supabase_client.auth.admin.invite_user_by_email(
                invitation.email,
                options={
                    "redirect_to": redirect_url,
                    "data": {
                        "workspace_invitation_id": str(invitation.id),
                        "workspace_id": str(workspace_id),
                    },
                },
            )
            invitation.supabase_invite_sent_at = datetime.now(UTC)
            await session.flush()
        except Exception:
            logger.warning(
                "supabase_invite_failed",
                invitation_id=str(invitation.id),
                email=invitation.email,
            )

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
    response_model=PaginatedResponse[InvitationResponse],
    tags=["workspaces", "invitations"],
)
async def list_workspace_invitations(
    workspace_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
    service: WorkspaceInvitationServiceDep,
    page: int = Query(default=1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
) -> PaginatedResponse[InvitationResponse]:
    """List invitations for a workspace.

    Requires admin or owner role.
    Source: plan.md API Contract Endpoint 2.
    """
    result = await service.list_invitations(
        ListInvitationsPayload(
            workspace_id=workspace_id,
            requesting_user_id=current_user.user_id,
            page=page,
            page_size=page_size,
        )
    )

    items = [
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

    return PaginatedResponse(
        items=items,
        total=result.total,
        has_next=result.has_next,
        has_prev=result.has_prev,
        page_size=result.page_size,
    )


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


@router.delete(
    "/{workspace_id}/members/invitations/{invitation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["workspaces", "invitations"],
)
async def rescind_workspace_invitation(
    workspace_id: UUID,
    invitation_id: UUID,
    session: SessionDep,
    current_user_id: CurrentUserId,
    service: WorkspaceInvitationServiceDep,
) -> None:
    """Rescind (cancel) a pending invitation from the Members page.

    Admin/owner only. Sets invitation status to 'REVOKED'.
    Source: T026, US3 FR-03.
    """
    await set_rls_context(session, current_user_id, workspace_id)
    await service.cancel_invitation(
        CancelInvitationPayload(
            workspace_id=workspace_id,
            invitation_id=invitation_id,
            actor_id=current_user_id,
        )
    )


# ===== Public invitation endpoints (no /workspaces prefix) =====

invitation_router = APIRouter(prefix="/invitations", tags=["invitations"])


@invitation_router.get(
    "/{invitation_id}",
    response_model=InvitationPublicDetailResponse,
    tags=["invitations"],
)
async def get_invitation_details(
    invitation_id: UUID,
    session: SessionDep,
    service: WorkspaceInvitationServiceDep,
) -> InvitationPublicDetailResponse:
    """Get public-facing invitation details.

    No authentication required. Returns limited information
    for the accept-invite page to display context.
    """
    result = await service.get_invitation_details(invitation_id)
    return InvitationPublicDetailResponse(
        id=result.id,
        workspace_name=result.workspace_name,
        workspace_slug=result.workspace_slug,
        inviter_name=result.inviter_name,
        role=result.role,
        email_masked=result.email_masked,
        status=result.status,
        expires_at=result.expires_at,
    )


@invitation_router.post(
    "/{invitation_id}/accept",
    response_model=InvitationAcceptResponse,
    tags=["invitations"],
)
async def accept_invitation(
    invitation_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
    service: WorkspaceInvitationServiceDep,
) -> InvitationAcceptResponse:
    """Accept a pending invitation.

    Requires authentication. Verifies the authenticated user's
    email matches the invitation email, adds them to the workspace,
    and marks the invitation as accepted.
    """
    if not current_user.email:
        raise ValidationError("User email is required to accept an invitation")
    result = await service.accept_invitation(
        AcceptInvitationPayload(
            invitation_id=invitation_id,
            user_id=current_user.user_id,
        )
    )
    return InvitationAcceptResponse(
        workspace_slug=result.workspace_slug,
        workspace_name=result.workspace_name,
        role=result.role,
    )


__all__ = ["invitation_router", "router"]
