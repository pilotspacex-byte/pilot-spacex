"""Unit tests for workspace backend bugfixes.

Tests for issues found during code review:
- H-4: AI configuration uses get_with_members (avoids MissingGreenlet)
- H-5: Cross-workspace invitation cancel security
- H-6: Delete workspace requires owner (not just admin)
- M-2: Settings merge vs replace on PATCH
- M-5: Owner self-removal prevention

Source: Backend review task #3.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from pilot_space.infrastructure.database.models.workspace_member import (
    WorkspaceRole,
)

from ..factories import UserFactory, WorkspaceFactory, WorkspaceMemberFactory


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


class TestH4AIConfigUsesGetWithMembers:
    """H-4: _verify_workspace_membership must use get_with_members, not get_by_id."""

    @pytest.mark.asyncio
    async def test_verify_membership_calls_get_with_members(self) -> None:
        """_verify_workspace_membership calls get_with_members (not get_by_id)."""
        from pilot_space.api.v1.routers.ai_configuration import (
            _verify_workspace_membership,
        )

        workspace, owner, owner_member = _make_workspace_with_owner()

        mock_workspace_repo = AsyncMock()
        mock_workspace_repo.get_with_members.return_value = workspace
        mock_workspace_repo.get_by_id.return_value = workspace

        role = await _verify_workspace_membership(
            workspace_id=workspace.id,
            user_id=owner.id,
            workspace_repo=mock_workspace_repo,
        )

        assert role == WorkspaceRole.OWNER
        mock_workspace_repo.get_with_members.assert_awaited_once_with(workspace.id)
        mock_workspace_repo.get_by_id.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_verify_membership_admin_required_rejects_member(self) -> None:
        """_verify_workspace_membership with require_admin=True rejects plain member."""
        from pilot_space.api.v1.routers.ai_configuration import (
            _verify_workspace_membership,
        )

        member_user = UserFactory(email="member@example.com")
        workspace = WorkspaceFactory(owner_id=member_user.id, owner=member_user)
        member = WorkspaceMemberFactory(
            user=member_user,
            workspace=workspace,
            role=WorkspaceRole.MEMBER,
        )
        workspace.members = [member]

        mock_workspace_repo = AsyncMock()
        mock_workspace_repo.get_with_members.return_value = workspace

        with pytest.raises(HTTPException) as exc_info:
            await _verify_workspace_membership(
                workspace_id=workspace.id,
                user_id=member_user.id,
                workspace_repo=mock_workspace_repo,
                require_admin=True,
            )

        assert exc_info.value.status_code == 403
        assert "Admin" in exc_info.value.detail


class TestH6DeleteWorkspaceRequiresOwner:
    """H-6: delete_workspace should require owner role, not just admin."""

    @pytest.mark.asyncio
    async def test_admin_cannot_delete_workspace(self) -> None:
        """Admin (non-owner) gets 403 when trying to delete workspace."""
        from pilot_space.api.v1.routers.workspaces import delete_workspace

        workspace, admin, admin_member = _make_workspace_with_admin()

        mock_workspace_repo = AsyncMock()
        mock_workspace_repo.get_with_members.return_value = workspace
        mock_workspace_repo.get_by_slug_with_members.return_value = workspace

        current_user = MagicMock()
        current_user.user_id = admin.id

        with pytest.raises(HTTPException) as exc_info:
            await delete_workspace(
                workspace_id=str(workspace.id),
                current_user=current_user,
                workspace_repo=mock_workspace_repo,
            )

        assert exc_info.value.status_code == 403
        assert "Owner" in exc_info.value.detail or "owner" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_owner_can_delete_workspace(self) -> None:
        """Owner can delete workspace."""
        from pilot_space.api.v1.routers.workspaces import delete_workspace

        workspace, owner, owner_member = _make_workspace_with_owner()

        mock_workspace_repo = AsyncMock()
        mock_workspace_repo.get_with_members.return_value = workspace
        mock_workspace_repo.get_by_slug_with_members.return_value = workspace
        mock_workspace_repo.delete.return_value = None

        current_user = MagicMock()
        current_user.user_id = owner.id

        result = await delete_workspace(
            workspace_id=str(workspace.id),
            current_user=current_user,
            workspace_repo=mock_workspace_repo,
        )

        assert result.id == workspace.id
        mock_workspace_repo.delete.assert_awaited_once()


class TestM5OwnerSelfRemovalPrevention:
    """M-5: Owner cannot remove themselves from workspace."""

    @pytest.mark.asyncio
    async def test_owner_cannot_self_remove(self) -> None:
        """Owner trying to remove themselves gets 400."""
        from pilot_space.api.v1.routers.workspace_members import remove_workspace_member

        workspace, owner, owner_member = _make_workspace_with_owner()

        mock_workspace_repo = AsyncMock()
        mock_workspace_repo.get_with_members.return_value = workspace

        current_user = MagicMock()
        current_user.user_id = owner.id

        with pytest.raises(HTTPException) as exc_info:
            await remove_workspace_member(
                workspace_id=workspace.id,
                user_id=owner.id,
                current_user=current_user,
                workspace_repo=mock_workspace_repo,
            )

        assert exc_info.value.status_code == 400
        assert "owner" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_admin_count_includes_owner_role(self) -> None:
        """When checking 'only admin', both OWNER and ADMIN roles count."""
        from pilot_space.api.v1.routers.workspace_members import remove_workspace_member

        # Setup: owner + admin, admin tries to self-remove
        owner = UserFactory(email="owner@example.com")
        admin = UserFactory(email="admin@example.com")
        workspace = WorkspaceFactory(owner_id=owner.id, owner=owner)
        owner_member = WorkspaceMemberFactory(
            user=owner, workspace=workspace, role=WorkspaceRole.OWNER
        )
        admin_member = WorkspaceMemberFactory(
            user=admin, workspace=workspace, role=WorkspaceRole.ADMIN
        )
        workspace.members = [owner_member, admin_member]

        mock_workspace_repo = AsyncMock()
        mock_workspace_repo.get_with_members.return_value = workspace
        mock_workspace_repo.remove_member.return_value = True

        current_user = MagicMock()
        current_user.user_id = admin.id

        # Admin can self-remove because owner is still there (admin_count=2)
        await remove_workspace_member(
            workspace_id=workspace.id,
            user_id=admin.id,
            current_user=current_user,
            workspace_repo=mock_workspace_repo,
        )

        mock_workspace_repo.remove_member.assert_awaited_once_with(workspace.id, admin.id)


class TestM2SettingsMerge:
    """M-2: PATCH workspace settings should merge, not replace."""

    @pytest.mark.asyncio
    async def test_settings_merge_preserves_existing_keys(self) -> None:
        """Updating settings merges new keys with existing ones."""
        from pilot_space.api.v1.routers.workspaces import update_workspace
        from pilot_space.api.v1.schemas.workspace import WorkspaceUpdate

        workspace, owner, owner_member = _make_workspace_with_owner()
        # Pre-existing settings
        workspace.settings = {"ai_features": {"ghost_text": True}, "theme": "light"}

        mock_workspace_repo = AsyncMock()
        mock_workspace_repo.get_with_members.return_value = workspace
        mock_workspace_repo.get_by_slug_with_members.return_value = workspace
        mock_workspace_repo.update.return_value = workspace

        current_user = MagicMock()
        current_user.user_id = owner.id

        # Send only a new setting key
        request = WorkspaceUpdate(settings={"new_key": "new_value"})

        await update_workspace(
            workspace_id=str(workspace.id),
            request=request,
            current_user=current_user,
            workspace_repo=mock_workspace_repo,
        )

        # Verify existing keys are preserved
        assert workspace.settings is not None
        assert workspace.settings.get("theme") == "light"
        assert workspace.settings.get("ai_features") == {"ghost_text": True}
        assert workspace.settings.get("new_key") == "new_value"

    @pytest.mark.asyncio
    async def test_settings_merge_from_none(self) -> None:
        """Settings merge works when workspace.settings is None."""
        from pilot_space.api.v1.routers.workspaces import update_workspace
        from pilot_space.api.v1.schemas.workspace import WorkspaceUpdate

        workspace, owner, owner_member = _make_workspace_with_owner()
        workspace.settings = None

        mock_workspace_repo = AsyncMock()
        mock_workspace_repo.get_with_members.return_value = workspace
        mock_workspace_repo.get_by_slug_with_members.return_value = workspace
        mock_workspace_repo.update.return_value = workspace

        current_user = MagicMock()
        current_user.user_id = owner.id

        request = WorkspaceUpdate(settings={"theme": "dark"})

        await update_workspace(
            workspace_id=str(workspace.id),
            request=request,
            current_user=current_user,
            workspace_repo=mock_workspace_repo,
        )

        assert workspace.settings == {"theme": "dark"}


class TestH5CrossWorkspaceInvitationCancel:
    """H-5: cancel_workspace_invitation must verify invitation belongs to workspace."""

    @pytest.mark.asyncio
    async def test_cancel_invitation_from_other_workspace_rejected(self) -> None:
        """Admin cannot cancel invitation from a different workspace."""
        from pilot_space.api.v1.routers.workspace_invitations import (
            cancel_workspace_invitation,
        )

        workspace_a, admin_a, admin_member_a = _make_workspace_with_admin()
        workspace_b_id = uuid4()  # Different workspace

        # Invitation belongs to workspace_b
        mock_invitation = MagicMock()
        mock_invitation.workspace_id = workspace_b_id
        mock_invitation.status = "pending"

        mock_workspace_repo = AsyncMock()
        mock_workspace_repo.get_with_members.return_value = workspace_a

        mock_invitation_repo = AsyncMock()
        mock_invitation_repo.cancel.return_value = mock_invitation

        current_user = MagicMock()
        current_user.user_id = admin_a.id

        with pytest.raises(HTTPException) as exc_info:
            await cancel_workspace_invitation(
                workspace_id=workspace_a.id,
                invitation_id=uuid4(),
                current_user=current_user,
                workspace_repo=mock_workspace_repo,
                invitation_repo=mock_invitation_repo,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_cancel_invitation_same_workspace_succeeds(self) -> None:
        """Admin can cancel invitation from their own workspace."""
        from pilot_space.api.v1.routers.workspace_invitations import (
            cancel_workspace_invitation,
        )

        workspace, admin, admin_member = _make_workspace_with_admin()

        # Invitation belongs to same workspace
        mock_invitation = MagicMock()
        mock_invitation.workspace_id = workspace.id
        mock_invitation.status = "pending"

        mock_workspace_repo = AsyncMock()
        mock_workspace_repo.get_with_members.return_value = workspace

        mock_invitation_repo = AsyncMock()
        mock_invitation_repo.cancel.return_value = mock_invitation

        current_user = MagicMock()
        current_user.user_id = admin.id

        # Should not raise
        await cancel_workspace_invitation(
            workspace_id=workspace.id,
            invitation_id=uuid4(),
            current_user=current_user,
            workspace_repo=mock_workspace_repo,
            invitation_repo=mock_invitation_repo,
        )
