"""Unit tests for ensure_user_synced auto-accept invitation logic.

Verifies that when a new user signs up, pending invitations
are automatically accepted and the user is added to workspaces.

Source: FR-016, RD-004, T020.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from pilot_space.infrastructure.auth import TokenPayload
from pilot_space.infrastructure.database.models.workspace_invitation import (
    WorkspaceInvitation,
)
from pilot_space.infrastructure.database.models.workspace_member import WorkspaceRole


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create mock async session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    # Support `async with session.begin_nested():` (savepoint context manager)
    _savepoint = AsyncMock()
    _savepoint.__aenter__ = AsyncMock(return_value=_savepoint)
    _savepoint.__aexit__ = AsyncMock(return_value=False)
    session.begin_nested = MagicMock(return_value=_savepoint)
    return session


@pytest.fixture
def token_payload() -> TokenPayload:
    """Create a test token payload."""
    now = datetime.now(tz=UTC)
    return TokenPayload(
        sub=str(uuid4()),
        email="newuser@example.com",
        role="authenticated",
        aud="authenticated",
        exp=int(now.timestamp()) + 3600,
        iat=int(now.timestamp()),
        app_metadata={},
        user_metadata={},
    )


def _make_mock_repos(
    *,
    user_exists: bool = False,
    pending_invitations: list[MagicMock] | None = None,
) -> tuple[AsyncMock, AsyncMock, AsyncMock]:
    """Create mock repositories for ensure_user_synced.

    Args:
        user_exists: Whether get_by_id_scalar should find a user.
        pending_invitations: List of mock invitations to return.

    Returns:
        Tuple of (user_repo, invitation_repo, workspace_repo).
    """
    user_repo = AsyncMock()
    user_repo.get_by_id_scalar.return_value = MagicMock() if user_exists else None
    user_repo.create = AsyncMock()

    invitation_repo = AsyncMock()
    invitation_repo.get_pending_by_email.return_value = pending_invitations or []
    invitation_repo.mark_accepted = AsyncMock()

    workspace_repo = AsyncMock()
    workspace_repo.add_member = AsyncMock()

    return user_repo, invitation_repo, workspace_repo


class TestEnsureUserSyncedAutoAccept:
    """Tests for auto-accept invitation logic in ensure_user_synced."""

    @pytest.mark.asyncio
    async def test_existing_user_returns_immediately(
        self,
        mock_session: AsyncMock,
        token_payload: TokenPayload,
    ) -> None:
        """Existing user skips invitation check entirely."""
        user_repo, invitation_repo, workspace_repo = _make_mock_repos(user_exists=True)

        with (
            patch(
                "pilot_space.infrastructure.database.repositories.user_repository.UserRepository",
                return_value=user_repo,
            ),
            patch(
                "pilot_space.infrastructure.database.repositories.invitation_repository.InvitationRepository",
                return_value=invitation_repo,
            ),
            patch(
                "pilot_space.infrastructure.database.repositories.workspace_repository.WorkspaceRepository",
                return_value=workspace_repo,
            ),
        ):
            from pilot_space.dependencies.auth import ensure_user_synced

            result = await ensure_user_synced(token_payload, mock_session)

        assert result == token_payload.user_id
        invitation_repo.get_pending_by_email.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_new_user_no_pending_invitations(
        self,
        mock_session: AsyncMock,
        token_payload: TokenPayload,
    ) -> None:
        """New user with no pending invitations creates user only."""
        user_repo, invitation_repo, workspace_repo = _make_mock_repos(
            user_exists=False,
            pending_invitations=[],
        )

        with (
            patch(
                "pilot_space.infrastructure.database.repositories.user_repository.UserRepository",
                return_value=user_repo,
            ),
            patch(
                "pilot_space.infrastructure.database.repositories.invitation_repository.InvitationRepository",
                return_value=invitation_repo,
            ),
            patch(
                "pilot_space.infrastructure.database.repositories.workspace_repository.WorkspaceRepository",
                return_value=workspace_repo,
            ),
        ):
            from pilot_space.dependencies.auth import ensure_user_synced

            result = await ensure_user_synced(token_payload, mock_session)

        assert result == token_payload.user_id
        user_repo.create.assert_awaited_once()
        invitation_repo.get_pending_by_email.assert_awaited_once_with("newuser@example.com")
        workspace_repo.add_member.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_new_user_with_pending_invitations_auto_accepts(
        self,
        mock_session: AsyncMock,
        token_payload: TokenPayload,
    ) -> None:
        """New user with pending invitations auto-accepts all of them."""
        ws_id_1 = uuid4()
        ws_id_2 = uuid4()
        inv_id_1 = uuid4()
        inv_id_2 = uuid4()

        invitation_1 = MagicMock(spec=WorkspaceInvitation)
        invitation_1.id = inv_id_1
        invitation_1.workspace_id = ws_id_1
        invitation_1.role = WorkspaceRole.MEMBER

        invitation_2 = MagicMock(spec=WorkspaceInvitation)
        invitation_2.id = inv_id_2
        invitation_2.workspace_id = ws_id_2
        invitation_2.role = WorkspaceRole.ADMIN

        user_repo, invitation_repo, workspace_repo = _make_mock_repos(
            user_exists=False,
            pending_invitations=[invitation_1, invitation_2],
        )

        with (
            patch(
                "pilot_space.infrastructure.database.repositories.user_repository.UserRepository",
                return_value=user_repo,
            ),
            patch(
                "pilot_space.infrastructure.database.repositories.invitation_repository.InvitationRepository",
                return_value=invitation_repo,
            ),
            patch(
                "pilot_space.infrastructure.database.repositories.workspace_repository.WorkspaceRepository",
                return_value=workspace_repo,
            ),
        ):
            from pilot_space.dependencies.auth import ensure_user_synced

            result = await ensure_user_synced(token_payload, mock_session)

        assert result == token_payload.user_id

        # Verify both invitations auto-accepted
        assert workspace_repo.add_member.await_count == 2
        workspace_repo.add_member.assert_any_await(
            workspace_id=ws_id_1,
            user_id=token_payload.user_id,
            role=WorkspaceRole.MEMBER,
        )
        workspace_repo.add_member.assert_any_await(
            workspace_id=ws_id_2,
            user_id=token_payload.user_id,
            role=WorkspaceRole.ADMIN,
        )

        assert invitation_repo.mark_accepted.await_count == 2
        invitation_repo.mark_accepted.assert_any_await(inv_id_1)
        invitation_repo.mark_accepted.assert_any_await(inv_id_2)

        # ensure_user_synced commits twice: once after user creation, once after
        # invitation acceptance loop.
        assert mock_session.commit.await_count == 2

    @pytest.mark.asyncio
    async def test_new_user_uses_placeholder_email_when_missing(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """User without email in JWT gets placeholder, no invitations matched."""
        now = datetime.now(tz=UTC)
        user_id = uuid4()
        payload = TokenPayload(
            sub=str(user_id),
            email=None,
            role="authenticated",
            aud="authenticated",
            exp=int(now.timestamp()) + 3600,
            iat=int(now.timestamp()),
            app_metadata={},
            user_metadata={},
        )

        user_repo, invitation_repo, workspace_repo = _make_mock_repos(
            user_exists=False,
            pending_invitations=[],
        )

        with (
            patch(
                "pilot_space.infrastructure.database.repositories.user_repository.UserRepository",
                return_value=user_repo,
            ),
            patch(
                "pilot_space.infrastructure.database.repositories.invitation_repository.InvitationRepository",
                return_value=invitation_repo,
            ),
            patch(
                "pilot_space.infrastructure.database.repositories.workspace_repository.WorkspaceRepository",
                return_value=workspace_repo,
            ),
        ):
            from pilot_space.dependencies.auth import ensure_user_synced

            await ensure_user_synced(payload, mock_session)

        # Invitation lookup uses the placeholder email
        expected_email = f"user-{user_id}@placeholder.local"
        invitation_repo.get_pending_by_email.assert_awaited_once_with(expected_email)


class TestEnsureUserSyncedRaceCondition:
    """Tests for IntegrityError handling in ensure_user_synced (race condition fix)."""

    @pytest.mark.asyncio
    async def test_integrity_error_on_create_triggers_refetch(
        self,
        mock_session: AsyncMock,
        token_payload: TokenPayload,
    ) -> None:
        """Concurrent user creation triggers rollback + re-fetch."""
        from sqlalchemy.exc import IntegrityError

        user_repo, invitation_repo, workspace_repo = _make_mock_repos(
            user_exists=False,
        )

        # First call to get_by_id_scalar returns None (user doesn't exist)
        # create raises IntegrityError (concurrent insert)
        # Second call to get_by_id_scalar returns user (created by other request)
        user_repo.create.side_effect = IntegrityError("dup", {}, Exception())
        user_repo.get_by_id_scalar.side_effect = [None, MagicMock()]

        with (
            patch(
                "pilot_space.infrastructure.database.repositories.user_repository.UserRepository",
                return_value=user_repo,
            ),
            patch(
                "pilot_space.infrastructure.database.repositories.invitation_repository.InvitationRepository",
                return_value=invitation_repo,
            ),
            patch(
                "pilot_space.infrastructure.database.repositories.workspace_repository.WorkspaceRepository",
                return_value=workspace_repo,
            ),
        ):
            from pilot_space.dependencies.auth import ensure_user_synced

            result = await ensure_user_synced(token_payload, mock_session)

        assert result == token_payload.user_id
        mock_session.rollback.assert_awaited_once()
        assert user_repo.get_by_id_scalar.await_count == 2

    @pytest.mark.asyncio
    async def test_integrity_error_reraises_when_user_still_missing(
        self,
        mock_session: AsyncMock,
        token_payload: TokenPayload,
    ) -> None:
        """IntegrityError re-raises if re-fetch also finds no user."""
        from sqlalchemy.exc import IntegrityError

        user_repo, invitation_repo, workspace_repo = _make_mock_repos(
            user_exists=False,
        )

        user_repo.create.side_effect = IntegrityError("dup", {}, Exception())
        user_repo.get_by_id_scalar.side_effect = [None, None]

        with (
            patch(
                "pilot_space.infrastructure.database.repositories.user_repository.UserRepository",
                return_value=user_repo,
            ),
            patch(
                "pilot_space.infrastructure.database.repositories.invitation_repository.InvitationRepository",
                return_value=invitation_repo,
            ),
            patch(
                "pilot_space.infrastructure.database.repositories.workspace_repository.WorkspaceRepository",
                return_value=workspace_repo,
            ),
        ):
            from pilot_space.dependencies.auth import ensure_user_synced

            with pytest.raises(IntegrityError):
                await ensure_user_synced(token_payload, mock_session)


class TestEnsureUserSyncedPartialFailure:
    """Tests for error isolation in auto-accept invitation loop."""

    @pytest.mark.asyncio
    async def test_failed_invitation_does_not_block_others(
        self,
        mock_session: AsyncMock,
        token_payload: TokenPayload,
    ) -> None:
        """One failed invitation doesn't prevent others from being accepted."""
        ws_id_1 = uuid4()
        ws_id_2 = uuid4()
        inv_id_1 = uuid4()
        inv_id_2 = uuid4()

        invitation_1 = MagicMock(spec=WorkspaceInvitation)
        invitation_1.id = inv_id_1
        invitation_1.workspace_id = ws_id_1
        invitation_1.role = WorkspaceRole.MEMBER

        invitation_2 = MagicMock(spec=WorkspaceInvitation)
        invitation_2.id = inv_id_2
        invitation_2.workspace_id = ws_id_2
        invitation_2.role = WorkspaceRole.ADMIN

        user_repo, invitation_repo, workspace_repo = _make_mock_repos(
            user_exists=False,
            pending_invitations=[invitation_1, invitation_2],
        )

        # First add_member call raises, second succeeds
        workspace_repo.add_member.side_effect = [
            Exception("DB constraint violation"),
            None,
        ]

        with (
            patch(
                "pilot_space.infrastructure.database.repositories.user_repository.UserRepository",
                return_value=user_repo,
            ),
            patch(
                "pilot_space.infrastructure.database.repositories.invitation_repository.InvitationRepository",
                return_value=invitation_repo,
            ),
            patch(
                "pilot_space.infrastructure.database.repositories.workspace_repository.WorkspaceRepository",
                return_value=workspace_repo,
            ),
        ):
            from pilot_space.dependencies.auth import ensure_user_synced

            result = await ensure_user_synced(token_payload, mock_session)

        assert result == token_payload.user_id

        # Both invitations were attempted
        assert workspace_repo.add_member.await_count == 2

        # Only the second invitation was marked accepted
        invitation_repo.mark_accepted.assert_awaited_once_with(inv_id_2)
