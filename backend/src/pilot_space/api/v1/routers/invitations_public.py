"""Public invitation endpoints (no authentication required).

Provides unauthenticated endpoints for the /invite page to:
1. Preview invitation details (workspace name, status, masked email)
2. Request a Supabase magic link for a pending invitation

These endpoints are intentionally unauthenticated — they are called
from the pre-login invitation acceptance page by users who may not
have an account yet.

Source: FR-012, FR-013, contracts/api.yaml
"""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, status

from pilot_space.api.v1.dependencies import InviteRateLimiterDep
from pilot_space.api.v1.schemas.workspace import (
    InvitationPreviewResponse,
    RequestMagicLinkRequest,
    RequestMagicLinkResponse,
)
from pilot_space.dependencies.auth import SessionDep
from pilot_space.domain.exceptions import AppError, NotFoundError
from pilot_space.infrastructure.database.models.workspace_invitation import (
    InvitationStatus,
)
from pilot_space.infrastructure.database.repositories.invitation_repository import (
    InvitationRepository,
)
from pilot_space.infrastructure.database.repositories.workspace_repository import (
    WorkspaceRepository,
)
from pilot_space.infrastructure.logging import get_logger

router = APIRouter(prefix="/invitations", tags=["invitations"])

logger = get_logger(__name__)


class InvitationNotActionableError(AppError):
    """Raised when an invitation cannot be used (410 Gone)."""

    error_code = "invitation_not_actionable"
    http_status = 410


# Statuses that make an invitation no longer actionable
_TERMINAL_STATUSES = {
    InvitationStatus.ACCEPTED,
    InvitationStatus.EXPIRED,
    InvitationStatus.CANCELLED,
}
# REVOKED was added in migration 104 — use contextlib.suppress for forward compat
with contextlib.suppress(AttributeError):
    _TERMINAL_STATUSES.add(InvitationStatus.REVOKED)  # type: ignore[attr-defined]


def _mask_email(email: str) -> str:
    """Mask the local part of an email address.

    Keeps the first character visible: j***@example.com
    """
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    if len(local) <= 1:
        return f"{local}***@{domain}"
    return f"{local[0]}***@{domain}"


@router.get(
    "/{invitation_id}/preview",
    response_model=InvitationPreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Preview invitation details (public)",
    description=(
        "Returns workspace name and masked invited email for display on the "
        "/invite page. No authentication required. Returns 404 if the "
        "invitation does not exist, 410 if it is no longer actionable."
    ),
)
async def preview_invitation(
    invitation_id: UUID,
    session: SessionDep,
) -> InvitationPreviewResponse:
    """Return public preview of an invitation.

    Source: contracts/api.yaml GET /invitations/{invitation_id}/preview
    """
    invitation_repo = InvitationRepository(session=session)
    invitation = await invitation_repo.get_by_id(invitation_id)

    if invitation is None:
        raise NotFoundError("Invitation not found")

    # Treat time-expired PENDING invitations as expired
    is_time_expired = (
        invitation.status == InvitationStatus.PENDING
        and datetime.now(tz=UTC) > invitation.expires_at
    )

    if invitation.status in _TERMINAL_STATUSES or is_time_expired:
        effective_status = InvitationStatus.EXPIRED if is_time_expired else invitation.status
        raise InvitationNotActionableError(
            f"Invitation is {effective_status.value} and can no longer be used",
            details={"invitation_status": effective_status.value},
        )

    return InvitationPreviewResponse(
        invitation_id=invitation.id,
        status=invitation.status.value,
        workspace_name=invitation.workspace.name,
        workspace_slug=invitation.workspace.slug,
        invited_email_masked=_mask_email(invitation.email),
        expires_at=invitation.expires_at,
    )


@router.post(
    "/{invitation_id}/request-magic-link",
    response_model=RequestMagicLinkResponse,
    status_code=status.HTTP_200_OK,
    summary="Request magic link for invitation (public)",
    description=(
        "Sends a Supabase magic link email to the invited email address. "
        "Rate limited to 3 requests per hour per email. "
        "No authentication required."
    ),
)
async def request_magic_link(
    invitation_id: UUID,
    request: RequestMagicLinkRequest,
    session: SessionDep,
    rate_limiter: InviteRateLimiterDep,
) -> RequestMagicLinkResponse:
    """Send a magic link to the invited email.

    Source: contracts/api.yaml POST /invitations/{invitation_id}/request-magic-link
    """
    from pilot_space.application.services.workspace_invitation import (
        RequestMagicLinkPayload,
        WorkspaceInvitationService,
    )
    from pilot_space.infrastructure.database.repositories.user_repository import (
        UserRepository,
    )

    invitation_repo = InvitationRepository(session=session)
    workspace_repo = WorkspaceRepository(session=session)
    user_repo = UserRepository(session=session)

    svc = WorkspaceInvitationService(
        workspace_repo=workspace_repo,
        invitation_repo=invitation_repo,
        user_repo=user_repo,
        rate_limiter=rate_limiter,
    )

    await svc.request_magic_link(
        RequestMagicLinkPayload(
            invitation_id=invitation_id,
            email=str(request.email),
        )
    )

    return RequestMagicLinkResponse(
        message="Check your email for the magic link. It will expire in 60 minutes.",
        expires_in_minutes=60,
    )


__all__ = ["router"]
