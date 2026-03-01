"""Integration API schemas.

T185: Create Integration Pydantic schemas for API layer.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from pilot_space.infrastructure.database.models import (
    IntegrationLinkType,
    IntegrationProvider,
)

__all__: list[str] = []  # Defined at end of file


# ============================================================================
# Request Schemas
# ============================================================================


class GitHubOAuthCallbackRequest(BaseModel):
    """Request from GitHub OAuth callback."""

    code: str = Field(..., description="OAuth authorization code")
    state: str | None = Field(None, description="CSRF state parameter")


class LinkCommitRequest(BaseModel):
    """Request to link a commit to an issue."""

    repository: str = Field(..., pattern=r"^[^/]+/[^/]+$", description="owner/repo")
    commit_sha: str = Field(..., min_length=7, max_length=40)


class LinkPullRequestRequest(BaseModel):
    """Request to link a PR to an issue."""

    repository: str = Field(..., pattern=r"^[^/]+/[^/]+$", description="owner/repo")
    pr_number: int = Field(..., ge=1)


class CreateBranchRequest(BaseModel):
    """Request to create a GitHub branch linked to an issue."""

    repository: str = Field(
        ..., pattern=r"^[^/]+/[^/]+$", description="Repository full name (owner/repo)"
    )
    branch_name: str = Field(..., min_length=1, max_length=100)
    base_branch: str = Field(default="main", max_length=100)


class BranchNameResponse(BaseModel):
    """Suggested branch name derived from issue identifier and title."""

    branch_name: str
    git_command: str
    format: str


class SetupWebhookRequest(BaseModel):
    """Request to setup webhook for a repository."""

    repository: str = Field(..., pattern=r"^[^/]+/[^/]+$", description="owner/repo")


# ============================================================================
# Response Schemas
# ============================================================================


class IntegrationResponse(BaseModel):
    """Full integration response."""

    id: UUID
    workspace_id: UUID
    provider: IntegrationProvider
    external_account_id: str | None
    external_account_name: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    # Computed fields
    avatar_url: str | None = None
    display_name: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_integration(cls, integration: Any) -> IntegrationResponse:
        """Create from Integration model.

        Args:
            integration: Integration model instance.

        Returns:
            IntegrationResponse instance.
        """
        settings = integration.settings or {}
        return cls(
            id=integration.id,
            workspace_id=integration.workspace_id,
            provider=integration.provider,
            external_account_id=integration.external_account_id,
            external_account_name=integration.external_account_name,
            is_active=integration.is_active,
            created_at=integration.created_at,
            updated_at=integration.updated_at,
            avatar_url=settings.get("avatar_url"),
            display_name=settings.get("name") or integration.external_account_name,
        )


class IntegrationListResponse(BaseModel):
    """List of integrations response."""

    items: list[IntegrationResponse]
    total: int


class IntegrationLinkResponse(BaseModel):
    """Integration link response (commit/PR)."""

    id: UUID
    integration_id: UUID
    issue_id: UUID
    link_type: IntegrationLinkType
    external_id: str
    external_url: str | None
    title: str | None
    author_name: str | None
    author_avatar_url: str | None
    # ORM attribute is `link_metadata` (DB column alias), not `metadata`.
    # validation_alias reads the correct ORM attribute; serialization keeps
    # the `metadata` key that the frontend IntegrationLinkRaw expects.
    metadata: dict[str, Any] | None = Field(default=None, validation_alias="link_metadata")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class IntegrationLinksResponse(BaseModel):
    """List of integration links response."""

    items: list[IntegrationLinkResponse]
    total: int


class GitHubRepositoryResponse(BaseModel):
    """GitHub repository response."""

    id: int
    name: str
    full_name: str
    private: bool
    default_branch: str
    description: str | None
    html_url: str

    model_config = ConfigDict(from_attributes=True)


class GitHubRepositoriesResponse(BaseModel):
    """List of GitHub repositories response."""

    items: list[GitHubRepositoryResponse]
    total: int


class GitHubOAuthUrlResponse(BaseModel):
    """Response with GitHub OAuth URL."""

    authorize_url: str
    state: str


class ConnectGitHubResponse(BaseModel):
    """Response from GitHub connection."""

    integration: IntegrationResponse
    github_login: str
    github_name: str | None
    github_avatar_url: str


class WebhookSetupResponse(BaseModel):
    """Response from webhook setup."""

    hook_id: int
    active: bool
    events: list[str]


# ============================================================================
# Webhook Schemas
# ============================================================================


class WebhookProcessResult(BaseModel):
    """Result from webhook processing."""

    processed: bool
    event_type: str
    action: str | None = None
    links_created: int = 0
    issues_affected: list[str] = Field(default_factory=list)
    auto_transitioned: list[str] = Field(default_factory=list)
    error: str | None = None


__all__ = [
    "BranchNameResponse",
    "ConnectGitHubResponse",
    "CreateBranchRequest",
    "GitHubOAuthCallbackRequest",
    "GitHubOAuthUrlResponse",
    "GitHubRepositoriesResponse",
    "GitHubRepositoryResponse",
    "IntegrationLinkResponse",
    "IntegrationLinksResponse",
    "IntegrationListResponse",
    "IntegrationResponse",
    "LinkCommitRequest",
    "LinkPullRequestRequest",
    "SetupWebhookRequest",
    "WebhookProcessResult",
    "WebhookSetupResponse",
]
