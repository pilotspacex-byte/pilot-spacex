"""Unit tests for AuthService."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from pilot_space.application.services.auth import (
    AuthService,
    GetLoginUrlPayload,
    GetProfilePayload,
    LogoutPayload,
    UpdateProfilePayload,
)
from pilot_space.domain.exceptions import NotFoundError


@pytest.fixture
def user_repo() -> AsyncMock:
    """Mock user repository."""
    return AsyncMock()


@pytest.fixture
def auth_service(user_repo: AsyncMock) -> AuthService:
    """Auth service with mocked dependencies."""
    return AuthService(
        user_repo=user_repo,
        supabase_url="https://test.supabase.co",
        default_redirect_origin="http://localhost:3000",
    )


def _make_user(**overrides: object) -> SimpleNamespace:
    """Create a fake user object for testing."""
    defaults = {
        "id": uuid.uuid4(),
        "email": "test@example.com",
        "full_name": "Test User",
        "avatar_url": None,
        "default_sdlc_role": None,
        "created_at": "2025-01-01T00:00:00Z",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class TestGetLoginUrl:
    """Tests for AuthService.get_login_url."""

    @pytest.mark.asyncio
    async def test_builds_url_with_provider(
        self,
        auth_service: AuthService,
    ) -> None:
        """Should construct OAuth URL with specified provider."""
        result = await auth_service.get_login_url(
            GetLoginUrlPayload(provider="google"),
        )

        assert result.provider == "google"
        assert "provider=google" in result.url
        assert result.url.startswith("https://test.supabase.co/auth/v1/authorize")

    @pytest.mark.asyncio
    async def test_uses_custom_redirect(
        self,
        auth_service: AuthService,
    ) -> None:
        """Should use provided redirect URL when specified."""
        result = await auth_service.get_login_url(
            GetLoginUrlPayload(
                provider="github",
                redirect_url="https://custom.example.com/callback",
            ),
        )

        assert "redirect_to=https://custom.example.com/callback" in result.url
        assert result.provider == "github"

    @pytest.mark.asyncio
    async def test_uses_default_redirect(
        self,
        auth_service: AuthService,
    ) -> None:
        """Should use default redirect origin when no redirect_url provided."""
        result = await auth_service.get_login_url(
            GetLoginUrlPayload(provider="google"),
        )

        assert "redirect_to=http://localhost:3000/auth/callback" in result.url


class TestGetProfile:
    """Tests for AuthService.get_profile."""

    @pytest.mark.asyncio
    async def test_returns_user(
        self,
        auth_service: AuthService,
        user_repo: AsyncMock,
    ) -> None:
        """Should return user when found."""
        user = _make_user()
        user_repo.get_by_id.return_value = user

        result = await auth_service.get_profile(
            GetProfilePayload(user_id=user.id),
        )

        assert result.user is user
        user_repo.get_by_id.assert_awaited_once_with(user.id)

    @pytest.mark.asyncio
    async def test_raises_when_not_found(
        self,
        auth_service: AuthService,
        user_repo: AsyncMock,
    ) -> None:
        """Should raise ValueError when user not found."""
        user_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundError, match="User not found"):
            await auth_service.get_profile(
                GetProfilePayload(user_id=uuid.uuid4()),
            )


class TestUpdateProfile:
    """Tests for AuthService.update_profile."""

    @pytest.mark.asyncio
    async def test_updates_provided_fields(
        self,
        auth_service: AuthService,
        user_repo: AsyncMock,
    ) -> None:
        """Should update only the fields that are provided."""
        user = _make_user()
        user_repo.get_by_id.return_value = user
        user_repo.update.return_value = user

        result = await auth_service.update_profile(
            UpdateProfilePayload(
                user_id=user.id,
                full_name="New Name",
                default_sdlc_role="developer",
            ),
        )

        assert "full_name" in result.changed_fields
        assert "default_sdlc_role" in result.changed_fields
        assert "avatar_url" not in result.changed_fields
        user_repo.update.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_skips_update_when_no_fields(
        self,
        auth_service: AuthService,
        user_repo: AsyncMock,
    ) -> None:
        """Should not call repo.update when no fields changed."""
        user = _make_user()
        user_repo.get_by_id.return_value = user

        result = await auth_service.update_profile(
            UpdateProfilePayload(user_id=user.id),
        )

        assert result.changed_fields == []
        user_repo.update.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_raises_when_not_found(
        self,
        auth_service: AuthService,
        user_repo: AsyncMock,
    ) -> None:
        """Should raise ValueError when user not found."""
        user_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundError, match="User not found"):
            await auth_service.update_profile(
                UpdateProfilePayload(
                    user_id=uuid.uuid4(),
                    full_name="Name",
                ),
            )


class TestLogout:
    """Tests for AuthService.logout."""

    @pytest.mark.asyncio
    async def test_returns_success(
        self,
        auth_service: AuthService,
    ) -> None:
        """Should return success=True (JWT logout is a no-op)."""
        result = await auth_service.logout(
            LogoutPayload(user_id=uuid.uuid4()),
        )

        assert result.success is True
