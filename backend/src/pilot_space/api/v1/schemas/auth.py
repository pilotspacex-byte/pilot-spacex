"""Authentication schemas for API requests/responses.

Pydantic models for login and user profile endpoints.
OAuth callback and token refresh are handled client-side by Supabase SDK (RD-002).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import EmailStr, Field

from pilot_space.api.v1.schemas.base import BaseSchema


class LoginRequest(BaseSchema):
    """OAuth login request (redirect to provider).

    Attributes:
        provider: OAuth provider name (google, github).
        redirect_url: URL to redirect after authentication.
    """

    provider: str = Field(
        default="google",
        description="OAuth provider (google, github)",
        pattern="^(google|github)$",
    )
    redirect_url: str | None = Field(
        default=None,
        description="URL to redirect after authentication",
    )


class TokenResponse(BaseSchema):
    """JWT token response.

    Attributes:
        access_token: JWT access token.
        token_type: Token type (always 'Bearer').
        expires_in: Token expiry in seconds.
        refresh_token: Optional refresh token.
    """

    access_token: str = Field(description="JWT access token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(description="Token expiry in seconds")
    refresh_token: str | None = Field(default=None, description="Refresh token")


class UserProfileResponse(BaseSchema):
    """Current user profile response.

    Attributes:
        id: User unique identifier.
        email: User email address.
        full_name: User display name.
        avatar_url: Profile image URL.
        bio: Short bio displayed to teammates.
        created_at: Account creation timestamp.
    """

    id: UUID = Field(description="User unique identifier")
    email: EmailStr = Field(description="User email address")
    full_name: str | None = Field(default=None, description="User display name")
    avatar_url: str | None = Field(default=None, description="Profile image URL")
    bio: str | None = Field(default=None, description="Short bio displayed to teammates")
    default_sdlc_role: str | None = Field(default=None, description="User's default SDLC role")
    ai_settings: dict[str, Any] | None = Field(
        default=None, description="Per-user AI provider settings (model overrides, base_url)"
    )
    created_at: datetime = Field(description="Account creation timestamp")


class UserProfileUpdateRequest(BaseSchema):
    """Update user profile request.

    Attributes:
        full_name: New display name.
        avatar_url: New profile image URL.
        bio: Short bio (max 200 characters).
    """

    full_name: str | None = Field(default=None, max_length=255, description="Display name")
    avatar_url: str | None = Field(default=None, max_length=2048, description="Profile image URL")
    bio: str | None = Field(default=None, max_length=200, description="Short bio (max 200 chars)")
    default_sdlc_role: str | None = Field(
        default=None, max_length=50, description="Default SDLC role"
    )
    ai_settings: dict[str, Any] | None = Field(
        default=None, description="Per-user AI provider settings (model overrides, base_url)"
    )


__all__ = [
    "LoginRequest",
    "TokenResponse",
    "UserProfileResponse",
    "UserProfileUpdateRequest",
]
