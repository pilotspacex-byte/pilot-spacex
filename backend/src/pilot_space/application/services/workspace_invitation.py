"""Workspace invitation management service.

Handles invitation operations following CQRS-lite pattern (DD-064):
- List workspace invitations
- Cancel invitation

Note: The invite_member operation is in WorkspaceService (maintains
existing API compatibility).

Source: FR-014, FR-015, FR-016, US3.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pilot_space.domain.exceptions import ForbiddenError, NotFoundError
from pilot_space.infrastructure.database.models.workspace_invitation import (
    InvitationStatus,
)
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.workspace_invitation import (
        WorkspaceInvitation,
    )
    from pilot_space.infrastructure.database.repositories.invitation_repository import (
        InvitationRepository,
    )
    from pilot_space.infrastructure.database.repositories.workspace_repository import (
        WorkspaceRepository,
    )

logger = get_logger(__name__)


# ===== Payloads & Results =====


@dataclass
class ListInvitationsPayload:
    """Payload for listing workspace invitations."""

    workspace_id: UUID
    requesting_user_id: UUID


@dataclass
class ListInvitationsResult:
    """Result of list_invitations operation."""

    invitations: list[WorkspaceInvitation]


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
    """Result after accepting an invitation."""

    workspace_slug: str
    workspace_name: str
    role: str


class WorkspaceInvitationService:
    """Service for workspace invitation operations.

    Follows CQRS-lite pattern per DD-064.
    """

    def __init__(
        self,
        workspace_repo: WorkspaceRepository,
        invitation_repo: InvitationRepository,
    ) -> None:
        self.workspace_repo = workspace_repo
        self.invitation_repo = invitation_repo

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
            raise NotFoundError(msg)

        # Check admin/owner role
        current_member = next(
            (m for m in (workspace.members or []) if m.user_id == payload.requesting_user_id),
            None,
        )
        if not current_member or not current_member.is_admin:
            msg = "Admin role required"
            raise ForbiddenError(msg)

        invitations = await self.invitation_repo.get_by_workspace(payload.workspace_id)

        return ListInvitationsResult(invitations=list(invitations))

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
            raise NotFoundError(msg)

        # Check admin/owner role
        current_member = next(
            (m for m in (workspace.members or []) if m.user_id == payload.actor_id),
            None,
        )
        if not current_member or not current_member.is_admin:
            msg = "Admin role required"
            raise ForbiddenError(msg)

        # Cancel invitation
        cancelled_invitation = await self.invitation_repo.cancel(payload.invitation_id)
        if cancelled_invitation is None:
            msg = "Invitation not found or already processed"
            raise NotFoundError(msg)

        # H-5 fix: verify invitation belongs to this workspace (cross-workspace security)
        if cancelled_invitation.workspace_id != payload.workspace_id:
            msg = "Invitation not found or already processed"
            raise NotFoundError(msg)

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
        invitation_id: UUID,
        user_id: UUID,
        user_email: str,
    ) -> AcceptInvitationResult:
        """Accept a pending invitation.

        Verifies the authenticated user's email matches the invitation,
        adds them to the workspace, and marks the invitation as accepted.

        Args:
            invitation_id: The invitation UUID.
            user_id: The authenticated user's UUID.
            user_email: The authenticated user's email.

        Returns:
            Accept result with workspace slug for redirect.

        Raises:
            NotFoundError: If invitation not found, expired, or not pending.
            ForbiddenError: If email doesn't match the invitation.
        """
        invitation = await self.invitation_repo.get_by_id(invitation_id)
        if invitation is None or invitation.is_deleted:
            msg = "Invitation not found"
            raise NotFoundError(msg)

        # Check pending status first, then expiry (avoids mark_expired on
        # already-accepted/cancelled invitations whose transaction would
        # roll back anyway).
        if invitation.status != InvitationStatus.PENDING:
            msg = "Invitation is no longer pending"
            raise NotFoundError(msg)

        if invitation.is_expired:
            await self.invitation_repo.mark_expired(invitation_id)
            msg = "Invitation has expired"
            raise NotFoundError(msg)

        if invitation.email.lower() != user_email.strip().lower():
            msg = "This invitation was sent to a different email address"
            raise ForbiddenError(msg)

        workspace_name = invitation.workspace.name if invitation.workspace else "Unknown"
        workspace_slug = invitation.workspace.slug if invitation.workspace else ""

        # Check if already a member — treat as idempotent success
        is_member = await self.workspace_repo.is_member(invitation.workspace_id, user_id)
        if is_member:
            await self.invitation_repo.mark_accepted(invitation_id)
            return AcceptInvitationResult(
                workspace_slug=workspace_slug,
                workspace_name=workspace_name,
                role=invitation.role.value,
            )

        # Add to workspace
        from pilot_space.infrastructure.database.models.workspace_member import (
            WorkspaceRole,
        )

        await self.workspace_repo.add_member(
            workspace_id=invitation.workspace_id,
            user_id=user_id,
            role=WorkspaceRole(invitation.role.value),
        )
        await self.invitation_repo.mark_accepted(invitation_id)

        logger.info(
            "Invitation accepted",
            extra={
                "invitation_id": str(invitation_id),
                "user_id": str(user_id),
                "workspace_id": str(invitation.workspace_id),
            },
        )

        return AcceptInvitationResult(
            workspace_slug=workspace_slug,
            workspace_name=workspace_name,
            role=invitation.role.value,
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
    "AcceptInvitationResult",
    "CancelInvitationPayload",
    "CancelInvitationResult",
    "InvitationDetailResult",
    "ListInvitationsPayload",
    "ListInvitationsResult",
    "WorkspaceInvitationService",
]
