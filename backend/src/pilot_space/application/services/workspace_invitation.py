"""Workspace invitation management service.

Handles invitation operations following CQRS-lite pattern (DD-064):
- List workspace invitations
- Cancel invitation
- Accept invitation (magic-link flow)

Note: The invite_member operation is in WorkspaceService (maintains
existing API compatibility).

Source: FR-014, FR-015, FR-016, US3.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pilot_space.domain.exceptions import NotFoundError
from pilot_space.infrastructure.database.models.workspace_invitation import (
    InvitationStatus,
)
from pilot_space.infrastructure.database.rls import set_rls_context
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from pilot_space.infrastructure.cache.invite_rate_limiter import InviteRateLimiter
    from pilot_space.infrastructure.database.models.workspace_invitation import (
        WorkspaceInvitation,
    )
    from pilot_space.infrastructure.database.repositories.invitation_repository import (
        InvitationRepository,
    )
    from pilot_space.infrastructure.database.repositories.user_repository import (
        UserRepository,
    )
    from pilot_space.infrastructure.database.repositories.workspace_repository import (
        WorkspaceRepository,
    )

logger = get_logger(__name__)


# ===== Custom Exceptions =====


class WorkspaceInvitationError(Exception):
    """Base for all workspace-invitation domain errors."""

    error_code: str = "workspace_invitation_error"
    http_status: int = 400

    def __init__(
        self,
        message: str,
        *,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if error_code:
            self.error_code = error_code
        self.details = details or {}


class WorkspaceNotFoundError(WorkspaceInvitationError):
    """Raised when the workspace does not exist."""

    error_code = "workspace_not_found"
    http_status = 404


class WorkspaceInvitationNotFoundError(WorkspaceInvitationError):
    """Raised when the invitation is not found."""

    error_code = "workspace_invitation_not_found"
    http_status = 404


class WorkspaceInvitationForbiddenError(WorkspaceInvitationError):
    """Raised when the actor lacks admin role."""

    error_code = "workspace_invitation_forbidden"
    http_status = 403


class WorkspaceInvitationConflictError(WorkspaceInvitationError):
    """Raised when invitation is not in a state that allows the action."""

    error_code = "workspace_invitation_conflict"
    http_status = 409


# ===== Payloads & Results =====


@dataclass
class ListInvitationsPayload:
    """Payload for listing workspace invitations."""

    workspace_id: UUID
    requesting_user_id: UUID
    page: int = 1
    page_size: int = 20


@dataclass
class ListInvitationsResult:
    """Result of list_invitations operation."""

    invitations: list[WorkspaceInvitation]
    total: int = 0
    has_next: bool = False
    has_prev: bool = False
    page_size: int = 20


@dataclass
class CancelInvitationPayload:
    """Payload for canceling invitation."""

    workspace_id: UUID
    invitation_id: UUID
    actor_id: UUID


@dataclass
class CancelInvitationResult:
    """Result of cancel_invitation operation."""

    invitation_id: UUID
    cancelled_at: datetime


@dataclass
class AcceptInvitationPayload:
    """Payload for accepting a workspace invitation via magic link."""

    invitation_id: UUID
    user_id: UUID


@dataclass
class InvitationDetailResult:
    """Public invitation details for the accept-invite page."""

    id: UUID
    workspace_name: str
    workspace_slug: str
    inviter_name: str | None
    role: str
    email_masked: str
    status: str
    expires_at: datetime


@dataclass
class AcceptInvitationResult:
    """Result of accept_invitation operation."""

    workspace_slug: str
    workspace_name: str
    role: str
    requires_profile_completion: bool


@dataclass
class RequestMagicLinkPayload:
    """Payload for requesting a magic link for an invitation."""

    invitation_id: UUID
    email: str


@dataclass
class RequestMagicLinkResult:
    """Result of request_magic_link operation."""

    message: str
    expires_in_minutes: int = 60


class WorkspaceInvitationService:
    """Service for workspace invitation operations.

    Follows CQRS-lite pattern per DD-064.
    """

    def __init__(
        self,
        workspace_repo: WorkspaceRepository,
        invitation_repo: InvitationRepository,
        user_repo: UserRepository | None = None,
        rate_limiter: InviteRateLimiter | None = None,
    ) -> None:
        self.workspace_repo = workspace_repo
        self.invitation_repo = invitation_repo
        self.user_repo = user_repo
        self.rate_limiter = rate_limiter

    async def list_invitations(
        self,
        payload: ListInvitationsPayload,
    ) -> ListInvitationsResult:
        """List invitations for a workspace.

        Requires admin or owner role.

        Args:
            payload: List invitations payload.

        Returns:
            List of invitations.

        Raises:
            ValueError: If workspace not found or user not admin.
        """
        # H-3 fix: use get_with_members to eagerly load members
        workspace = await self.workspace_repo.get_with_members(payload.workspace_id)
        if not workspace:
            msg = "Workspace not found"
            raise WorkspaceNotFoundError(msg)

        # Check admin/owner role
        current_member = next(
            (m for m in (workspace.members or []) if m.user_id == payload.requesting_user_id),
            None,
        )
        if not current_member or not current_member.is_admin:
            msg = "Admin role required"
            raise WorkspaceInvitationForbiddenError(msg)

        invitations = await self.invitation_repo.get_by_workspace(
            payload.workspace_id,
            status_filter=InvitationStatus.PENDING,
        )

        all_invitations = list(invitations)
        total = len(all_invitations)
        offset = (payload.page - 1) * payload.page_size
        page_items = all_invitations[offset : offset + payload.page_size]

        return ListInvitationsResult(
            invitations=page_items,
            total=total,
            has_next=offset + payload.page_size < total,
            has_prev=payload.page > 1,
            page_size=payload.page_size,
        )

    async def cancel_invitation(
        self,
        payload: CancelInvitationPayload,
    ) -> CancelInvitationResult:
        """Cancel a pending invitation.

        Requires admin or owner role.

        Args:
            payload: Cancel invitation payload.

        Returns:
            Cancelled invitation info.

        Raises:
            ValueError: If not found, not authorized, or invitation processed.
        """
        # H-3 fix: use get_with_members to eagerly load members
        workspace = await self.workspace_repo.get_with_members(payload.workspace_id)
        if not workspace:
            msg = "Workspace not found"
            raise WorkspaceNotFoundError(msg)

        # Check admin/owner role
        current_member = next(
            (m for m in (workspace.members or []) if m.user_id == payload.actor_id),
            None,
        )
        if not current_member or not current_member.is_admin:
            msg = "Admin role required"
            raise WorkspaceInvitationForbiddenError(msg)

        # Preflight: verify invitation exists and belongs to this workspace before mutating
        preflight = await self.invitation_repo.get_by_id(payload.invitation_id)
        if preflight is None or preflight.workspace_id != payload.workspace_id:
            msg = "Invitation not found or already processed"
            raise WorkspaceInvitationNotFoundError(msg)

        # Cancel invitation
        cancelled_invitation = await self.invitation_repo.cancel(payload.invitation_id)
        if cancelled_invitation is None:
            msg = "Invitation not found or already processed"
            raise WorkspaceInvitationNotFoundError(msg)

        logger.info(
            "Invitation cancelled",
            extra={
                "workspace_id": str(payload.workspace_id),
                "invitation_id": str(payload.invitation_id),
            },
        )

        return CancelInvitationResult(
            invitation_id=payload.invitation_id,
            cancelled_at=datetime.now(tz=UTC),
        )

    async def request_magic_link(
        self,
        payload: RequestMagicLinkPayload,
    ) -> RequestMagicLinkResult:
        """Send a Supabase magic link to an invited email address.

        Validates the invitation is PENDING and not expired, applies rate
        limiting (3 per hour per email), then calls Supabase
        `auth.admin.invite_user_by_email` with `redirect_to` pointing to
        `/accept-invite` for finalization.

        Args:
            payload: RequestMagicLinkPayload with invitation_id and email.

        Returns:
            RequestMagicLinkResult with confirmation message.

        Raises:
            NotFoundError: If the invitation does not exist.
            ConflictError: If invitation is not PENDING or is expired.
            AppError (429): If rate limit is exceeded.
        """
        from pilot_space.config import get_settings
        from pilot_space.domain.exceptions import AppError, ConflictError, NotFoundError
        from pilot_space.infrastructure.supabase_client import get_supabase_client

        invitation = await self.invitation_repo.get_by_id(payload.invitation_id)
        if invitation is None:
            raise NotFoundError("Invitation not found")

        if invitation.is_expired or invitation.status != InvitationStatus.PENDING:
            effective = "expired" if invitation.is_expired else invitation.status.value
            raise ConflictError(f"Invitation is {effective} and cannot receive a magic link")

        # Rate limiting — fail-open (rate_limiter None means no limit configured)
        if self.rate_limiter is not None:
            allowed = await self.rate_limiter.check_and_increment(payload.email)
            if not allowed:

                class _RateLimitError(AppError):
                    http_status = 429
                    error_code = "rate_limit_exceeded"

                raise _RateLimitError(
                    "Too many magic link requests. Please wait before trying again."
                )

        settings = get_settings()
        supabase_client = await get_supabase_client()
        redirect_url = (
            f"{settings.frontend_url}/accept-invite"
            f"?invitation_id={invitation.id}"
            f"&workspace_id={invitation.workspace_id}"
        )

        try:
            await supabase_client.auth.admin.invite_user_by_email(
                payload.email,
                options={
                    "redirect_to": redirect_url,
                    "data": {
                        "workspace_invitation_id": str(invitation.id),
                        "workspace_id": str(invitation.workspace_id),
                    },
                },
            )
        except Exception:
            logger.warning(
                "supabase_invite_failed_on_request_magic_link",
                invitation_id=str(invitation.id),
                email=payload.email,
            )
            raise

        invitation.supabase_invite_sent_at = datetime.now(UTC)
        await self.invitation_repo.session.flush()

        logger.info(
            "magic_link_sent",
            invitation_id=str(invitation.id),
            workspace_id=str(invitation.workspace_id),
        )

        return RequestMagicLinkResult(
            message="Check your email for the magic link.",
            expires_in_minutes=60,
        )

    async def get_invitation_details(
        self,
        invitation_id: UUID,
    ) -> InvitationDetailResult:
        """Get public-facing invitation details (no auth required).

        Args:
            invitation_id: The invitation UUID.

        Returns:
            Public invitation details for the accept-invite page.

        Raises:
            NotFoundError: If invitation not found, expired, or not pending.
        """
        invitation = await self.invitation_repo.get_by_id(invitation_id)
        if invitation is None or invitation.is_deleted:
            msg = "Invitation not found"
            raise NotFoundError(msg)

        # Mark expired invitations on read
        if invitation.is_expired and invitation.status == InvitationStatus.PENDING:
            await self.invitation_repo.mark_expired(invitation_id)
            invitation.status = InvitationStatus.EXPIRED

        return InvitationDetailResult(
            id=invitation.id,
            workspace_name=invitation.workspace.name if invitation.workspace else "Unknown",
            workspace_slug=invitation.workspace.slug if invitation.workspace else "",
            inviter_name=invitation.inviter.full_name if invitation.inviter else None,
            role=invitation.role.value,
            email_masked=_mask_email(invitation.email),
            status=invitation.status.value,
            expires_at=invitation.expires_at,
        )

    async def accept_invitation(
        self,
        payload: AcceptInvitationPayload,
    ) -> AcceptInvitationResult:
        """Accept a workspace invitation after Supabase magic-link authentication.

        Adds the authenticated user as a workspace member, marks the invitation
        accepted, and materializes any project assignments stored on the invitation.

        Args:
            payload: Accept invitation payload containing invitation_id and user_id.

        Returns:
            AcceptInvitationResult with workspace_slug and profile-completion flag.

        Raises:
            NotFoundError: If invitation is not found.
            ConflictError: If invitation is not in PENDING state.
        """
        invitation = await self.invitation_repo.get_by_id(payload.invitation_id)
        if invitation is None:
            msg = "Invitation not found"
            raise WorkspaceInvitationNotFoundError(msg)

        from pilot_space.infrastructure.database.models.workspace_invitation import (
            InvitationStatus,
        )

        if invitation.status != InvitationStatus.PENDING:
            msg = f"Invitation is {invitation.status.value}, cannot be accepted"
            raise WorkspaceInvitationConflictError(msg)

        # Email mismatch validation (US2 — T013)
        # Ensures the authenticated user's email matches the invited email.
        if self.user_repo is not None:
            from pilot_space.domain.exceptions import ConflictError

            user = await self.user_repo.get_by_id_scalar(payload.user_id)
            if user is not None and user.email.lower() != invitation.email.lower():
                raise ConflictError(
                    "This invitation was sent to a different email address. "
                    "Please sign in with the invited email or request a new invitation."
                )

        workspace_id = invitation.workspace_id

        # Set RLS context using the inviting admin so workspace_members INSERT passes policy
        if invitation.invited_by:
            session = self.workspace_repo.session
            await set_rls_context(session, invitation.invited_by)

        await self.workspace_repo.add_member(
            workspace_id=workspace_id,
            user_id=payload.user_id,
            role=invitation.role,
        )
        await self.invitation_repo.mark_accepted(payload.invitation_id)

        # Materialize stored project assignments
        if invitation.project_assignments:
            from pilot_space.application.services.project_member import (
                InviteAssignmentsPayload,
                ProjectMemberService,
            )
            from pilot_space.infrastructure.database.repositories.project_member import (
                ProjectMemberRepository,
            )

            pm_repo = ProjectMemberRepository(session=self.workspace_repo.session)
            pm_svc = ProjectMemberService(project_member_repository=pm_repo)
            await pm_svc.materialize_invite_assignments(
                InviteAssignmentsPayload(
                    workspace_id=workspace_id,
                    user_id=payload.user_id,
                    assigned_by=invitation.invited_by,
                    project_assignments=invitation.project_assignments,
                )
            )

        workspace = await self.workspace_repo.get_by_id(workspace_id)
        if workspace is None:
            msg = "Workspace not found"
            raise WorkspaceNotFoundError(msg)

        # Determine if user needs to complete their profile (provide full_name)
        requires_profile_completion = False
        if self.user_repo is not None:
            user = await self.user_repo.get_by_id_scalar(payload.user_id)
            requires_profile_completion = user is not None and not user.full_name

        logger.info(
            "invitation_accepted",
            invitation_id=str(payload.invitation_id),
            user_id=str(payload.user_id),
            workspace_id=str(workspace_id),
        )

        return AcceptInvitationResult(
            workspace_slug=workspace.slug,
            workspace_name=workspace.name,
            role=invitation.role.value,
            requires_profile_completion=requires_profile_completion,
        )


def _mask_email(email: str) -> str:
    """Mask an email address for public display (e.g. t***@example.com)."""
    parts = email.split("@")
    if len(parts) != 2:
        return "***"
    local = parts[0]
    if len(local) <= 1:
        return f"*@{parts[1]}"
    return f"{local[0]}{'*' * (len(local) - 1)}@{parts[1]}"


__all__ = [
    "AcceptInvitationPayload",
    "AcceptInvitationResult",
    "CancelInvitationPayload",
    "CancelInvitationResult",
    "InvitationDetailResult",
    "ListInvitationsPayload",
    "ListInvitationsResult",
    "RequestMagicLinkPayload",
    "RequestMagicLinkResult",
    "WorkspaceInvitationService",
]
