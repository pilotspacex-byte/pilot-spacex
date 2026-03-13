"""Integration tests for authentication.

T324: Auth integration tests
- Supabase auth callback handling
- Workspace membership verification
- RLS policy enforcement
- Session management
- Permission checks for each role (owner, admin, editor, viewer)

These tests verify the authentication and authorization flow
using mocked Supabase auth responses.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from fastapi import status

from pilot_space.infrastructure.auth import (
    SupabaseAuth,
    TokenExpiredError,
    TokenInvalidError,
    TokenPayload,
)
from pilot_space.infrastructure.database.models import (
    User,
    WorkspaceRole,
)

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from tests.factories import (
        UserFactory as UserFactoryType,
        WorkspaceFactory as WorkspaceFactoryType,
    )


# ============================================================================
# Supabase Auth Token Validation Tests
# ============================================================================


class TestTokenValidation:
    """Tests for JWT token validation."""

    def test_that_valid_token_is_decoded_successfully(self) -> None:
        """Test that a valid JWT token is properly decoded."""
        # Arrange
        secret = "test-secret-key-for-testing-purposes"  # pragma: allowlist secret
        auth = SupabaseAuth(jwt_secret=secret)

        # Create a valid token manually
        import jwt

        now = datetime.now(tz=UTC)
        payload = {
            "sub": str(uuid4()),
            "email": "test@example.com",
            "role": "authenticated",
            "aud": "authenticated",
            "exp": int(now.timestamp()) + 3600,
            "iat": int(now.timestamp()),
            "app_metadata": {},
            "user_metadata": {"full_name": "Test User"},
        }
        token = jwt.encode(payload, secret, algorithm="HS256")

        # Act
        result = auth.validate_token(token)

        # Assert
        assert result.email == "test@example.com"
        assert result.role == "authenticated"
        assert result.aud == "authenticated"
        assert not result.is_expired

    def test_that_expired_token_raises_error(self) -> None:
        """Test that an expired token raises TokenExpiredError."""
        # Arrange
        secret = "test-secret-key-for-testing-purposes"  # pragma: allowlist secret
        auth = SupabaseAuth(jwt_secret=secret)

        import jwt

        # Create expired token (expired 1 hour ago)
        now = datetime.now(tz=UTC)
        payload = {
            "sub": str(uuid4()),
            "email": "test@example.com",
            "role": "authenticated",
            "aud": "authenticated",
            "exp": int(now.timestamp()) - 3600,  # Expired
            "iat": int(now.timestamp()) - 7200,
        }
        token = jwt.encode(payload, secret, algorithm="HS256")

        # Act & Assert
        with pytest.raises(TokenExpiredError):
            auth.validate_token(token)

    def test_that_invalid_token_raises_error(self) -> None:
        """Test that an invalid token raises TokenInvalidError."""
        # Arrange
        auth = SupabaseAuth(jwt_secret="test-secret")

        # Act & Assert
        with pytest.raises(TokenInvalidError):
            auth.validate_token("invalid-token-string")

    def test_that_token_with_wrong_secret_raises_error(self) -> None:
        """Test that a token signed with wrong secret is rejected."""
        # Arrange
        auth = SupabaseAuth(jwt_secret="correct-secret")

        import jwt

        now = datetime.now(tz=UTC)
        payload = {
            "sub": str(uuid4()),
            "email": "test@example.com",
            "role": "authenticated",
            "aud": "authenticated",
            "exp": int(now.timestamp()) + 3600,
            "iat": int(now.timestamp()),
        }
        # Sign with wrong secret
        token = jwt.encode(payload, "wrong-secret", algorithm="HS256")

        # Act & Assert
        with pytest.raises(TokenInvalidError):
            auth.validate_token(token)

    def test_that_token_user_id_is_extracted_correctly(self) -> None:
        """Test that user ID is correctly extracted from token."""
        # Arrange
        secret = "test-secret"  # pragma: allowlist secret
        auth = SupabaseAuth(jwt_secret=secret)
        user_id = uuid4()

        import jwt

        now = datetime.now(tz=UTC)
        payload = {
            "sub": str(user_id),
            "email": "test@example.com",
            "role": "authenticated",
            "aud": "authenticated",
            "exp": int(now.timestamp()) + 3600,
            "iat": int(now.timestamp()),
        }
        token = jwt.encode(payload, secret, algorithm="HS256")

        # Act
        result = auth.get_user_id_from_token(token)

        # Assert
        assert result == user_id


# ============================================================================
# Authentication Middleware Tests
# ============================================================================


class TestAuthMiddleware:
    """Tests for authentication middleware behavior."""

    @pytest.mark.asyncio
    async def test_that_request_without_auth_header_returns_401(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that requests without Authorization header return 401."""
        # Act
        response = await client.get("/api/v1/auth/me")

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Missing Authorization header" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_that_request_with_invalid_auth_format_returns_401(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that requests with invalid auth format return 401."""
        # Act
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "InvalidFormat token"},
        )

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_that_authenticated_request_succeeds(
        self,
        app: Any,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        mock_token_payload: TokenPayload,
    ) -> None:
        """Test that authenticated requests succeed."""
        from unittest.mock import AsyncMock

        from pilot_space.api.v1.dependencies import _get_auth_service
        from pilot_space.application.services.auth import AuthService

        # Arrange - Create user in database
        user = User(
            id=mock_token_payload.user_id,
            email=mock_token_payload.email or "test@example.com",
            full_name="Test User",
        )
        db_session.add(user)
        await db_session.flush()

        # Create mock auth service that raises user not found (404 path)
        mock_service = AsyncMock(spec=AuthService)
        mock_service.get_profile.side_effect = ValueError("User not found")

        # Override auth service DI — get_current_user is already overridden by authenticated_client
        app.dependency_overrides[_get_auth_service] = lambda: mock_service
        try:
            # Act
            response = await authenticated_client.get("/api/v1/auth/me")
        finally:
            app.dependency_overrides.pop(_get_auth_service, None)

        # Assert - 404 because mock service raises user not found
        # The point is it doesn't return 401 (auth passed)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]


# ============================================================================
# Workspace Membership Verification Tests
# ============================================================================


class TestWorkspaceMembership:
    """Tests for workspace membership verification."""

    def test_that_owner_role_has_full_permissions(
        self,
        user_factory: type[UserFactoryType],
        workspace_factory: type[WorkspaceFactoryType],
    ) -> None:
        """Test that owner role has full workspace permissions."""
        # Arrange
        from tests.factories import WorkspaceMemberFactory

        user = user_factory()
        workspace = workspace_factory(owner_id=user.id, owner=user)
        membership = WorkspaceMemberFactory(
            user=user,
            workspace=workspace,
            role=WorkspaceRole.OWNER,
        )

        # Assert
        assert membership.is_owner is True
        assert membership.is_admin is True
        assert membership.can_edit is True

    def test_that_admin_role_has_admin_permissions(
        self,
        user_factory: type[UserFactoryType],
        workspace_factory: type[WorkspaceFactoryType],
    ) -> None:
        """Test that admin role has admin but not owner permissions."""
        # Arrange
        from tests.factories import WorkspaceMemberFactory

        user = user_factory()
        workspace = workspace_factory()
        membership = WorkspaceMemberFactory(
            user=user,
            workspace=workspace,
            role=WorkspaceRole.ADMIN,
        )

        # Assert
        assert membership.is_owner is False
        assert membership.is_admin is True
        assert membership.can_edit is True

    def test_that_member_role_can_edit(
        self,
        user_factory: type[UserFactoryType],
        workspace_factory: type[WorkspaceFactoryType],
    ) -> None:
        """Test that member role can edit content."""
        # Arrange
        from tests.factories import WorkspaceMemberFactory

        user = user_factory()
        workspace = workspace_factory()
        membership = WorkspaceMemberFactory(
            user=user,
            workspace=workspace,
            role=WorkspaceRole.MEMBER,
        )

        # Assert
        assert membership.is_owner is False
        assert membership.is_admin is False
        assert membership.can_edit is True

    def test_that_guest_role_is_read_only(
        self,
        user_factory: type[UserFactoryType],
        workspace_factory: type[WorkspaceFactoryType],
    ) -> None:
        """Test that guest role has read-only access."""
        # Arrange
        from tests.factories import WorkspaceMemberFactory

        user = user_factory()
        workspace = workspace_factory()
        membership = WorkspaceMemberFactory(
            user=user,
            workspace=workspace,
            role=WorkspaceRole.GUEST,
        )

        # Assert
        assert membership.is_owner is False
        assert membership.is_admin is False
        assert membership.can_edit is False


# ============================================================================
# RLS Policy Tests
# ============================================================================


class TestRLSPolicies:
    """Tests for Row-Level Security policy enforcement.

    Note: These tests verify the RLS policy logic at the application level.
    Full RLS testing requires PostgreSQL with RLS policies enabled.
    """

    def test_that_workspace_access_requires_valid_token(self) -> None:
        """Test that workspace access verification requires valid token."""
        # Arrange
        auth = SupabaseAuth(jwt_secret="test-secret")
        workspace_id = uuid4()

        # Act
        result = auth.verify_workspace_access("invalid-token", workspace_id)

        # Assert
        assert result is False

    def test_that_workspace_access_succeeds_with_valid_token(self) -> None:
        """Test that workspace access succeeds with valid token."""
        # Arrange
        secret = "test-secret"  # pragma: allowlist secret
        auth = SupabaseAuth(jwt_secret=secret)
        workspace_id = uuid4()

        import jwt

        now = datetime.now(tz=UTC)
        payload = {
            "sub": str(uuid4()),
            "email": "test@example.com",
            "role": "authenticated",
            "aud": "authenticated",
            "exp": int(now.timestamp()) + 3600,
            "iat": int(now.timestamp()),
        }
        token = jwt.encode(payload, secret, algorithm="HS256")

        # Act
        result = auth.verify_workspace_access(token, workspace_id)

        # Assert
        assert result is True


# ============================================================================
# Session Management Tests
# ============================================================================


class TestSessionManagement:
    """Tests for session management."""

    def test_that_token_payload_expiration_is_calculated_correctly(
        self,
        mock_token_payload: TokenPayload,
    ) -> None:
        """Test that token expiration is calculated correctly."""
        # Assert
        assert not mock_token_payload.is_expired
        assert mock_token_payload.expiration_datetime > datetime.now(tz=UTC)

    def test_that_expired_token_payload_is_detected(self) -> None:
        """Test that expired token payload is detected."""
        # Arrange
        now = datetime.now(tz=UTC)
        payload = TokenPayload(
            sub=str(uuid4()),
            email="test@example.com",
            role="authenticated",
            aud="authenticated",
            exp=int(now.timestamp()) - 3600,  # Expired
            iat=int(now.timestamp()) - 7200,
            app_metadata={},
            user_metadata={},
        )

        # Assert
        assert payload.is_expired is True

    @pytest.mark.asyncio
    async def test_that_logout_returns_success(
        self,
        app: Any,
        authenticated_client: AsyncClient,
        mock_token_payload: TokenPayload,
    ) -> None:
        """Test that logout endpoint returns success."""
        from unittest.mock import AsyncMock

        from pilot_space.api.v1.dependencies import _get_auth_service
        from pilot_space.application.services.auth import AuthService

        # Create mock auth service
        mock_service = AsyncMock(spec=AuthService)
        mock_service.logout.return_value = None

        # Override auth service DI — get_current_user already overridden by authenticated_client
        app.dependency_overrides[_get_auth_service] = lambda: mock_service
        try:
            # Act
            response = await authenticated_client.post("/api/v1/auth/logout")
        finally:
            app.dependency_overrides.pop(_get_auth_service, None)

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "Logged out successfully"


# ============================================================================
# Permission Check Tests
# ============================================================================


class TestPermissionChecks:
    """Tests for permission checks across different roles."""

    @pytest.fixture
    def workspace_with_roles(
        self,
        user_factory: type[UserFactoryType],
        workspace_factory: type[WorkspaceFactoryType],
    ) -> dict[str, Any]:
        """Create workspace with users in different roles.

        Returns:
            Dictionary with workspace and users for each role.
        """
        from tests.factories import WorkspaceMemberFactory

        owner = user_factory()
        workspace = workspace_factory(owner_id=owner.id, owner=owner)

        admin = user_factory()
        member = user_factory()
        guest = user_factory()

        return {
            "workspace": workspace,
            "owner": {
                "user": owner,
                "membership": WorkspaceMemberFactory(
                    user=owner,
                    workspace=workspace,
                    role=WorkspaceRole.OWNER,
                ),
            },
            "admin": {
                "user": admin,
                "membership": WorkspaceMemberFactory(
                    user=admin,
                    workspace=workspace,
                    role=WorkspaceRole.ADMIN,
                ),
            },
            "member": {
                "user": member,
                "membership": WorkspaceMemberFactory(
                    user=member,
                    workspace=workspace,
                    role=WorkspaceRole.MEMBER,
                ),
            },
            "guest": {
                "user": guest,
                "membership": WorkspaceMemberFactory(
                    user=guest,
                    workspace=workspace,
                    role=WorkspaceRole.GUEST,
                ),
            },
        }

    def test_that_owner_can_delete_workspace(
        self,
        workspace_with_roles: dict[str, Any],
    ) -> None:
        """Test that owner has delete workspace permission."""
        # Arrange
        owner_membership = workspace_with_roles["owner"]["membership"]

        # Assert - Owner should have full control
        assert owner_membership.role == WorkspaceRole.OWNER
        assert owner_membership.is_owner is True

    def test_that_admin_cannot_delete_workspace(
        self,
        workspace_with_roles: dict[str, Any],
    ) -> None:
        """Test that admin cannot delete workspace."""
        # Arrange
        admin_membership = workspace_with_roles["admin"]["membership"]

        # Assert - Admin should not be owner
        assert admin_membership.role == WorkspaceRole.ADMIN
        assert admin_membership.is_owner is False

    def test_that_admin_can_manage_members(
        self,
        workspace_with_roles: dict[str, Any],
    ) -> None:
        """Test that admin can manage workspace members."""
        # Arrange
        admin_membership = workspace_with_roles["admin"]["membership"]

        # Assert - Admin has admin privileges
        assert admin_membership.is_admin is True

    def test_that_member_cannot_manage_members(
        self,
        workspace_with_roles: dict[str, Any],
    ) -> None:
        """Test that member cannot manage workspace members."""
        # Arrange
        member_membership = workspace_with_roles["member"]["membership"]

        # Assert - Member is not admin
        assert member_membership.is_admin is False

    def test_that_member_can_create_content(
        self,
        workspace_with_roles: dict[str, Any],
    ) -> None:
        """Test that member can create content."""
        # Arrange
        member_membership = workspace_with_roles["member"]["membership"]

        # Assert - Member can edit
        assert member_membership.can_edit is True

    def test_that_guest_cannot_create_content(
        self,
        workspace_with_roles: dict[str, Any],
    ) -> None:
        """Test that guest cannot create content."""
        # Arrange
        guest_membership = workspace_with_roles["guest"]["membership"]

        # Assert - Guest cannot edit
        assert guest_membership.can_edit is False

    def test_that_role_hierarchy_is_correct(
        self,
        workspace_with_roles: dict[str, Any],
    ) -> None:
        """Test that role hierarchy is owner > admin > member > guest."""
        # Arrange
        owner = workspace_with_roles["owner"]["membership"]
        admin = workspace_with_roles["admin"]["membership"]
        member = workspace_with_roles["member"]["membership"]
        guest = workspace_with_roles["guest"]["membership"]

        # Assert hierarchy
        # Owner has all permissions
        assert owner.is_owner
        assert owner.is_admin
        assert owner.can_edit

        # Admin has admin and edit, not owner
        assert not admin.is_owner
        assert admin.is_admin
        assert admin.can_edit

        # Member has edit only
        assert not member.is_owner
        assert not member.is_admin
        assert member.can_edit

        # Guest has no permissions
        assert not guest.is_owner
        assert not guest.is_admin
        assert not guest.can_edit


# ============================================================================
# Token Payload Property Tests
# ============================================================================


class TestTokenPayloadProperties:
    """Tests for TokenPayload property accessors."""

    def test_that_user_id_returns_uuid(
        self,
        mock_token_payload: TokenPayload,
    ) -> None:
        """Test that user_id property returns UUID."""
        # Act
        user_id = mock_token_payload.user_id

        # Assert
        assert isinstance(user_id, UUID)

    def test_that_expiration_datetime_returns_datetime(
        self,
        mock_token_payload: TokenPayload,
    ) -> None:
        """Test that expiration_datetime returns datetime."""
        # Act
        exp_dt = mock_token_payload.expiration_datetime

        # Assert
        assert isinstance(exp_dt, datetime)
        assert exp_dt.tzinfo is not None  # Timezone aware


__all__ = [
    "TestAuthMiddleware",
    "TestPermissionChecks",
    "TestRLSPolicies",
    "TestSessionManagement",
    "TestTokenPayloadProperties",
    "TestTokenValidation",
    "TestWorkspaceMembership",
]
