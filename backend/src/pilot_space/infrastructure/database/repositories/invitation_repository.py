"""Repository for WorkspaceInvitation entities.

Provides data access for invitation lifecycle operations.
Source: FR-016, US3.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import and_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import lazyload

from pilot_space.infrastructure.database.models.workspace_invitation import (
    InvitationStatus,
    WorkspaceInvitation,
)
from pilot_space.infrastructure.database.models.workspace_member import WorkspaceRole
from pilot_space.infrastructure.database.repositories.base import BaseRepository

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

        Marks expired pending invitations on read (write-on-read cleanup).

        Args:
            workspace_id: The workspace UUID.
            status_filter: Optional status to filter by.

        Returns:
            List of invitations ordered by creation date descending.
        """
        # Mark expired pending invitations before querying
        expire_stmt = (
            update(WorkspaceInvitation)
            .where(
                and_(
                    WorkspaceInvitation.workspace_id == workspace_id,
                    WorkspaceInvitation.status == InvitationStatus.PENDING,
                    WorkspaceInvitation.expires_at < datetime.now(tz=UTC),
                    WorkspaceInvitation.is_deleted == False,  # noqa: E712
                )
            )
            .values(status=InvitationStatus.EXPIRED)
        )
        await self.session.execute(expire_stmt)

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
        # lazyload("*") prevents the mapper-level lazy="joined" relationships
        # (workspace, inviter) from being loaded, which would cascade into
        # lazy="selectin" collections on Workspace and cause MissingGreenlet
        # errors in async mode when objects are later accessed outside a
        # SQLAlchemy greenlet context.  We only need scalar columns here.
        query = (
            select(WorkspaceInvitation)
            .options(lazyload("*"))
            .where(
                and_(
                    WorkspaceInvitation.email == email,
                    WorkspaceInvitation.status == InvitationStatus.PENDING,
                    WorkspaceInvitation.is_deleted == False,  # noqa: E712
                    WorkspaceInvitation.expires_at > datetime.now(tz=UTC),
                )
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

    async def upsert_invitation(
        self,
        workspace_id: UUID,
        email: str,
        role: WorkspaceRole,
        invited_by: UUID,
        expires_at: datetime,
    ) -> WorkspaceInvitation:
        """Create or reactivate a workspace invitation using upsert.

        Handles re-invite of an email whose previous invitation was cancelled or
        expired, without raising a UniqueConstraint error on (workspace_id, email).

        On conflict with the unique constraint ``uq_workspace_invitations_pending``:
        - Reactivates the row: sets status=PENDING, is_deleted=False, deleted_at=None
        - Resets supabase_invite_sent_at=None so a new magic link will be sent
        - Updates role, invited_by, and expires_at to the new values

        Args:
            workspace_id: Target workspace UUID.
            email: Invited email address (already normalised).
            role: Intended workspace role.
            invited_by: UUID of the admin sending the invite.
            expires_at: New expiry timestamp.

        Returns:
            The created or reactivated WorkspaceInvitation.
        """
        now = datetime.now(tz=UTC)
        stmt = (
            pg_insert(WorkspaceInvitation)
            .values(
                workspace_id=workspace_id,
                email=email,
                role=role,
                invited_by=invited_by,
                status=InvitationStatus.PENDING,
                expires_at=expires_at,
                is_deleted=False,
                deleted_at=None,
                supabase_invite_sent_at=None,
                updated_at=now,
            )
            .on_conflict_do_update(
                index_elements=[
                    WorkspaceInvitation.__table__.c.workspace_id,
                    WorkspaceInvitation.__table__.c.email,
                ],
                index_where=(WorkspaceInvitation.__table__.c.status == "PENDING")
                & (WorkspaceInvitation.__table__.c.is_deleted == False),  # noqa: E712
                set_={
                    "role": role,
                    "invited_by": invited_by,
                    "status": InvitationStatus.PENDING,
                    "expires_at": expires_at,
                    "is_deleted": False,
                    "deleted_at": None,
                    "supabase_invite_sent_at": None,
                    "accepted_at": None,
                    "updated_at": now,
                },
            )
            .returning(WorkspaceInvitation.id)
        )
        result = await self.session.execute(stmt)
        invitation_id = result.scalar_one()

        # Fetch the full ORM object (with workspace/inviter relationships) after upsert
        invitation_result = await self.session.execute(
            select(WorkspaceInvitation).where(WorkspaceInvitation.id == invitation_id)
        )
        return invitation_result.scalar_one()

    async def cancel(self, invitation_id: UUID) -> WorkspaceInvitation | None:
        """Revoke a pending invitation (admin-initiated cancellation).

        Sets status to REVOKED (migration 104). CANCELLED is preserved in
        the enum for backward compatibility with existing records.

        Args:
            invitation_id: The invitation UUID.

        Returns:
            The revoked invitation, or None if not found/already processed.
        """
        invitation = await self.get_by_id(invitation_id)
        if invitation is None or invitation.status != InvitationStatus.PENDING:
            return None
        invitation.status = InvitationStatus.REVOKED
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
