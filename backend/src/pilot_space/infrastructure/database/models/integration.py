"""Integration SQLAlchemy models.

Integration models for GitHub and Slack integrations with OAuth token management.
Supports PR/commit linking and auto-transitions based on GitHub events.

T172: Create Integration model.
T173: Create IntegrationLink model.
"""

from __future__ import annotations

import uuid
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import WorkspaceScopedModel
from pilot_space.infrastructure.database.types import JSONBCompat

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.issue import Issue


class IntegrationProvider(StrEnum):
    """Supported integration providers.

    MVP supports GitHub and Slack per spec.md US-18.
    """

    GITHUB = "github"
    SLACK = "slack"


class IntegrationLinkType(StrEnum):
    """Type of link between issue and external resource.

    Links track commits, PRs, branches for GitHub integration.
    """

    COMMIT = "commit"
    PULL_REQUEST = "pull_request"
    BRANCH = "branch"
    MENTION = "mention"  # Issue mentioned in external system


class Integration(WorkspaceScopedModel):
    """Integration model for external service connections.

    Stores OAuth tokens and configuration for workspace integrations.
    Tokens are encrypted before storage for security.

    Attributes:
        provider: Integration provider (github/slack).
        access_token: Encrypted OAuth access token.
        refresh_token: Encrypted OAuth refresh token (if applicable).
        token_expires_at: Token expiration timestamp (ISO 8601 string).
        external_account_id: External service account/org ID.
        external_account_name: External service account/org name.
        settings: Provider-specific configuration (JSONBCompat).
        is_active: Whether integration is currently active.
        installed_by_id: User who installed the integration.
    """

    __tablename__ = "integrations"  # type: ignore[assignment]

    # Provider type
    provider: Mapped[IntegrationProvider] = mapped_column(
        SQLEnum(
            IntegrationProvider,
            name="integration_provider",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )

    # OAuth tokens (encrypted at application layer before storage)
    access_token: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    refresh_token: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    token_expires_at: Mapped[str | None] = mapped_column(
        String(50),  # ISO 8601 timestamp
        nullable=True,
    )

    # External account info
    external_account_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    external_account_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Provider-specific settings
    settings: Mapped[dict[str, Any] | None] = mapped_column(
        JSONBCompat,
        nullable=True,
        default=dict,
    )
    # settings structure for GitHub:
    # {
    #   "default_repository": "owner/repo",
    #   "repositories": ["owner/repo1", "owner/repo2"],
    #   "auto_link_commits": true,
    #   "auto_transition_on_pr_merge": true,
    #   "webhook_secret": "encrypted_value",  # pragma: allowlist secret
    #   "default_branch": "main",
    #   "installation_id": 12345  # GitHub App installation ID
    # }
    # settings structure for Slack:
    # {
    #   "default_channel_id": "C1234567890",
    #   "notify_on_issue_create": true,
    #   "notify_on_pr_merge": true,
    #   "bot_user_id": "U1234567890"
    # }

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    # Installer
    installed_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    links: Mapped[list[IntegrationLink]] = relationship(
        "IntegrationLink",
        back_populates="integration",
        cascade="all, delete-orphan",
        lazy="raise",
    )

    # Indexes and constraints
    __table_args__ = (
        # Only one integration per provider per workspace
        UniqueConstraint(
            "workspace_id",
            "provider",
            name="uq_integrations_workspace_provider",
        ),
        Index("ix_integrations_provider", "provider"),
        Index("ix_integrations_is_active", "is_active"),
        Index("ix_integrations_is_deleted", "is_deleted"),
        Index("ix_integrations_external_account_id", "external_account_id"),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<Integration(id={self.id}, provider={self.provider.value})>"

    @property
    def is_github(self) -> bool:
        """Check if this is a GitHub integration."""
        return self.provider == IntegrationProvider.GITHUB

    @property
    def is_slack(self) -> bool:
        """Check if this is a Slack integration."""
        return self.provider == IntegrationProvider.SLACK

    @property
    def repositories(self) -> list[str]:
        """Get list of connected GitHub repositories."""
        if not self.settings or not self.is_github:
            return []
        return self.settings.get("repositories", [])

    @property
    def default_repository(self) -> str | None:
        """Get default GitHub repository."""
        if not self.settings or not self.is_github:
            return None
        return self.settings.get("default_repository")


class IntegrationLink(WorkspaceScopedModel):
    """IntegrationLink model for linking issues to external resources.

    Links issues to commits, PRs, branches in GitHub.
    Used for bi-directional traceability and auto-transitions.

    Attributes:
        integration_id: FK to parent integration.
        issue_id: FK to linked issue.
        link_type: Type of link (commit/pr/branch/mention).
        external_id: ID in external system (commit SHA, PR number, etc.).
        external_url: Full URL to resource in external system.
        title: Title/message of external resource.
        author_name: Author of the commit/PR.
        author_avatar_url: Avatar URL of author.
        metadata: Additional data from external system (JSONBCompat).
    """

    __tablename__ = "integration_links"  # type: ignore[assignment]

    # Foreign keys
    integration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("integrations.id", ondelete="CASCADE"),
        nullable=False,
    )
    issue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("issues.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Link details
    link_type: Mapped[IntegrationLinkType] = mapped_column(
        SQLEnum(IntegrationLinkType, name="integration_link_type", create_type=False),
        nullable=False,
    )
    external_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    external_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
    )
    title: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )

    # Author info
    author_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    author_avatar_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
    )

    # CI check status from GitHub check_suite webhook events.
    # Values: "pending" | "success" | "failure" | "neutral" | None
    ci_status: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    # Additional metadata from external system
    # Python attribute is `link_metadata`; DB column is `metadata` (from migration 009).
    link_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSONBCompat,
        nullable=True,
        default=dict,
    )
    # link_metadata structure for commits:
    # {
    #   "sha": "abc123...",
    #   "message": "fix: resolve PILOT-123",
    #   "branch": "feature/fix-auth",
    #   "repository": "owner/repo",
    #   "timestamp": "2026-01-24T10:00:00Z",
    #   "files_changed": 5,
    #   "additions": 100,
    #   "deletions": 20
    # }
    # metadata structure for pull_request:
    # {
    #   "number": 42,
    #   "state": "open" | "closed" | "merged",
    #   "head_branch": "feature/fix-auth",
    #   "base_branch": "main",
    #   "repository": "owner/repo",
    #   "is_draft": false,
    #   "merged_at": "2026-01-24T12:00:00Z",
    #   "commits_count": 3,
    #   "changed_files": 10,
    #   "additions": 200,
    #   "deletions": 50,
    #   "reviews": [{"user": "reviewer", "state": "approved"}]
    # }
    # metadata structure for branch:
    # {
    #   "name": "feature/PILOT-123",
    #   "repository": "owner/repo",
    #   "is_protected": false,
    #   "ahead_by": 5,
    #   "behind_by": 2
    # }

    # Relationships
    integration: Mapped[Integration] = relationship(
        "Integration",
        back_populates="links",
        lazy="joined",
    )
    issue: Mapped[Issue] = relationship(
        "Issue",
        lazy="joined",
    )

    # Indexes and constraints
    __table_args__ = (
        # Prevent duplicate links
        UniqueConstraint(
            "integration_id",
            "issue_id",
            "link_type",
            "external_id",
            name="uq_integration_links_unique_link",
        ),
        Index("ix_integration_links_integration_id", "integration_id"),
        Index("ix_integration_links_issue_id", "issue_id"),
        Index("ix_integration_links_link_type", "link_type"),
        Index("ix_integration_links_external_id", "external_id"),
        Index("ix_integration_links_is_deleted", "is_deleted"),
        Index(
            "ix_integration_links_integration_type",
            "integration_id",
            "link_type",
        ),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<IntegrationLink(id={self.id}, type={self.link_type.value}, "
            f"external_id={self.external_id})>"
        )

    @property
    def is_commit(self) -> bool:
        """Check if this is a commit link."""
        return self.link_type == IntegrationLinkType.COMMIT

    @property
    def is_pull_request(self) -> bool:
        """Check if this is a pull request link."""
        return self.link_type == IntegrationLinkType.PULL_REQUEST

    @property
    def is_branch(self) -> bool:
        """Check if this is a branch link."""
        return self.link_type == IntegrationLinkType.BRANCH

    @property
    def repository(self) -> str | None:
        """Get repository name from link_metadata."""
        if not self.link_metadata:
            return None
        return self.link_metadata.get("repository")

    @property
    def pr_state(self) -> str | None:
        """Get PR state from link_metadata (for PR links)."""
        if not self.link_metadata or not self.is_pull_request:
            return None
        return self.link_metadata.get("state")

    @property
    def is_merged(self) -> bool:
        """Check if PR is merged (for PR links)."""
        return self.pr_state == "merged"


__all__ = [
    "Integration",
    "IntegrationLink",
    "IntegrationLinkType",
    "IntegrationProvider",
]
