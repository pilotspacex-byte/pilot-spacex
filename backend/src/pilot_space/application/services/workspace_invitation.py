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


__all__ = [
    "CancelInvitationPayload",
    "CancelInvitationResult",
    "ListInvitationsPayload",
    "ListInvitationsResult",
    "WorkspaceInvitationService",
]
