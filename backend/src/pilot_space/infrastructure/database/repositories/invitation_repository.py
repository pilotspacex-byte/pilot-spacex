"""Repository for WorkspaceInvitation entities.

Provides data access for invitation lifecycle operations.
Source: FR-016, US3.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pilot_space.infrastructure.database.models.workspace_invitation import (
    InvitationStatus,
    WorkspaceInvitation,
)
from pilot_space.infrastructure.database.repositories.base import BaseRepository
from sqlalchemy import and_, select

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession


class InvitationRepository(BaseRepository[WorkspaceInvitation]):
    """Repository for workspace invitation operations.

    Extends BaseRepository with invitation-specific queries:
    listing by workspace, finding pending by email, and status transitions.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with async session."""
        super().__init__(session, WorkspaceInvitation)

    async def get_by_workspace(
        self,
        workspace_id: UUID,
        *,
        status_filter: InvitationStatus | None = None,
    ) -> Sequence[WorkspaceInvitation]:
        """List invitations for a workspace, optionally filtered by status.

        Args:
            workspace_id: The workspace UUID.
            status_filter: Optional status to filter by.

        Returns:
            List of invitations ordered by creation date descending.
        """
        query = select(WorkspaceInvitation).where(
            and_(
                WorkspaceInvitation.workspace_id == workspace_id,
                WorkspaceInvitation.is_deleted == False,  # noqa: E712
            )
        )
        if status_filter is not None:
            query = query.where(WorkspaceInvitation.status == status_filter)
        query = query.order_by(WorkspaceInvitation.created_at.desc())
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_pending_by_email(
        self,
        email: str,
    ) -> Sequence[WorkspaceInvitation]:
        """Find all pending invitations for an email address.

        Used during user signup to auto-accept pending invitations.

        Args:
            email: The email address to look up.

        Returns:
            List of pending invitations for the email.
        """
        query = select(WorkspaceInvitation).where(
            and_(
                WorkspaceInvitation.email == email,
                WorkspaceInvitation.status == InvitationStatus.PENDING,
                WorkspaceInvitation.is_deleted == False,  # noqa: E712
                WorkspaceInvitation.expires_at > datetime.now(tz=UTC),
            )
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def exists_pending(
        self,
        workspace_id: UUID,
        email: str,
    ) -> bool:
        """Check if a pending invitation already exists for this email in the workspace.

        Args:
            workspace_id: The workspace UUID.
            email: The email address to check.

        Returns:
            True if a pending invitation exists.
        """
        query = select(WorkspaceInvitation).where(
            and_(
                WorkspaceInvitation.workspace_id == workspace_id,
                WorkspaceInvitation.email == email,
                WorkspaceInvitation.status == InvitationStatus.PENDING,
                WorkspaceInvitation.is_deleted == False,  # noqa: E712
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

    async def cancel(self, invitation_id: UUID) -> WorkspaceInvitation | None:
        """Cancel a pending invitation.

        Args:
            invitation_id: The invitation UUID.

        Returns:
            The cancelled invitation, or None if not found/already processed.
        """
        invitation = await self.get_by_id(invitation_id)
        if invitation is None or invitation.status != InvitationStatus.PENDING:
            return None
        invitation.status = InvitationStatus.CANCELLED
        await self.session.flush()
        return invitation

    async def mark_accepted(self, invitation_id: UUID) -> WorkspaceInvitation | None:
        """Mark an invitation as accepted.

        Args:
            invitation_id: The invitation UUID.

        Returns:
            The accepted invitation, or None if not found/already processed.
        """
        invitation = await self.get_by_id(invitation_id)
        if invitation is None or invitation.status != InvitationStatus.PENDING:
            return None
        invitation.status = InvitationStatus.ACCEPTED
        invitation.accepted_at = datetime.now(tz=UTC)
        await self.session.flush()
        return invitation

    async def mark_expired(self, invitation_id: UUID) -> WorkspaceInvitation | None:
        """Mark an invitation as expired.

        Args:
            invitation_id: The invitation UUID.

        Returns:
            The expired invitation, or None if not found/already processed.
        """
        invitation = await self.get_by_id(invitation_id)
        if invitation is None or invitation.status != InvitationStatus.PENDING:
            return None
        invitation.status = InvitationStatus.EXPIRED
        await self.session.flush()
        return invitation
