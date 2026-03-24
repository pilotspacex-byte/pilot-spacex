"""Unit tests for WorkspaceService.invite_member.

Verifies invitation flow: existing users are added immediately,
non-existing users get pending invitations.

Source: FR-014, FR-015, FR-016, US3.
"""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from pilot_space.application.services.workspace import WorkspaceService
from pilot_space.infrastructure.database.models.workspace_invitation import (
    InvitationStatus,
    WorkspaceInvitation,
)
from pilot_space.infrastructure.database.models.workspace_member import (
    WorkspaceMember,
    WorkspaceRole,
)

from ..factories import UserFactory


@pytest.fixture
def workspace_repo() -> AsyncMock:
    """Mock workspace repository."""
    return AsyncMock()


@pytest.fixture
def user_repo() -> AsyncMock:
    """Mock user repository."""
    return AsyncMock()


@pytest.fixture
def invitation_repo() -> AsyncMock:
    """Mock invitation repository."""
    return AsyncMock()


@pytest.fixture
def label_repo() -> AsyncMock:
    """Mock label repository."""
    return AsyncMock()


@pytest.fixture
def workspace_service(
    workspace_repo: AsyncMock,
    user_repo: AsyncMock,
    invitation_repo: AsyncMock,
    label_repo: AsyncMock,
) -> WorkspaceService:
    """Create WorkspaceService with mocked dependencies."""
    return WorkspaceService(
        workspace_repo=workspace_repo,
        user_repo=user_repo,
        invitation_repo=invitation_repo,
        label_repo=label_repo,
    )


class TestInviteMember:
    """Test suite for WorkspaceService.invite_member."""

    async def test_invite_existing_user_adds_immediately(
        self,
        workspace_service: WorkspaceService,
        user_repo: AsyncMock,
        workspace_repo: AsyncMock,
    ) -> None:
        """User exists and is not a member -- add immediately."""
        # Arrange
        workspace_id = uuid4()
        invited_by = uuid4()
        existing_user = UserFactory(email="dev@example.com")
        member = WorkspaceMember(
            user_id=existing_user.id,
            workspace_id=workspace_id,
            role=WorkspaceRole.MEMBER,
        )

        user_repo.get_by_email.return_value = existing_user
        workspace_repo.is_member.return_value = False
        workspace_repo.add_member.return_value = member

        # Act
        result = await workspace_service.invite_member(
            workspace_id=workspace_id,
            email="dev@example.com",
            role="MEMBER",
            invited_by=invited_by,
        )

        # Assert
        assert result.is_immediate is True
        assert result.member is member
        assert result.invitation is None
        workspace_repo.add_member.assert_awaited_once_with(
            workspace_id=workspace_id,
            user_id=existing_user.id,
            role=WorkspaceRole.MEMBER,
        )

    async def test_invite_existing_user_already_member_raises(
        self,
        workspace_service: WorkspaceService,
        user_repo: AsyncMock,
        workspace_repo: AsyncMock,
    ) -> None:
        """User exists and is already a member -- raises ConflictError."""
        from pilot_space.domain.exceptions import ConflictError

        # Arrange
        existing_user = UserFactory(email="member@example.com")
        user_repo.get_by_email.return_value = existing_user
        workspace_repo.is_member.return_value = True

        # Act & Assert
        with pytest.raises(ConflictError):
            await workspace_service.invite_member(
                workspace_id=uuid4(),
                email="member@example.com",
                role="MEMBER",
                invited_by=uuid4(),
            )

    async def test_invite_non_existing_user_creates_invitation(
        self,
        workspace_service: WorkspaceService,
        user_repo: AsyncMock,
        invitation_repo: AsyncMock,
    ) -> None:
        """User does not exist -- creates pending invitation."""
        # Arrange
        workspace_id = uuid4()
        invited_by = uuid4()
        user_repo.get_by_email.return_value = None
        invitation_repo.exists_pending.return_value = False

        # Make create return the invitation it receives
        async def return_invitation(inv: WorkspaceInvitation) -> WorkspaceInvitation:
            return inv

        invitation_repo.create.side_effect = return_invitation

        # Act
        result = await workspace_service.invite_member(
            workspace_id=workspace_id,
            email="new@example.com",
            role="MEMBER",
            invited_by=invited_by,
        )

        # Assert
        assert result.is_immediate is False
        assert result.invitation is not None
        assert result.invitation.email == "new@example.com"
        assert result.invitation.workspace_id == workspace_id
        assert result.invitation.role == WorkspaceRole.MEMBER
        assert result.invitation.status == InvitationStatus.PENDING
        assert result.member is None

    async def test_invite_duplicate_pending_raises(
        self,
        workspace_service: WorkspaceService,
        user_repo: AsyncMock,
        invitation_repo: AsyncMock,
    ) -> None:
        """User does not exist, pending invitation exists -- raises ConflictError."""
        from pilot_space.domain.exceptions import ConflictError

        # Arrange
        user_repo.get_by_email.return_value = None
        invitation_repo.exists_pending.return_value = True

        # Act & Assert
        with pytest.raises(ConflictError):
            await workspace_service.invite_member(
                workspace_id=uuid4(),
                email="pending@example.com",
                role="MEMBER",
                invited_by=uuid4(),
            )

    async def test_invite_normalizes_email(
        self,
        workspace_service: WorkspaceService,
        user_repo: AsyncMock,
        invitation_repo: AsyncMock,
    ) -> None:
        """Email is stripped and lowercased before lookup."""
        # Arrange
        user_repo.get_by_email.return_value = None
        invitation_repo.exists_pending.return_value = False

        async def return_invitation(inv: WorkspaceInvitation) -> WorkspaceInvitation:
            return inv

        invitation_repo.create.side_effect = return_invitation

        # Act
        result = await workspace_service.invite_member(
            workspace_id=uuid4(),
            email="  Test@Example.COM  ",
            role="MEMBER",
            invited_by=uuid4(),
        )

        # Assert
        user_repo.get_by_email.assert_awaited_once_with("test@example.com")
        assert result.invitation is not None
        assert result.invitation.email == "test@example.com"
