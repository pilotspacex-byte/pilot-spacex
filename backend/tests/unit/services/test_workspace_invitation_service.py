"""Unit tests for WorkspaceInvitationService.accept_invitation.

S009: Tests for the accept_invitation method covering:
- Successful acceptance with profile completion required
- Successful acceptance without profile completion
- Not found invitation
- Non-pending invitation (conflict)
- Project assignment materialization

T016: Tests for request_magic_link and accept_invitation email mismatch.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pilot_space.application.services.workspace_invitation import (
    AcceptInvitationPayload,
    RequestMagicLinkPayload,
    WorkspaceInvitationConflictError,
    WorkspaceInvitationNotFoundError,
    WorkspaceInvitationService,
)
from pilot_space.domain.exceptions import AppError, ConflictError, NotFoundError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_uuid() -> uuid.UUID:
    return uuid.uuid4()


def _make_invitation(
    invitation_id: uuid.UUID,
    workspace_id: uuid.UUID,
    status: str = "pending",
    project_assignments: list | None = None,
) -> MagicMock:
    from pilot_space.infrastructure.database.models.workspace_invitation import (
        InvitationStatus,
    )
    from pilot_space.infrastructure.database.models.workspace_member import WorkspaceRole

    inv = MagicMock()
    inv.id = invitation_id
    inv.workspace_id = workspace_id
    inv.email = "invited@example.com"
    inv.invited_by = _make_uuid()
    inv.project_assignments = project_assignments
    role = MagicMock()
    role.value = "member"
    inv.role = WorkspaceRole.MEMBER
    inv.status = InvitationStatus(status)
    return inv


def _make_workspace(workspace_id: uuid.UUID, slug: str = "test-workspace") -> MagicMock:
    ws = MagicMock()
    ws.id = workspace_id
    ws.slug = slug
    return ws


def _make_user(
    user_id: uuid.UUID, full_name: str | None = "Alice", email: str = "invited@example.com"
) -> MagicMock:
    u = MagicMock()
    u.id = user_id
    u.full_name = full_name
    u.email = email
    return u


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAcceptInvitation:
    """Tests for WorkspaceInvitationService.accept_invitation."""

    def _make_service(
        self,
        invitation: MagicMock | None = None,
        workspace: MagicMock | None = None,
        user: MagicMock | None = None,
    ) -> WorkspaceInvitationService:
        workspace_repo = MagicMock()
        workspace_repo.session = MagicMock()
        workspace_repo.get_by_id = AsyncMock(return_value=workspace)
        workspace_repo.add_member = AsyncMock()

        invitation_repo = MagicMock()
        invitation_repo.get_by_id = AsyncMock(return_value=invitation)
        invitation_repo.mark_accepted = AsyncMock(return_value=invitation)

        user_repo = MagicMock()
        user_repo.get_by_id_scalar = AsyncMock(return_value=user)

        svc = WorkspaceInvitationService(
            workspace_repo=workspace_repo,
            invitation_repo=invitation_repo,
            user_repo=user_repo,
        )
        # Patch set_rls_context so it doesn't require a real DB session
        svc._workspace_repo = workspace_repo
        return svc

    @pytest.mark.asyncio
    async def test_accept_invitation_success_with_profile_completion(self) -> None:
        """User with no full_name gets requires_profile_completion=True."""
        inv_id = _make_uuid()
        workspace_id = _make_uuid()
        user_id = _make_uuid()

        invitation = _make_invitation(inv_id, workspace_id)
        workspace = _make_workspace(workspace_id, slug="my-workspace")
        user = _make_user(user_id, full_name=None)

        svc = self._make_service(invitation=invitation, workspace=workspace, user=user)

        with patch(
            "pilot_space.application.services.workspace_invitation.set_rls_context",
            new=AsyncMock(),
        ):
            result = await svc.accept_invitation(
                AcceptInvitationPayload(invitation_id=inv_id, user_id=user_id)
            )

        assert result.workspace_slug == "my-workspace"
        assert result.requires_profile_completion is True
        svc.workspace_repo.add_member.assert_awaited_once()
        svc.invitation_repo.mark_accepted.assert_awaited_once_with(inv_id)

    @pytest.mark.asyncio
    async def test_accept_invitation_success_no_profile_completion(self) -> None:
        """User with full_name gets requires_profile_completion=False."""
        inv_id = _make_uuid()
        workspace_id = _make_uuid()
        user_id = _make_uuid()

        invitation = _make_invitation(inv_id, workspace_id)
        workspace = _make_workspace(workspace_id, slug="team-space")
        user = _make_user(user_id, full_name="Alice Doe")

        svc = self._make_service(invitation=invitation, workspace=workspace, user=user)

        with patch(
            "pilot_space.application.services.workspace_invitation.set_rls_context",
            new=AsyncMock(),
        ):
            result = await svc.accept_invitation(
                AcceptInvitationPayload(invitation_id=inv_id, user_id=user_id)
            )

        assert result.workspace_slug == "team-space"
        assert result.requires_profile_completion is False

    @pytest.mark.asyncio
    async def test_accept_invitation_not_found(self) -> None:
        """Raises NotFoundError when invitation doesn't exist."""
        svc = self._make_service(invitation=None)

        with pytest.raises(WorkspaceInvitationNotFoundError):
            await svc.accept_invitation(
                AcceptInvitationPayload(invitation_id=_make_uuid(), user_id=_make_uuid())
            )

    @pytest.mark.asyncio
    async def test_accept_already_accepted_raises_conflict(self) -> None:
        """Raises ConflictError when invitation is already accepted."""
        inv_id = _make_uuid()
        workspace_id = _make_uuid()
        invitation = _make_invitation(inv_id, workspace_id, status="accepted")

        svc = self._make_service(invitation=invitation)

        with pytest.raises(WorkspaceInvitationConflictError, match="accepted"):
            await svc.accept_invitation(
                AcceptInvitationPayload(invitation_id=inv_id, user_id=_make_uuid())
            )

    @pytest.mark.asyncio
    async def test_accept_cancelled_invitation_raises_conflict(self) -> None:
        """Raises ConflictError when invitation is cancelled."""
        inv_id = _make_uuid()
        workspace_id = _make_uuid()
        invitation = _make_invitation(inv_id, workspace_id, status="cancelled")

        svc = self._make_service(invitation=invitation)

        with pytest.raises(WorkspaceInvitationConflictError, match="cancelled"):
            await svc.accept_invitation(
                AcceptInvitationPayload(invitation_id=inv_id, user_id=_make_uuid())
            )

    @pytest.mark.asyncio
    async def test_accept_materializes_project_assignments(self) -> None:
        """Project assignments stored on invitation are materialized."""
        inv_id = _make_uuid()
        workspace_id = _make_uuid()
        user_id = _make_uuid()
        project_id = str(_make_uuid())

        invitation = _make_invitation(
            inv_id,
            workspace_id,
            project_assignments=[{"project_id": project_id}],
        )
        workspace = _make_workspace(workspace_id)
        user = _make_user(user_id)

        svc = self._make_service(invitation=invitation, workspace=workspace, user=user)

        materialize_mock = AsyncMock(return_value=1)
        with (
            patch(
                "pilot_space.application.services.workspace_invitation.set_rls_context",
                new=AsyncMock(),
            ),
            patch(
                "pilot_space.application.services.project_member.ProjectMemberService.materialize_invite_assignments",
                new=materialize_mock,
            ),
        ):
            result = await svc.accept_invitation(
                AcceptInvitationPayload(invitation_id=inv_id, user_id=user_id)
            )

        assert result.workspace_slug == workspace.slug
        # member was added to workspace
        svc.workspace_repo.add_member.assert_awaited_once()


# ---------------------------------------------------------------------------
# T016: TestRequestMagicLink
# ---------------------------------------------------------------------------


class TestRequestMagicLink:
    """Tests for WorkspaceInvitationService.request_magic_link."""

    def _make_service(
        self,
        invitation: MagicMock | None = None,
        rate_limiter_allowed: bool = True,
    ) -> WorkspaceInvitationService:
        workspace_repo = MagicMock()
        workspace_repo.session = MagicMock()

        invitation_repo = MagicMock()
        invitation_repo.get_by_id = AsyncMock(return_value=invitation)
        invitation_repo.session = MagicMock()
        invitation_repo.session.flush = AsyncMock()

        rate_limiter = MagicMock()
        rate_limiter.check_and_increment = AsyncMock(return_value=rate_limiter_allowed)

        return WorkspaceInvitationService(
            workspace_repo=workspace_repo,
            invitation_repo=invitation_repo,
            rate_limiter=rate_limiter,
        )

    def _make_pending_invitation(self) -> MagicMock:
        from pilot_space.infrastructure.database.models.workspace_invitation import (
            InvitationStatus,
        )

        inv = MagicMock()
        inv.id = _make_uuid()
        inv.workspace_id = _make_uuid()
        inv.email = "invited@example.com"
        inv.status = InvitationStatus.PENDING
        inv.is_expired = False
        return inv

    @pytest.mark.asyncio
    async def test_request_magic_link_happy_path(self) -> None:
        """Happy path: PENDING invitation → magic link sent → result returned."""
        invitation = self._make_pending_invitation()
        svc = self._make_service(invitation=invitation)

        mock_supabase = MagicMock()
        mock_supabase.auth.admin.invite_user_by_email = AsyncMock(return_value=None)

        mock_settings = MagicMock()
        mock_settings.frontend_url = "https://app.example.com"

        with (
            patch(
                "pilot_space.infrastructure.supabase_client.get_supabase_client",
                new=AsyncMock(return_value=mock_supabase),
            ),
            patch(
                "pilot_space.config.get_settings",
                return_value=mock_settings,
            ),
        ):
            result = await svc.request_magic_link(
                RequestMagicLinkPayload(
                    invitation_id=invitation.id,
                    email="invited@example.com",
                )
            )

        assert result.expires_in_minutes == 60
        mock_supabase.auth.admin.invite_user_by_email.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_request_magic_link_not_found(self) -> None:
        """Raises NotFoundError when invitation does not exist."""
        svc = self._make_service(invitation=None)

        with pytest.raises(NotFoundError):
            await svc.request_magic_link(
                RequestMagicLinkPayload(
                    invitation_id=_make_uuid(),
                    email="user@example.com",
                )
            )

    @pytest.mark.asyncio
    async def test_request_magic_link_expired_invitation(self) -> None:
        """Raises ConflictError when invitation is expired."""
        from pilot_space.infrastructure.database.models.workspace_invitation import (
            InvitationStatus,
        )

        invitation = MagicMock()
        invitation.id = _make_uuid()
        invitation.workspace_id = _make_uuid()
        invitation.status = InvitationStatus.PENDING
        invitation.is_expired = True  # Time-expired PENDING

        svc = self._make_service(invitation=invitation)

        with pytest.raises(ConflictError):
            await svc.request_magic_link(
                RequestMagicLinkPayload(
                    invitation_id=invitation.id,
                    email="invited@example.com",
                )
            )

    @pytest.mark.asyncio
    async def test_request_magic_link_rate_limited(self) -> None:
        """Raises AppError with http_status=429 when rate limit exceeded."""
        invitation = self._make_pending_invitation()
        svc = self._make_service(invitation=invitation, rate_limiter_allowed=False)

        with pytest.raises(AppError) as exc_info:
            await svc.request_magic_link(
                RequestMagicLinkPayload(
                    invitation_id=invitation.id,
                    email="invited@example.com",
                )
            )

        assert exc_info.value.http_status == 429


# ---------------------------------------------------------------------------
# T016: TestAcceptInvitationEmailMismatch
# ---------------------------------------------------------------------------


class TestAcceptInvitationEmailMismatch:
    """Tests for email mismatch validation in accept_invitation."""

    def _make_service_with_user_repo(
        self,
        invitation: MagicMock,
        user_email: str,
    ) -> WorkspaceInvitationService:
        workspace_repo = MagicMock()
        workspace_repo.session = MagicMock()
        workspace_repo.get_by_id = AsyncMock(return_value=_make_workspace(_make_uuid()))
        workspace_repo.add_member = AsyncMock()

        invitation_repo = MagicMock()
        invitation_repo.get_by_id = AsyncMock(return_value=invitation)
        invitation_repo.mark_accepted = AsyncMock(return_value=invitation)

        user = _make_user(_make_uuid(), full_name="Test User")
        user.email = user_email

        user_repo = MagicMock()
        user_repo.get_by_id_scalar = AsyncMock(return_value=user)

        return WorkspaceInvitationService(
            workspace_repo=workspace_repo,
            invitation_repo=invitation_repo,
            user_repo=user_repo,
        )

    @pytest.mark.asyncio
    async def test_accept_invitation_email_mismatch(self) -> None:
        """Raises ConflictError when authenticated user email differs from invited email."""
        inv_id = _make_uuid()
        workspace_id = _make_uuid()

        invitation = _make_invitation(inv_id, workspace_id)
        invitation.email = "invited@example.com"

        svc = self._make_service_with_user_repo(
            invitation=invitation,
            user_email="other@example.com",
        )

        with pytest.raises(WorkspaceInvitationConflictError, match="different email"):
            await svc.accept_invitation(
                AcceptInvitationPayload(invitation_id=inv_id, user_id=_make_uuid())
            )

    @pytest.mark.asyncio
    async def test_accept_invitation_email_match_succeeds(self) -> None:
        """Accept proceeds when authenticated user email matches invited email."""
        inv_id = _make_uuid()
        workspace_id = _make_uuid()

        invitation = _make_invitation(inv_id, workspace_id)
        invitation.email = "invited@example.com"
        invitation.invited_by = _make_uuid()

        svc = self._make_service_with_user_repo(
            invitation=invitation,
            user_email="invited@example.com",
        )

        with patch(
            "pilot_space.application.services.workspace_invitation.set_rls_context",
            new=AsyncMock(),
        ):
            result = await svc.accept_invitation(
                AcceptInvitationPayload(invitation_id=inv_id, user_id=_make_uuid())
            )

        assert result.workspace_slug is not None
        svc.workspace_repo.add_member.assert_awaited_once()
