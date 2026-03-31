"""Unit tests for InvitationRepository.

Tests invitation lifecycle operations using mocked AsyncSession.
Source: FR-016, US3.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from pilot_space.infrastructure.database.models.workspace_invitation import (
    InvitationStatus,
    WorkspaceInvitation,
)
from pilot_space.infrastructure.database.models.workspace_member import WorkspaceRole
from pilot_space.infrastructure.database.repositories.invitation_repository import (
    InvitationRepository,
)


def _make_invitation(
    email: str = "invitee@example.com",
    status: InvitationStatus = InvitationStatus.PENDING,
    workspace_id: ... = None,
    invited_by: ... = None,
) -> WorkspaceInvitation:
    """Create a WorkspaceInvitation instance for testing."""
    return WorkspaceInvitation(
        id=uuid4(),
        workspace_id=workspace_id or uuid4(),
        email=email,
        role=WorkspaceRole.MEMBER,
        invited_by=invited_by or uuid4(),
        status=status,
        expires_at=datetime.now(tz=UTC) + timedelta(days=7),
    )


def _mock_session_with_results(
    results: list[WorkspaceInvitation],
) -> AsyncMock:
    """Create a mock session that returns the given results from execute."""
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = results
    mock_result.scalar_one_or_none.return_value = results[0] if results else None
    session.execute.return_value = mock_result
    return session


class TestGetByWorkspace:
    """Tests for InvitationRepository.get_by_workspace."""

    async def test_get_by_workspace_returns_invitations(self) -> None:
        """Returns all non-deleted invitations for a workspace."""
        # Arrange
        workspace_id = uuid4()
        inv1 = _make_invitation(email="a@test.com", workspace_id=workspace_id)
        inv2 = _make_invitation(email="b@test.com", workspace_id=workspace_id)
        session = _mock_session_with_results([inv1, inv2])

        repo = InvitationRepository(session=session)

        # Act
        results = await repo.get_by_workspace(workspace_id)

        # Assert
        assert len(results) == 2
        # 2 calls: expire stale invitations UPDATE + SELECT query
        assert session.execute.await_count == 2

    async def test_get_by_workspace_with_status_filter(self) -> None:
        """Filters invitations by status when status_filter provided."""
        # Arrange
        workspace_id = uuid4()
        pending = _make_invitation(email="pending@test.com", workspace_id=workspace_id)
        session = _mock_session_with_results([pending])

        repo = InvitationRepository(session=session)

        # Act
        results = await repo.get_by_workspace(
            workspace_id,
            status_filter=InvitationStatus.PENDING,
        )

        # Assert
        assert len(results) == 1
        # 2 calls: expire stale invitations UPDATE + SELECT query
        assert session.execute.await_count == 2


class TestExistsPending:
    """Tests for InvitationRepository.exists_pending."""

    async def test_exists_pending_true(self) -> None:
        """Returns True when a pending invitation exists for the email."""
        # Arrange
        workspace_id = uuid4()
        invitation = _make_invitation(workspace_id=workspace_id)
        session = _mock_session_with_results([invitation])

        repo = InvitationRepository(session=session)

        # Act
        result = await repo.exists_pending(workspace_id, "invitee@example.com")

        # Assert
        assert result is True

    async def test_exists_pending_false(self) -> None:
        """Returns False when no pending invitation exists."""
        # Arrange
        session = _mock_session_with_results([])

        repo = InvitationRepository(session=session)

        # Act
        result = await repo.exists_pending(uuid4(), "nobody@test.com")

        # Assert
        assert result is False


class TestStatusTransitions:
    """Tests for cancel, mark_accepted, and mark_expired."""

    async def test_cancel_pending_invitation(self) -> None:
        """Cancelling a pending invitation sets status to CANCELLED."""
        # Arrange
        invitation = _make_invitation(status=InvitationStatus.PENDING)
        session = AsyncMock()
        repo = InvitationRepository(session=session)

        # Mock get_by_id to return the invitation
        repo.get_by_id = AsyncMock(return_value=invitation)

        # Act
        result = await repo.cancel(invitation.id)

        # Assert
        assert result is not None
        assert result.status == InvitationStatus.REVOKED
        session.flush.assert_awaited_once()

    async def test_cancel_non_pending_returns_none(self) -> None:
        """Cancelling a non-pending invitation returns None."""
        # Arrange
        invitation = _make_invitation(status=InvitationStatus.ACCEPTED)
        session = AsyncMock()
        repo = InvitationRepository(session=session)
        repo.get_by_id = AsyncMock(return_value=invitation)

        # Act
        result = await repo.cancel(invitation.id)

        # Assert
        assert result is None
        session.flush.assert_not_awaited()

    async def test_mark_accepted_sets_status_and_timestamp(self) -> None:
        """Accepting sets status to ACCEPTED and records accepted_at."""
        # Arrange
        invitation = _make_invitation(status=InvitationStatus.PENDING)
        assert invitation.accepted_at is None
        session = AsyncMock()
        repo = InvitationRepository(session=session)
        repo.get_by_id = AsyncMock(return_value=invitation)

        before = datetime.now(tz=UTC)

        # Act
        result = await repo.mark_accepted(invitation.id)

        # Assert
        assert result is not None
        assert result.status == InvitationStatus.ACCEPTED
        assert result.accepted_at is not None
        assert result.accepted_at >= before
        session.flush.assert_awaited_once()

    async def test_mark_expired_sets_status(self) -> None:
        """Expiring a pending invitation sets status to EXPIRED."""
        # Arrange
        invitation = _make_invitation(status=InvitationStatus.PENDING)
        session = AsyncMock()
        repo = InvitationRepository(session=session)
        repo.get_by_id = AsyncMock(return_value=invitation)

        # Act
        result = await repo.mark_expired(invitation.id)

        # Assert
        assert result is not None
        assert result.status == InvitationStatus.EXPIRED
        session.flush.assert_awaited_once()
