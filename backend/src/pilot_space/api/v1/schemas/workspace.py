"""Workspace schemas for API requests/responses.

Pydantic models for workspace CRUD and member management.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import EmailStr, Field

from pilot_space.api.v1.schemas.base import BaseSchema, EntitySchema


class WorkspaceCreate(BaseSchema):
    """Create workspace request.

    Attributes:
        name: Workspace display name.
        slug: URL-friendly unique identifier.
        description: Optional workspace description.
    """

    name: str = Field(
        min_length=1,
        max_length=255,
        description="Workspace display name",
    )
    slug: str = Field(
        min_length=2,
        max_length=100,
        pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$",
        description="URL-friendly identifier (lowercase letters, numbers, hyphens)",
    )
    description: str | None = Field(
        default=None,
        max_length=2000,
        description="Workspace description",
    )


class WorkspaceUpdate(BaseSchema):
    """Update workspace request.

    Attributes:
        name: New workspace name.
        description: New workspace description.
        settings: Workspace-level settings.
    """

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="New workspace name",
    )
    description: str | None = Field(
        default=None,
        max_length=2000,
        description="New description",
    )
    settings: dict[str, Any] | None = Field(
        default=None,
        description="Workspace settings (merged with existing)",
    )


class WorkspaceResponse(EntitySchema):
    """Workspace response.

    Attributes:
        name: Workspace display name.
        slug: URL-friendly identifier.
        description: Workspace description.
        owner_id: Owner user ID.
        member_count: Number of members.
        project_count: Number of projects.
    """

    name: str = Field(description="Workspace display name")
    slug: str = Field(description="URL-friendly identifier")
    description: str | None = Field(default=None, description="Workspace description")
    owner_id: UUID | None = Field(default=None, description="Owner user ID")
    member_count: int = Field(default=0, description="Number of members")
    project_count: int = Field(default=0, description="Number of projects")


class WorkspaceDetailResponse(WorkspaceResponse):
    """Detailed workspace response with settings.

    Attributes:
        settings: Workspace-level settings.
        current_user_role: Current user's role in workspace.
    """

    settings: dict[str, Any] | None = Field(default=None, description="Workspace settings")
    current_user_role: str | None = Field(default=None, description="Current user's role")


# Member management schemas
class WorkspaceMemberCreate(BaseSchema):
    """Add workspace member request.

    Attributes:
        email: User email to invite.
        role: Role to assign (admin, member, guest).
    """

    email: str = Field(description="User email to invite")
    role: str = Field(
        default="member",
        pattern="^(admin|member|guest)$",
        description="Role to assign",
    )


class WorkspaceMemberUpdate(BaseSchema):
    """Update workspace member request.

    Attributes:
        role: New role for member.
    """

    role: str = Field(
        pattern="^(owner|admin|member|guest)$",
        description="New role for member",
    )


class InvitationResponse(BaseSchema):
    """Workspace invitation response.

    Attributes:
        id: Invitation UUID.
        email: Invited email address.
        role: Intended role upon acceptance.
        status: Invitation lifecycle state.
        invited_by: Inviter user ID.
        expires_at: When the invitation expires.
        created_at: When the invitation was created.
    """

    id: UUID = Field(description="Invitation UUID")
    email: str = Field(description="Invited email address")
    role: str = Field(description="Intended role upon acceptance")
    status: str = Field(description="Invitation status (pending/accepted/expired/cancelled)")
    invited_by: UUID = Field(description="Inviter user ID")
    suggested_sdlc_role: str | None = Field(
        default=None, description="Owner's suggested SDLC role hint"
    )
    expires_at: datetime = Field(description="Invitation expiry timestamp")
    created_at: datetime = Field(description="Invitation creation timestamp")


class InvitationCreateRequest(BaseSchema):
    """Create invitation request.

    Attributes:
        email: Email address to invite.
        role: Role to assign (admin, member, guest).
    """

    email: EmailStr = Field(
        max_length=255,
        description="Email address to invite",
    )
    role: str = Field(
        default="member",
        pattern="^(admin|member|guest)$",
        description="Role to assign",
    )
    suggested_sdlc_role: str | None = Field(
        default=None,
        max_length=50,
        description="Suggested SDLC role for invitee",
    )


class WorkspaceMemberResponse(BaseSchema):
    """Workspace member response.

    Attributes:
        user_id: Member user ID.
        email: Member email.
        full_name: Member display name.
        avatar_url: Member profile image.
        role: Member role.
        joined_at: When member joined.
    """

    user_id: UUID = Field(description="Member user ID")
    email: str = Field(description="Member email")
    full_name: str | None = Field(default=None, description="Member display name")
    avatar_url: str | None = Field(default=None, description="Profile image URL")
    role: str = Field(description="Member role")
    joined_at: datetime = Field(description="When member joined")


# AI Settings schemas (T062-T064)
class ProviderStatus(BaseSchema):
    """Status of a configured AI provider.

    Attributes:
        provider: Provider name (anthropic, openai, google).
        is_configured: Whether an API key exists for this provider.
        is_valid: Whether the key has been validated (None if never validated).
        last_validated_at: Timestamp of last successful validation.
    """

    provider: str = Field(description="Provider name (anthropic, openai, google)")
    is_configured: bool = Field(description="Whether API key is configured")
    is_valid: bool | None = Field(
        default=None, description="Validation status (None if never validated)"
    )
    last_validated_at: datetime | None = Field(
        default=None, description="Last validation timestamp"
    )


class AIFeatureToggles(BaseSchema):
    """AI feature toggles for workspace.

    Attributes:
        ghost_text_enabled: Enable AI ghost text suggestions in editor.
        ai_context_enabled: Enable AI context generation for issues.
        pr_review_enabled: Enable AI PR review.
        issue_extraction_enabled: Enable AI issue extraction from notes.
        margin_annotations_enabled: Enable AI margin annotations.
        auto_approve_non_destructive: Auto-approve non-destructive AI actions.
    """

    ghost_text_enabled: bool = Field(default=True, description="Enable ghost text")
    ai_context_enabled: bool = Field(default=True, description="Enable AI context")
    pr_review_enabled: bool = Field(default=True, description="Enable PR review")
    issue_extraction_enabled: bool = Field(default=True, description="Enable issue extraction")
    margin_annotations_enabled: bool = Field(default=True, description="Enable margin annotations")
    auto_approve_non_destructive: bool = Field(
        default=True, description="Auto-approve safe AI actions"
    )


class WorkspaceAISettingsResponse(BaseSchema):
    """Response for workspace AI settings.

    Attributes:
        workspace_id: Workspace UUID.
        providers: Status of configured providers.
        features: AI feature toggles.
        default_provider: Default provider for AI operations.
        cost_limit_usd: Monthly cost limit (optional).
    """

    workspace_id: UUID = Field(description="Workspace UUID")
    providers: list[ProviderStatus] = Field(description="Provider statuses")
    features: AIFeatureToggles = Field(description="Feature toggles")
    default_provider: str = Field(default="anthropic", description="Default AI provider")
    cost_limit_usd: float | None = Field(default=None, description="Monthly cost limit USD")


class APIKeyUpdate(BaseSchema):
    """API key update for a provider.

    Attributes:
        provider: Provider name (anthropic, openai, google).
        api_key: API key to store (None to remove).
    """

    provider: str = Field(
        description="Provider name",
        pattern="^(anthropic|openai|google)$",
    )
    api_key: str | None = Field(
        default=None,
        description="API key to store (None to remove)",
        min_length=1,
    )


class WorkspaceAISettingsUpdate(BaseSchema):
    """Request to update workspace AI settings.

    Attributes:
        api_keys: List of API key updates.
        features: Feature toggle updates.
        cost_limit_usd: Monthly cost limit update.
    """

    api_keys: list[APIKeyUpdate] | None = Field(default=None, description="API key updates")
    features: AIFeatureToggles | None = Field(default=None, description="Feature toggle updates")
    cost_limit_usd: float | None = Field(default=None, description="Monthly cost limit USD", ge=0)


class KeyValidationResult(BaseSchema):
    """Result of API key validation.

    Attributes:
        provider: Provider name.
        is_valid: Whether the key is valid.
        error_message: Error message if validation failed.
    """

    provider: str = Field(description="Provider name")
    is_valid: bool = Field(description="Validation result")
    error_message: str | None = Field(default=None, description="Error message if failed")


class WorkspaceAISettingsUpdateResponse(BaseSchema):
    """Response after updating AI settings.

    Attributes:
        success: Whether all updates succeeded.
        validation_results: Validation results per provider.
        updated_providers: List of providers that were updated.
        updated_features: Whether features were updated.
    """

    success: bool = Field(description="Overall success status")
    validation_results: list[KeyValidationResult] = Field(description="Validation results")
    updated_providers: list[str] = Field(description="Updated providers")
    updated_features: bool = Field(description="Whether features were updated")


__all__ = [
    "AIFeatureToggles",
    "APIKeyUpdate",
    "InvitationCreateRequest",
    "InvitationResponse",
    "KeyValidationResult",
    "ProviderStatus",
    "WorkspaceAISettingsResponse",
    "WorkspaceAISettingsUpdate",
    "WorkspaceAISettingsUpdateResponse",
    "WorkspaceCreate",
    "WorkspaceDetailResponse",
    "WorkspaceMemberCreate",
    "WorkspaceMemberResponse",
    "WorkspaceMemberUpdate",
    "WorkspaceResponse",
    "WorkspaceUpdate",
]
