"""Authentication schemas for API requests/responses.

Pydantic models for login and user profile endpoints.
OAuth callback and token refresh are handled client-side by Supabase SDK (RD-002).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field, field_validator

from pilot_space.api.v1.schemas.base import BaseSchema


class AiSettingsSchema(BaseSchema):
    """Per-user AI provider settings.

    All fields optional — omitted fields fall back to system defaults.
    base_url must be HTTPS with a public hostname (validated server-side
    in build_sdk_env_for_user to prevent SSRF).
    """

    model_sonnet: str | None = Field(
        default=None, max_length=200, description="Custom Sonnet model ID"
    )
    model_haiku: str | None = Field(
        default=None, max_length=200, description="Custom Haiku model ID"
    )
    model_opus: str | None = Field(default=None, max_length=200, description="Custom Opus model ID")
    base_url: str | None = Field(
        default=None, max_length=500, description="Custom Anthropic API base URL (HTTPS only)"
    )

    @field_validator("base_url")
    @classmethod
    def _validate_base_url(cls, v: str | None) -> str | None:
        if v is None:
            return None
        from pilot_space.ai.sdk.config import validate_base_url

        return validate_base_url(v)


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


class WorkspaceMembershipInfo(BaseSchema):
    """Compact workspace membership record for the current user.

    Attributes:
        workspace_id: The workspace this membership belongs to.
        role: The user's role in that workspace (lowercase).
    """

    workspace_id: UUID = Field(description="Workspace identifier")
    role: str = Field(description="User role in this workspace (owner/admin/member/guest)")


class UserProfileResponse(BaseSchema):
    """Current user profile response.

    Attributes:
        id: User unique identifier.
        email: User email address.
        full_name: User display name.
        avatar_url: Profile image URL.
        bio: Short bio displayed to teammates.
        created_at: Account creation timestamp.
        workspace_memberships: All workspaces the user belongs to with their role.
    """

    id: UUID = Field(description="User unique identifier")
    email: EmailStr = Field(description="User email address")
    full_name: str | None = Field(default=None, description="User display name")
    avatar_url: str | None = Field(default=None, description="Profile image URL")
    bio: str | None = Field(default=None, description="Short bio displayed to teammates")
    default_sdlc_role: str | None = Field(default=None, description="User's default SDLC role")
    ai_settings: AiSettingsSchema | None = Field(
        default=None, description="Per-user AI provider settings (model overrides, base_url)"
    )
    created_at: datetime = Field(description="Account creation timestamp")
    workspace_memberships: list[WorkspaceMembershipInfo] = Field(
        default_factory=list,
        description="All workspaces the user belongs to with their role",
    )


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
    ai_settings: AiSettingsSchema | None = Field(
        default=None, description="Per-user AI provider settings (model overrides, base_url)"
    )


__all__ = [
    "AiSettingsSchema",
    "LoginRequest",
    "TokenResponse",
    "UserProfileResponse",
    "UserProfileUpdateRequest",
    "WorkspaceMembershipInfo",
]
