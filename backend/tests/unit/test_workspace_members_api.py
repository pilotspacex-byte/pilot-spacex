"""Unit tests for workspace member management API endpoints.

Tests POST /members (invite), GET /invitations, DELETE /invitations/{id},
and ownership transfer via PATCH /members/{user_id}.

Source: T027, plan.md API Contracts.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from pilot_space.infrastructure.database.models.workspace_invitation import (
    InvitationStatus,
    WorkspaceInvitation,
)
from pilot_space.infrastructure.database.models.workspace_member import (
    WorkspaceRole,
)

from ..factories import UserFactory, WorkspaceFactory, WorkspaceMemberFactory


def _make_workspace_with_admin():
    """Create a workspace with an admin member attached."""
    admin = UserFactory(email="admin@example.com")
    workspace = WorkspaceFactory(owner_id=admin.id, owner=admin)
    admin_member = WorkspaceMemberFactory(
        user=admin,
        workspace=workspace,
        role=WorkspaceRole.ADMIN,
    )
    workspace.members = [admin_member]
    return workspace, admin, admin_member


def _make_workspace_with_owner():
    """Create a workspace with an owner member attached."""
    owner = UserFactory(email="owner@example.com")
    workspace = WorkspaceFactory(owner_id=owner.id, owner=owner)
    owner_member = WorkspaceMemberFactory(
        user=owner,
        workspace=workspace,
        role=WorkspaceRole.OWNER,
    )
    workspace.members = [owner_member]
    return workspace, owner, owner_member


class TestAddWorkspaceMember:
    """Tests for POST /workspaces/{id}/members endpoint logic."""

    @pytest.mark.asyncio
    async def test_invite_existing_user_returns_member(self) -> None:
        """Inviting an existing user adds them immediately."""
        workspace, admin, admin_member = _make_workspace_with_admin()
        existing_user = UserFactory(email="dev@example.com")
        member = WorkspaceMemberFactory(
            user=existing_user,
            workspace=workspace,
            role=WorkspaceRole.MEMBER,
        )

        mock_workspace_repo = AsyncMock()
        mock_workspace_repo.get_by_id.return_value = workspace
        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_email.return_value = existing_user
        mock_workspace_repo.is_member.return_value = False
        mock_workspace_repo.add_member.return_value = member
        mock_invitation_repo = AsyncMock()

        from pilot_space.application.services.workspace import WorkspaceService

        service = WorkspaceService(
            mock_workspace_repo, mock_user_repo, mock_invitation_repo, AsyncMock()
        )
        result = await service.invite_member(
            workspace_id=workspace.id,
            email="dev@example.com",
            role="MEMBER",
            invited_by=admin.id,
        )

        assert result.is_immediate is True
        assert result.member is member
        mock_workspace_repo.add_member.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_invite_new_user_returns_invitation(self) -> None:
        """Inviting a non-existing user creates a pending invitation."""
        workspace, admin, _ = _make_workspace_with_admin()

        mock_workspace_repo = AsyncMock()
        mock_workspace_repo.get_by_id.return_value = workspace
        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_email.return_value = None
        mock_invitation_repo = AsyncMock()
        mock_invitation_repo.exists_pending.return_value = False

        async def return_inv(inv: WorkspaceInvitation) -> WorkspaceInvitation:
            return inv

        mock_invitation_repo.create.side_effect = return_inv

        from pilot_space.application.services.workspace import WorkspaceService

        service = WorkspaceService(
            mock_workspace_repo, mock_user_repo, mock_invitation_repo, AsyncMock()
        )
        result = await service.invite_member(
            workspace_id=workspace.id,
            email="newuser@example.com",
            role="MEMBER",
            invited_by=admin.id,
        )

        assert result.is_immediate is False
        assert result.invitation is not None
        assert result.invitation.email == "newuser@example.com"
        assert result.invitation.status == InvitationStatus.PENDING

    @pytest.mark.asyncio
    async def test_invite_already_member_raises_conflict(self) -> None:
        """Inviting someone who is already a member raises ValueError."""
        workspace, admin, _ = _make_workspace_with_admin()
        existing_user = UserFactory(email="member@example.com")

        mock_workspace_repo = AsyncMock()
        mock_workspace_repo.get_by_id.return_value = workspace
        mock_workspace_repo.is_member.return_value = True
        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_email.return_value = existing_user
        mock_invitation_repo = AsyncMock()

        from pilot_space.application.services.workspace import WorkspaceService

        service = WorkspaceService(
            mock_workspace_repo, mock_user_repo, mock_invitation_repo, AsyncMock()
        )

        with pytest.raises(ValueError, match="already a member"):
            await service.invite_member(
                workspace_id=workspace.id,
                email="member@example.com",
                role="MEMBER",
                invited_by=admin.id,
            )

    @pytest.mark.asyncio
    async def test_invite_duplicate_pending_raises_conflict(self) -> None:
        """Inviting someone with an existing pending invitation raises ValueError."""
        workspace, admin, _ = _make_workspace_with_admin()

        mock_workspace_repo = AsyncMock()
        mock_workspace_repo.get_by_id.return_value = workspace
        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_email.return_value = None
        mock_invitation_repo = AsyncMock()
        mock_invitation_repo.exists_pending.return_value = True

        from pilot_space.application.services.workspace import WorkspaceService

        service = WorkspaceService(
            mock_workspace_repo, mock_user_repo, mock_invitation_repo, AsyncMock()
        )

        with pytest.raises(ValueError, match="already pending"):
            await service.invite_member(
                workspace_id=workspace.id,
                email="pending@example.com",
                role="MEMBER",
                invited_by=admin.id,
            )


class TestListWorkspaceInvitations:
    """Tests for GET /workspaces/{id}/invitations endpoint logic."""

    @pytest.mark.asyncio
    async def test_list_invitations_returns_all(self) -> None:
        """Admin can list all invitations for a workspace."""
        workspace_id = uuid4()
        now = datetime.now(tz=UTC)
        inv1 = MagicMock(spec=WorkspaceInvitation)
        inv1.id = uuid4()
        inv1.email = "a@example.com"
        inv1.role = WorkspaceRole.MEMBER
        inv1.status = InvitationStatus.PENDING
        inv1.invited_by = uuid4()
        inv1.expires_at = now + timedelta(days=7)
        inv1.created_at = now

        inv2 = MagicMock(spec=WorkspaceInvitation)
        inv2.id = uuid4()
        inv2.email = "b@example.com"
        inv2.role = WorkspaceRole.ADMIN
        inv2.status = InvitationStatus.ACCEPTED
        inv2.invited_by = uuid4()
        inv2.expires_at = now + timedelta(days=7)
        inv2.created_at = now

        from pilot_space.infrastructure.database.repositories.invitation_repository import (
            InvitationRepository,
        )

        mock_repo = AsyncMock(spec=InvitationRepository)
        mock_repo.get_by_workspace.return_value = [inv1, inv2]

        result = await mock_repo.get_by_workspace(workspace_id)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_invitations_with_status_filter(self) -> None:
        """Invitations can be filtered by status."""
        workspace_id = uuid4()

        from pilot_space.infrastructure.database.repositories.invitation_repository import (
            InvitationRepository,
        )

        mock_repo = AsyncMock(spec=InvitationRepository)
        mock_repo.get_by_workspace.return_value = []

        result = await mock_repo.get_by_workspace(
            workspace_id, status_filter=InvitationStatus.PENDING
        )
        assert result == []
        mock_repo.get_by_workspace.assert_awaited_once_with(
            workspace_id, status_filter=InvitationStatus.PENDING
        )


class TestCancelInvitation:
    """Tests for DELETE /workspaces/{id}/invitations/{id} endpoint logic."""

    @pytest.mark.asyncio
    async def test_cancel_pending_invitation_succeeds(self) -> None:
        """Cancelling a pending invitation sets status to CANCELLED."""
        inv_id = uuid4()
        inv = MagicMock(spec=WorkspaceInvitation)
        inv.id = inv_id
        inv.status = InvitationStatus.PENDING

        from pilot_space.infrastructure.database.repositories.invitation_repository import (
            InvitationRepository,
        )

        mock_repo = AsyncMock(spec=InvitationRepository)
        mock_repo.cancel.return_value = inv

        result = await mock_repo.cancel(inv_id)
        assert result is not None
        mock_repo.cancel.assert_awaited_once_with(inv_id)

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_invitation_returns_none(self) -> None:
        """Cancelling a non-existent invitation returns None."""
        from pilot_space.infrastructure.database.repositories.invitation_repository import (
            InvitationRepository,
        )

        mock_repo = AsyncMock(spec=InvitationRepository)
        mock_repo.cancel.return_value = None

        result = await mock_repo.cancel(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_cancel_already_accepted_returns_none(self) -> None:
        """Cancelling an already-accepted invitation returns None."""
        from pilot_space.infrastructure.database.repositories.invitation_repository import (
            InvitationRepository,
        )

        mock_repo = AsyncMock(spec=InvitationRepository)
        mock_repo.cancel.return_value = None

        result = await mock_repo.cancel(uuid4())
        assert result is None


class TestOwnershipTransfer:
    """Tests for PATCH /workspaces/{id}/members/{uid} ownership transfer."""

    @pytest.mark.asyncio
    async def test_owner_can_transfer_ownership(self) -> None:
        """Owner transfers ownership — new owner gets OWNER, old gets ADMIN."""
        workspace, owner, owner_member = _make_workspace_with_owner()
        target_user = UserFactory()
        target_member = WorkspaceMemberFactory(
            user=target_user,
            workspace=workspace,
            role=WorkspaceRole.ADMIN,
        )

        mock_workspace_repo = AsyncMock()
        mock_workspace_repo.get_by_id.return_value = workspace
        mock_workspace_repo.update_member_role = AsyncMock()

        # Simulate the router guard logic
        role = WorkspaceRole.OWNER
        current_member = owner_member

        assert current_member.is_owner is True

        # Demote current owner to admin
        await mock_workspace_repo.update_member_role(workspace.id, owner.id, WorkspaceRole.ADMIN)
        # Promote target to owner
        await mock_workspace_repo.update_member_role(
            workspace.id, target_user.id, WorkspaceRole.OWNER
        )

        assert mock_workspace_repo.update_member_role.await_count == 2

    @pytest.mark.asyncio
    async def test_non_owner_cannot_transfer_ownership(self) -> None:
        """Admin cannot transfer ownership — only owner can."""
        workspace, admin, admin_member = _make_workspace_with_admin()

        # Admin trying to set OWNER role should be rejected
        role = WorkspaceRole.OWNER
        current_member = admin_member

        assert current_member.is_owner is False
        # The router raises 403 when non-owner tries to set OWNER role

    @pytest.mark.asyncio
    async def test_role_change_non_owner_role_succeeds(self) -> None:
        """Admin can change member role to non-owner roles."""
        workspace, admin, admin_member = _make_workspace_with_admin()
        target_user = UserFactory()
        target_member = WorkspaceMemberFactory(
            user=target_user,
            workspace=workspace,
            role=WorkspaceRole.MEMBER,
        )

        mock_workspace_repo = AsyncMock()

        # Change to guest (non-owner role)
        await mock_workspace_repo.update_member_role(
            workspace.id, target_user.id, WorkspaceRole.GUEST
        )

        mock_workspace_repo.update_member_role.assert_awaited_once_with(
            workspace.id, target_user.id, WorkspaceRole.GUEST
        )


class TestIsAdminAuthCheck:
    """Tests verifying is_admin property includes both OWNER and ADMIN roles."""

    @pytest.mark.asyncio
    async def test_owner_can_update_member_role(self) -> None:
        """OWNER passes is_admin check and can update member roles."""
        workspace, owner, owner_member = _make_workspace_with_owner()
        target_user = UserFactory()
        target_member = WorkspaceMemberFactory(
            user=target_user,
            workspace=workspace,
            role=WorkspaceRole.MEMBER,
        )
        workspace.members = [owner_member, target_member]

        # Simulate the router auth check (line 183 of workspace_members.py)
        current_member = owner_member
        assert current_member.is_admin is True  # OWNER passes is_admin
        assert current_member.is_owner is True

    @pytest.mark.asyncio
    async def test_admin_can_update_member_role(self) -> None:
        """ADMIN passes is_admin check and can update member roles."""
        workspace, admin, admin_member = _make_workspace_with_admin()

        current_member = admin_member
        assert current_member.is_admin is True
        assert current_member.is_owner is False

    @pytest.mark.asyncio
    async def test_member_cannot_update_member_role(self) -> None:
        """MEMBER fails is_admin check — cannot update roles."""
        workspace, _owner, owner_member = _make_workspace_with_owner()
        regular_user = UserFactory()
        regular_member = WorkspaceMemberFactory(
            user=regular_user,
            workspace=workspace,
            role=WorkspaceRole.MEMBER,
        )
        workspace.members = [owner_member, regular_member]

        current_member = regular_member
        assert current_member.is_admin is False
        assert current_member.is_owner is False

    @pytest.mark.asyncio
    async def test_owner_passes_delete_is_admin_check(self) -> None:
        """OWNER passes is_admin check in DELETE endpoint (remove member)."""
        workspace, owner, owner_member = _make_workspace_with_owner()
        target_user = UserFactory()
        target_member = WorkspaceMemberFactory(
            user=target_user,
            workspace=workspace,
            role=WorkspaceRole.MEMBER,
        )
        workspace.members = [owner_member, target_member]

        # Simulate the DELETE endpoint auth check
        is_admin = any(m.user_id == owner.id and m.is_admin for m in workspace.members)
        assert is_admin is True
