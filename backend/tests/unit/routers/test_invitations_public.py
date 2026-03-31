"""Unit tests for the public invitations router.

T017: Tests for unauthenticated invitation endpoints:
- GET /invitations/{invitation_id}/preview
- POST /invitations/{invitation_id}/request-magic-link

Uses direct function-call style to avoid complex DI wiring, testing that
the correct exceptions are raised. HTTP status code mapping is covered by
the global error handler (tested separately).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from pilot_space.api.v1.routers.invitations_public import (
    InvitationNotActionableError,
    preview_invitation,
    request_magic_link,
)
from pilot_space.domain.exceptions import AppError, NotFoundError
from pilot_space.infrastructure.database.models.workspace_invitation import (
    InvitationStatus,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _future() -> datetime:
    """Return a datetime 7 days in the future."""
    return datetime.now(tz=UTC) + timedelta(days=7)


def _past() -> datetime:
    """Return a datetime 7 days in the past."""
    return datetime.now(tz=UTC) - timedelta(days=7)


def _make_invitation(
    *,
    status: InvitationStatus = InvitationStatus.PENDING,
    expires_at: datetime | None = None,
    email: str = "invited@example.com",
) -> MagicMock:
    """Build a minimal invitation mock."""
    inv = MagicMock()
    inv.id = uuid4()
    inv.email = email
    inv.status = status
    inv.expires_at = expires_at or _future()
    workspace = MagicMock()
    workspace.name = "Test Workspace"
    workspace.slug = "test-workspace"
    inv.workspace = workspace
    return inv


def _make_session() -> MagicMock:
    """Return a minimal async session mock."""
    return MagicMock()


# ---------------------------------------------------------------------------
# Tests: GET /invitations/{invitation_id}/preview
# ---------------------------------------------------------------------------


class TestPreviewInvitation:
    """Tests for preview_invitation endpoint function."""

    @pytest.mark.asyncio
    async def test_preview_returns_200_with_masked_email(self) -> None:
        """PENDING invitation with future expiry → returns preview with masked email."""
        invitation = _make_invitation(email="john@example.com")
        session = _make_session()

        with patch(
            "pilot_space.api.v1.routers.invitations_public.InvitationRepository"
        ) as MockRepo:
            repo_instance = MagicMock()
            repo_instance.get_by_id = AsyncMock(return_value=invitation)
            MockRepo.return_value = repo_instance

            response = await preview_invitation(invitation_id=invitation.id, session=session)

        assert response.invitation_id == invitation.id
        assert response.workspace_name == "Test Workspace"
        assert response.workspace_slug == "test-workspace"
        # Local part is masked: j***@<domain>
        assert response.invited_email_masked.startswith("j***@")
        # Domain is preserved (split on @ to avoid CodeQL URL-sanitization false positive)
        domain = invitation.email.split("@", 1)[1]
        assert response.invited_email_masked == f"j***@{domain}"

    @pytest.mark.asyncio
    async def test_preview_returns_404_for_unknown_id(self) -> None:
        """Non-existent invitation → NotFoundError (404)."""
        session = _make_session()

        with patch(
            "pilot_space.api.v1.routers.invitations_public.InvitationRepository"
        ) as MockRepo:
            repo_instance = MagicMock()
            repo_instance.get_by_id = AsyncMock(return_value=None)
            MockRepo.return_value = repo_instance

            with pytest.raises(NotFoundError):
                await preview_invitation(invitation_id=uuid4(), session=session)

    @pytest.mark.asyncio
    async def test_preview_returns_410_for_expired_invitation(self) -> None:
        """Time-expired PENDING invitation → InvitationNotActionableError (410)."""
        invitation = _make_invitation(
            status=InvitationStatus.PENDING,
            expires_at=_past(),  # Already expired
        )
        session = _make_session()

        with patch(
            "pilot_space.api.v1.routers.invitations_public.InvitationRepository"
        ) as MockRepo:
            repo_instance = MagicMock()
            repo_instance.get_by_id = AsyncMock(return_value=invitation)
            MockRepo.return_value = repo_instance

            with pytest.raises(InvitationNotActionableError) as exc_info:
                await preview_invitation(invitation_id=invitation.id, session=session)

        assert exc_info.value.http_status == 410

    @pytest.mark.asyncio
    async def test_preview_returns_410_for_revoked_invitation(self) -> None:
        """REVOKED invitation → InvitationNotActionableError (410)."""
        invitation = _make_invitation(status=InvitationStatus.REVOKED)
        session = _make_session()

        with patch(
            "pilot_space.api.v1.routers.invitations_public.InvitationRepository"
        ) as MockRepo:
            repo_instance = MagicMock()
            repo_instance.get_by_id = AsyncMock(return_value=invitation)
            MockRepo.return_value = repo_instance

            with pytest.raises(InvitationNotActionableError):
                await preview_invitation(invitation_id=invitation.id, session=session)

    @pytest.mark.asyncio
    async def test_preview_returns_410_for_accepted_invitation(self) -> None:
        """ACCEPTED invitation → InvitationNotActionableError (410)."""
        invitation = _make_invitation(status=InvitationStatus.ACCEPTED)
        session = _make_session()

        with patch(
            "pilot_space.api.v1.routers.invitations_public.InvitationRepository"
        ) as MockRepo:
            repo_instance = MagicMock()
            repo_instance.get_by_id = AsyncMock(return_value=invitation)
            MockRepo.return_value = repo_instance

            with pytest.raises(InvitationNotActionableError):
                await preview_invitation(invitation_id=invitation.id, session=session)


# ---------------------------------------------------------------------------
# Tests: POST /invitations/{invitation_id}/request-magic-link
# ---------------------------------------------------------------------------


class TestRequestMagicLinkEndpoint:
    """Tests for request_magic_link endpoint function."""

    def _make_request(self, email: str = "invited@example.com") -> MagicMock:
        req = MagicMock()
        req.email = email
        return req

    def _make_rate_limiter(self, allowed: bool = True) -> MagicMock:
        limiter = MagicMock()
        limiter.check_and_increment = AsyncMock(return_value=allowed)
        return limiter

    @pytest.mark.asyncio
    async def test_request_magic_link_returns_200(self) -> None:
        """Valid PENDING invitation → returns confirmation message."""
        from pilot_space.application.services.workspace_invitation import (
            WorkspaceInvitationService,
        )

        session = _make_session()
        request = self._make_request()
        rate_limiter = self._make_rate_limiter(allowed=True)
        invitation_id = uuid4()

        # Patch repos (module-level imports) and the service method (class-level)
        with (
            patch("pilot_space.api.v1.routers.invitations_public.InvitationRepository"),
            patch("pilot_space.api.v1.routers.invitations_public.WorkspaceRepository"),
            patch(
                "pilot_space.infrastructure.database.repositories.user_repository.UserRepository"
            ),
            patch.object(
                WorkspaceInvitationService,
                "request_magic_link",
                new=AsyncMock(),
            ),
        ):
            response = await request_magic_link(
                invitation_id=invitation_id,
                request=request,
                session=session,
                rate_limiter=rate_limiter,
            )

        assert "magic link" in response.message.lower() or "email" in response.message.lower()
        assert response.expires_in_minutes == 60

    @pytest.mark.asyncio
    async def test_request_magic_link_returns_429_when_rate_limited(self) -> None:
        """Service raises AppError(429) → exception propagates from endpoint."""
        from pilot_space.application.services.workspace_invitation import (
            WorkspaceInvitationService,
        )

        session = _make_session()
        request = self._make_request()
        rate_limiter = self._make_rate_limiter(allowed=True)
        invitation_id = uuid4()

        class _RateLimitError(AppError):
            http_status = 429
            error_code = "rate_limit_exceeded"

        with (
            patch("pilot_space.api.v1.routers.invitations_public.InvitationRepository"),
            patch("pilot_space.api.v1.routers.invitations_public.WorkspaceRepository"),
            patch(
                "pilot_space.infrastructure.database.repositories.user_repository.UserRepository"
            ),
            patch.object(
                WorkspaceInvitationService,
                "request_magic_link",
                new=AsyncMock(side_effect=_RateLimitError("Too many requests")),
            ),
            pytest.raises(AppError) as exc_info,
        ):
            await request_magic_link(
                invitation_id=invitation_id,
                request=request,
                session=session,
                rate_limiter=rate_limiter,
            )

        assert exc_info.value.http_status == 429

    @pytest.mark.asyncio
    async def test_request_magic_link_returns_422_for_invalid_email(self) -> None:
        """Invalid email in request body → Pydantic raises ValidationError (422)."""
        from pydantic import ValidationError as PydanticValidationError

        from pilot_space.api.v1.schemas.workspace import RequestMagicLinkRequest

        with pytest.raises(PydanticValidationError):
            RequestMagicLinkRequest(email="not-a-valid-email")
