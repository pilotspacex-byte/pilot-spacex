"""Workspace service for member invitation logic.

Handles the invite_member flow: existing users are added immediately,
non-existing users get a pending invitation that auto-accepts on signup.

Source: FR-014, FR-015, FR-016, US3.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID

from pilot_space.infrastructure.database.models.workspace_invitation import (
    InvitationStatus,
    WorkspaceInvitation,
)
from pilot_space.infrastructure.database.models.workspace_member import (
    WorkspaceMember,
    WorkspaceRole,
)

if TYPE_CHECKING:
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


@dataclass
class InviteMemberResult:
    """Result of invite_member operation.

    Attributes:
        is_immediate: True if user was added immediately (existing user).
        member: WorkspaceMember if immediate add.
        invitation: WorkspaceInvitation if pending invitation created.
    """

    is_immediate: bool
    member: WorkspaceMember | None = None
    invitation: WorkspaceInvitation | None = None


class WorkspaceService:
    """Service for workspace member invitation operations.

    Follows CQRS-lite pattern per DD-064.
    """

    def __init__(
        self,
        workspace_repo: WorkspaceRepository,
        user_repo: UserRepository,
        invitation_repo: InvitationRepository,
    ) -> None:
        self.workspace_repo = workspace_repo
        self.user_repo = user_repo
        self.invitation_repo = invitation_repo

    async def invite_member(
        self,
        workspace_id: UUID,
        email: str,
        role: str,
        invited_by: UUID,
    ) -> InviteMemberResult:
        """Invite a member to a workspace.

        If the email belongs to an existing user, add them immediately.
        If not, create a pending invitation for auto-accept on signup.

        Args:
            workspace_id: Target workspace UUID.
            email: Email address to invite.
            role: Intended role (admin, member, guest).
            invited_by: UUID of the admin sending the invite.

        Returns:
            InviteMemberResult with either member or invitation.

        Raises:
            ValueError: If user is already a member or has pending invitation.
        """
        normalized_email = email.strip().lower()
        workspace_role = WorkspaceRole(role)

        # Check if user exists in the system
        existing_user = await self.user_repo.get_by_email(normalized_email)

        if existing_user:
            # Check if already a member
            is_member = await self.workspace_repo.is_member(workspace_id, existing_user.id)
            if is_member:
                msg = "User is already a member of this workspace"
                raise ValueError(msg)

            # Add immediately
            member = await self.workspace_repo.add_member(
                workspace_id=workspace_id,
                user_id=existing_user.id,
                role=workspace_role,
            )

            logger.info(
                "Member added immediately",
                extra={
                    "workspace_id": str(workspace_id),
                    "user_id": str(existing_user.id),
                    "role": role,
                },
            )

            return InviteMemberResult(is_immediate=True, member=member)

        # User doesn't exist — check for duplicate pending invitation
        has_pending = await self.invitation_repo.exists_pending(workspace_id, normalized_email)
        if has_pending:
            msg = "An invitation is already pending for this email"
            raise ValueError(msg)

        # Create pending invitation
        invitation = WorkspaceInvitation(
            workspace_id=workspace_id,
            email=normalized_email,
            role=workspace_role,
            invited_by=invited_by,
            status=InvitationStatus.PENDING,
            expires_at=datetime.now(tz=UTC) + timedelta(days=7),
        )
        invitation = await self.invitation_repo.create(invitation)

        logger.info(
            "Invitation created",
            extra={
                "workspace_id": str(workspace_id),
                "email": normalized_email,
                "role": role,
                "invitation_id": str(invitation.id),
            },
        )

        return InviteMemberResult(is_immediate=False, invitation=invitation)
