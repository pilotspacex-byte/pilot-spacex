"""Workspace schemas for API requests/responses.

Pydantic models for workspace CRUD and member management.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import EmailStr, Field, field_validator, model_validator

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
        slug: New URL-friendly identifier. Must be globally unique.
        description: New workspace description.
        settings: Workspace-level settings.
    """

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="New workspace name",
    )
    slug: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
        pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$",
        description="New URL-friendly identifier (lowercase letters, numbers, hyphens)",
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
        role: Role to assign (owner, admin, member, guest).
    """

    email: str = Field(description="User email to invite")
    role: str = Field(
        default="MEMBER",
        pattern="^(OWNER|ADMIN|MEMBER|GUEST)$",
        description="Role to assign",
    )


class WorkspaceMemberUpdate(BaseSchema):
    """Update workspace member request.

    Attributes:
        role: New role for member.
    """

    role: str = Field(description="New role for member")

    @field_validator("role", mode="before")
    @classmethod
    def normalise_role(cls, v: str) -> str:
        """Normalise role string to uppercase; reject unknown values."""
        upper = str(v).upper()
        if upper not in ("OWNER", "ADMIN", "MEMBER", "GUEST"):
            raise ValueError(f"Invalid role: {v!r}")
        return upper


class WorkspaceMemberAvailabilityUpdate(BaseSchema):
    """Update workspace member weekly availability (T-246).

    Attributes:
        weekly_available_hours: Hours available per week (0-168).
    """

    weekly_available_hours: float = Field(
        ge=0,
        le=168,
        description="Hours available per week for capacity planning (0-168)",
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
    invited_by_name: str | None = Field(default=None, description="Inviter display name")
    suggested_sdlc_role: str | None = Field(
        default=None, description="Owner's suggested SDLC role hint"
    )
    email_sent: bool = Field(default=True, description="Whether the invitation email was delivered")
    expires_at: datetime = Field(description="Invitation expiry timestamp")
    created_at: datetime = Field(description="Invitation creation timestamp")


class InvitationPreviewResponse(BaseSchema):
    """Public preview of an invitation (no auth required).

    Returns enough information for the /invite page to render the
    workspace name and detect already-used/expired invitations.

    Attributes:
        invitation_id: Invitation UUID.
        status: Current invitation status.
        workspace_name: Display name of the workspace being joined.
        workspace_slug: Workspace URL slug (used for post-accept redirect).
        invited_email_masked: Email with local-part masked (e.g. j***@example.com).
        expires_at: When the invitation expires.
    """

    invitation_id: UUID = Field(description="Invitation UUID")
    status: str = Field(
        description="Invitation status (pending/accepted/expired/revoked/cancelled)"
    )
    workspace_name: str = Field(description="Display name of the workspace")
    workspace_slug: str = Field(description="Workspace URL slug")
    invited_email_masked: str = Field(description="Email with local-part masked")
    expires_at: datetime = Field(description="Invitation expiry timestamp")


class RequestMagicLinkRequest(BaseSchema):
    """Request to send a magic link for an invitation.

    Attributes:
        email: The email address that should receive the magic link.
               Must match the invited email address.
    """

    email: EmailStr = Field(description="Email address to send the magic link to")


class RequestMagicLinkResponse(BaseSchema):
    """Response after requesting a magic link.

    Attributes:
        message: Human-readable confirmation message.
        expires_in_minutes: How long the magic link is valid for.
    """

    message: str = Field(description="Confirmation message")
    expires_in_minutes: int = Field(description="Magic link validity in minutes")


class InvitationPublicDetailResponse(BaseSchema):
    """Public-facing invitation details (no auth required).

    Attributes:
        id: Invitation UUID.
        workspace_name: Workspace display name.
        workspace_slug: Workspace URL slug.
        inviter_name: Name of the person who sent the invitation.
        role: Intended role upon acceptance.
        email_masked: Masked email (e.g. t***@example.com).
        status: Invitation status.
        expires_at: When the invitation expires.
    """

    id: UUID = Field(description="Invitation UUID")
    workspace_name: str = Field(description="Workspace display name")
    workspace_slug: str = Field(description="Workspace URL slug")
    inviter_name: str | None = Field(default=None, description="Inviter display name")
    role: str = Field(description="Intended role upon acceptance")
    email_masked: str = Field(description="Masked email address")
    status: str = Field(description="Invitation status")
    expires_at: datetime = Field(description="Invitation expiry timestamp")


class InvitationAcceptResponse(BaseSchema):
    """Response after accepting an invitation.

    Attributes:
        workspace_slug: Workspace slug for redirect.
        workspace_name: Workspace display name.
        role: Role assigned to the new member.
    """

    workspace_slug: str = Field(description="Workspace slug for redirect")
    workspace_name: str = Field(description="Workspace display name")
    role: str = Field(description="Assigned role")


class InvitationCreateRequest(BaseSchema):
    """Create invitation request.

    Attributes:
        email: Email address to invite.
        role: Role to assign (admin, member, guest).
        project_assignments: Required project assignments for new member (FR-03).
    """

    email: EmailStr = Field(
        max_length=255,
        description="Email address to invite",
    )
    role: str = Field(
        default="MEMBER",
        pattern="^(ADMIN|MEMBER|GUEST)$",
        description="Role to assign",
    )
    suggested_sdlc_role: str | None = Field(
        default=None,
        max_length=50,
        description="Suggested SDLC role for invitee",
    )
    project_assignments: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Project assignments: [{project_id, role}]. Optional — member starts with no project assignment if omitted (FR-03-3, Amendment 1).",
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
        projects: Project chips for the member (RBAC — FR-02).
    """

    user_id: UUID = Field(description="Member user ID")
    email: str = Field(description="Member email")
    full_name: str | None = Field(default=None, description="Member display name")
    avatar_url: str | None = Field(default=None, description="Profile image URL")
    role: str = Field(description="Member role")
    joined_at: datetime = Field(description="When member joined")
    weekly_available_hours: float = Field(
        default=40.0,
        description="Hours available per week for capacity planning",
    )
    projects: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Project chips (id, name, identifier, is_archived) for FR-02",
    )


class PaginatedMembersResponse(BaseSchema):
    """Paginated workspace member list response (E-05)."""

    items: list[WorkspaceMemberResponse]
    total: int = Field(ge=0, description="Total matching member count")
    page: int = Field(ge=1, description="Current page (1-indexed)")
    page_size: int = Field(ge=1, description="Items per page")
    total_pages: int = Field(ge=0, description="Total number of pages")


class PaginatedInvitationsResponse(BaseSchema):
    """Paginated workspace invitations list response (E-05)."""

    items: list[InvitationResponse]
    total: int = Field(ge=0, description="Total pending invitation count")
    page: int = Field(ge=1, description="Current page (1-indexed)")
    page_size: int = Field(ge=1, description="Items per page")
    total_pages: int = Field(ge=0, description="Total number of pages")


class MemberContributionStats(BaseSchema):
    """Contribution metrics for a workspace member.

    Attributes:
        issues_created: Count of issues where member is reporter.
        issues_assigned: Count of issues where member is assignee.
        cycle_velocity: Average issues closed per sprint (last 3 completed cycles).
        capacity_utilization_pct: committed_hours / weekly_available_hours * 100, clamped [0, 100].
        pr_commit_links_count: Count of PR/commit integration links on member's issues.
    """

    issues_created: int = Field(description="Issues reported by this member")
    issues_assigned: int = Field(description="Issues assigned to this member")
    cycle_velocity: float = Field(description="Avg issues closed per sprint (last 3 cycles)")
    capacity_utilization_pct: float = Field(
        description="Committed hours / available hours × 100, clamped to [0, 100]"
    )
    pr_commit_links_count: int = Field(description="PR/commit links on member's issues")


class MemberProfileResponse(WorkspaceMemberResponse):
    """Full member profile with contribution stats.

    Extends WorkspaceMemberResponse with aggregated contribution metrics.
    """

    stats: MemberContributionStats = Field(description="Contribution metrics")


class MemberActivityItem(BaseSchema):
    """Single activity event from the member's timeline.

    Attributes:
        id: Activity UUID.
        activity_type: Type of activity (state_change, comment, field_update, etc.).
        field: Field that changed (for field_update type).
        old_value: Previous value.
        new_value: New value.
        comment: Comment body (for comment type).
        created_at: When this activity occurred.
        issue_id: Related issue UUID.
        issue_identifier: Human-readable issue identifier (e.g., "PS-42").
        issue_title: Issue title for display.
    """

    id: UUID = Field(description="Activity UUID")
    activity_type: str = Field(description="Activity type")
    field: str | None = Field(default=None, description="Changed field name")
    old_value: str | None = Field(default=None, description="Previous value")
    new_value: str | None = Field(default=None, description="New value")
    comment: str | None = Field(default=None, description="Comment body")
    created_at: datetime = Field(description="Activity timestamp")
    issue_id: UUID | None = Field(default=None, description="Related issue UUID")
    issue_identifier: str | None = Field(default=None, description="Issue identifier e.g. PS-42")
    issue_title: str | None = Field(default=None, description="Issue title")


class MemberActivityResponse(BaseSchema):
    """Paginated member activity response.

    Attributes:
        items: Activity items for current page.
        total: Total activity count.
        page: Current page (1-indexed).
        page_size: Items per page.
    """

    items: list[MemberActivityItem] = Field(description="Activity items")
    total: int = Field(description="Total count")
    page: int = Field(description="Current page (1-indexed)")
    page_size: int = Field(description="Items per page")


# AI Settings schemas (T062-T064)
class ProviderStatus(BaseSchema):
    """Status of a configured AI provider.

    Attributes:
        provider: Provider name (google, anthropic, ollama).
        service_type: Service category ('embedding' or 'llm').
        is_configured: Whether the provider is configured for this service.
        is_valid: Whether the key has been validated (None if never validated).
        last_validated_at: Timestamp of last successful validation.
        base_url: Custom base URL for provider API (if configured).
        model_name: Default model name override (if configured).
    """

    provider: str = Field(description="Provider name")
    service_type: str = Field(description="Service category: 'embedding', 'llm', or 'stt'")
    is_configured: bool = Field(description="Whether provider is configured for this service")
    is_valid: bool | None = Field(
        default=None, description="Validation status (None if never validated)"
    )
    last_validated_at: datetime | None = Field(
        default=None, description="Last validation timestamp"
    )
    base_url: str | None = Field(default=None, description="Custom base URL for provider API")
    model_name: str | None = Field(default=None, description="Default model name override")


class WorkspaceFeatureToggles(BaseSchema):
    """Workspace-level sidebar feature toggles.

    Controls which sidebar modules are visible and accessible
    to all members of the workspace. Stored in workspace.settings["feature_toggles"].

    Attributes:
        notes: Whether the Notes module is visible in the sidebar.
        issues: Whether the Issues module is visible in the sidebar.
        projects: Whether the Projects module is visible in the sidebar.
        members: Whether the Members module is visible in the sidebar.
        docs: Whether the Docs module is visible in the sidebar.
        knowledge: Whether the Knowledge Graph module is visible in the sidebar.
        skills: Whether the AI Skills module is visible in the sidebar.
        costs: Whether the AI Costs module is visible in the sidebar.
        approvals: Whether the AI Approvals module is visible in the sidebar.
    """

    notes: bool = Field(default=True, description="Notes module enabled")
    issues: bool = Field(default=True, description="Issue tracker module enabled")
    projects: bool = Field(default=True, description="Project management module enabled")
    members: bool = Field(default=True, description="Member directory module enabled")
    docs: bool = Field(default=True, description="Documentation module enabled")
    knowledge: bool = Field(default=True, description="Knowledge Graph module enabled")
    skills: bool = Field(default=True, description="AI Skills module enabled")
    costs: bool = Field(default=True, description="AI cost tracking module enabled")
    approvals: bool = Field(default=True, description="AI approval workflow module enabled")


class WorkspaceFeatureTogglesUpdate(BaseSchema):
    """Partial update for workspace feature toggles.

    Only provided fields are updated; omitted fields remain unchanged.
    """

    notes: bool | None = Field(default=None, description="Notes module enabled")
    issues: bool | None = Field(default=None, description="Issue tracker module enabled")
    projects: bool | None = Field(default=None, description="Project management module enabled")
    members: bool | None = Field(default=None, description="Member directory module enabled")
    docs: bool | None = Field(default=None, description="Documentation module enabled")
    knowledge: bool | None = Field(default=None, description="Knowledge Graph module enabled")
    skills: bool | None = Field(default=None, description="AI Skills module enabled")
    costs: bool | None = Field(default=None, description="AI cost tracking module enabled")
    approvals: bool | None = Field(default=None, description="AI approval workflow module enabled")


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
    default_llm_provider: str = Field(
        default="anthropic", description="Active LLM provider for this workspace"
    )
    default_embedding_provider: str = Field(
        default="google", description="Active embedding provider for this workspace"
    )
    cost_limit_usd: float | None = Field(default=None, description="Monthly cost limit USD")


class APIKeyUpdate(BaseSchema):
    """API key update for a provider.

    Attributes:
        provider: Provider name (google, anthropic, ollama).
        service_type: Service category ('embedding' or 'llm').
        api_key: API key to store (optional for ollama).
        base_url: Custom base URL for provider API (required for ollama).
        model_name: Default model name override.
    """

    provider: str = Field(
        description="Provider name",
        pattern="^(google|anthropic|ollama|elevenlabs)$",
    )
    service_type: str = Field(
        description="Service category",
        pattern="^(embedding|llm|stt)$",
    )
    api_key: str | None = Field(
        default=None,
        description="API key to store (None to keep existing, optional for Ollama)",
        min_length=1,
    )
    base_url: str | None = Field(
        default=None,
        description="Custom base URL for provider API",
        max_length=2048,
        pattern=r"^https?://[^\s/]+(/[^\s]*)?$",
    )
    model_name: str | None = Field(
        default=None,
        description="Default model name override",
        max_length=200,
    )

    @model_validator(mode="after")
    def check_provider_service_combo(self) -> APIKeyUpdate:
        """Validate that provider + service_type is a supported combination."""
        from pilot_space.ai.providers.constants import VALID_PROVIDER_SERVICES

        allowed = VALID_PROVIDER_SERVICES.get(self.provider)
        if allowed is not None and self.service_type not in allowed:
            msg = (
                f"Invalid combination: {self.provider} does not support "
                f"service_type '{self.service_type}'. "
                f"Allowed: {', '.join(sorted(allowed))}"
            )
            raise ValueError(msg)
        return self


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
    default_llm_provider: str | None = Field(
        default=None,
        description="Set active LLM provider",
        pattern="^(anthropic|ollama)$",
    )
    default_embedding_provider: str | None = Field(
        default=None,
        description="Set active embedding provider",
        pattern="^(google|ollama)$",
    )


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
    "InvitationAcceptResponse",
    "InvitationCreateRequest",
    "InvitationPreviewResponse",
    "InvitationPublicDetailResponse",
    "InvitationResponse",
    "KeyValidationResult",
    "MemberActivityItem",
    "MemberActivityResponse",
    "MemberContributionStats",
    "MemberProfileResponse",
    "PaginatedInvitationsResponse",
    "PaginatedMembersResponse",
    "ProviderStatus",
    "RequestMagicLinkRequest",
    "RequestMagicLinkResponse",
    "WorkspaceAISettingsResponse",
    "WorkspaceAISettingsUpdate",
    "WorkspaceAISettingsUpdateResponse",
    "WorkspaceCreate",
    "WorkspaceDetailResponse",
    "WorkspaceFeatureToggles",
    "WorkspaceFeatureTogglesUpdate",
    "WorkspaceMemberAvailabilityUpdate",
    "WorkspaceMemberCreate",
    "WorkspaceMemberResponse",
    "WorkspaceMemberUpdate",
    "WorkspaceResponse",
    "WorkspaceUpdate",
]
