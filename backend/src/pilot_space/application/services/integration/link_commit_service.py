"""Link Commit service for manual commit linking.

T183: Create LinkCommitService for commit-issue linking.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pilot_space.infrastructure.database.models import (
    Activity,
    ActivityType,
    IntegrationLink,
    IntegrationLinkType,
)
from pilot_space.infrastructure.encryption import decrypt_api_key
from pilot_space.integrations.github.client import GitHubClient

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.repositories import (
        ActivityRepository,
        IntegrationLinkRepository,
        IntegrationRepository,
        IssueRepository,
    )

logger = logging.getLogger(__name__)


class LinkCommitError(Exception):
    """Raised when commit linking fails."""


@dataclass
class LinkCommitPayload:
    """Payload for linking a commit to an issue.

    Attributes:
        workspace_id: Workspace UUID.
        issue_id: Issue UUID to link to.
        integration_id: GitHub Integration UUID.
        repository: Repository full name (owner/repo).
        commit_sha: Commit SHA to link.
        actor_id: User performing the action.
    """

    workspace_id: UUID
    issue_id: UUID
    integration_id: UUID
    repository: str
    commit_sha: str
    actor_id: UUID


@dataclass
class LinkCommitResult:
    """Result from commit linking."""

    link: IntegrationLink
    created: bool = True
    commit_message: str = ""
    author_name: str = ""


@dataclass
class LinkPullRequestPayload:
    """Payload for linking a PR to an issue.

    Attributes:
        workspace_id: Workspace UUID.
        issue_id: Issue UUID to link to.
        integration_id: GitHub Integration UUID.
        repository: Repository full name (owner/repo).
        pr_number: PR number to link.
        actor_id: User performing the action.
    """

    workspace_id: UUID
    issue_id: UUID
    integration_id: UUID
    repository: str
    pr_number: int
    actor_id: UUID


@dataclass
class LinkPullRequestResult:
    """Result from PR linking."""

    link: IntegrationLink
    created: bool = True
    pr_title: str = ""
    pr_state: str = ""


@dataclass
class BulkLinkResult:
    """Result from bulk linking."""

    links_created: int = 0
    links_skipped: int = 0
    errors: list[str] = field(default_factory=list)


class LinkCommitService:
    """Service for manually linking commits/PRs to issues.

    Handles:
    - Single commit linking
    - Single PR linking
    - Activity recording
    """

    def __init__(
        self,
        session: AsyncSession,
        integration_repo: IntegrationRepository,
        integration_link_repo: IntegrationLinkRepository,
        issue_repo: IssueRepository,
        activity_repo: ActivityRepository,
    ) -> None:
        """Initialize service.

        Args:
            session: Async database session.
            integration_repo: Integration repository.
            integration_link_repo: IntegrationLink repository.
            issue_repo: Issue repository.
            activity_repo: Activity repository.
        """
        self._session = session
        self._integration_repo = integration_repo
        self._link_repo = integration_link_repo
        self._issue_repo = issue_repo
        self._activity_repo = activity_repo

    async def link_commit(self, payload: LinkCommitPayload) -> LinkCommitResult:
        """Link a commit to an issue.

        Args:
            payload: Link parameters.

        Returns:
            LinkCommitResult with link details.

        Raises:
            LinkCommitError: If linking fails.
        """
        # Validate integration
        integration = await self._integration_repo.get_by_id(payload.integration_id)
        if not integration:
            raise LinkCommitError("Integration not found")
        if not integration.is_active:
            raise LinkCommitError("Integration is not active")

        # Validate issue
        issue = await self._issue_repo.get_by_id_with_relations(payload.issue_id)
        if not issue:
            raise LinkCommitError("Issue not found")

        # Fetch commit details from GitHub
        access_token = decrypt_api_key(integration.access_token)
        async with GitHubClient(access_token) as client:
            owner, repo = payload.repository.split("/")
            try:
                commit = await client.get_commit(owner, repo, payload.commit_sha)
            except Exception as e:
                raise LinkCommitError(f"Failed to fetch commit: {e}") from e

        # Create link
        link = IntegrationLink(
            workspace_id=payload.workspace_id,
            integration_id=payload.integration_id,
            issue_id=payload.issue_id,
            link_type=IntegrationLinkType.COMMIT,
            external_id=commit.sha,
            external_url=commit.html_url,
            title=commit.message.split("\n")[0][:500],
            author_name=commit.author_name,
            author_avatar_url=commit.author_avatar_url,
            metadata={
                "sha": commit.sha,
                "message": commit.message[:2000],
                "repository": payload.repository,
                "timestamp": commit.timestamp.isoformat(),
                "additions": commit.additions,
                "deletions": commit.deletions,
                "files_changed": commit.files_changed,
                "manual_link": True,
            },
        )

        link, created = await self._link_repo.create_if_not_exists(link)

        # Record activity if created
        if created:
            activity = Activity(
                workspace_id=payload.workspace_id,
                issue_id=payload.issue_id,
                actor_id=payload.actor_id,
                activity_type=ActivityType.LINKED_TO_NOTE,  # Reuse for external links
                field="integration_link",
                new_value=commit.sha[:8],
                activity_metadata={
                    "link_type": "commit",
                    "repository": payload.repository,
                    "commit_message": commit.message[:200],
                },
            )
            await self._activity_repo.create(activity)

        logger.info(
            "Linked commit to issue",
            extra={
                "issue_id": str(payload.issue_id),
                "commit_sha": commit.sha[:8],
                "created": created,
            },
        )

        return LinkCommitResult(
            link=link,
            created=created,
            commit_message=commit.message,
            author_name=commit.author_name,
        )

    async def link_pull_request(self, payload: LinkPullRequestPayload) -> LinkPullRequestResult:
        """Link a pull request to an issue.

        Args:
            payload: Link parameters.

        Returns:
            LinkPullRequestResult with link details.

        Raises:
            LinkCommitError: If linking fails.
        """
        # Validate integration
        integration = await self._integration_repo.get_by_id(payload.integration_id)
        if not integration:
            raise LinkCommitError("Integration not found")
        if not integration.is_active:
            raise LinkCommitError("Integration is not active")

        # Validate issue
        issue = await self._issue_repo.get_by_id_with_relations(payload.issue_id)
        if not issue:
            raise LinkCommitError("Issue not found")

        # Fetch PR details from GitHub
        access_token = decrypt_api_key(integration.access_token)
        async with GitHubClient(access_token) as client:
            owner, repo = payload.repository.split("/")
            try:
                pr = await client.get_pull_request(owner, repo, payload.pr_number)
            except Exception as e:
                raise LinkCommitError(f"Failed to fetch PR: {e}") from e

        # Determine PR state
        pr_state = "merged" if pr.merged else pr.state

        # Create link
        link = IntegrationLink(
            workspace_id=payload.workspace_id,
            integration_id=payload.integration_id,
            issue_id=payload.issue_id,
            link_type=IntegrationLinkType.PULL_REQUEST,
            external_id=str(pr.number),
            external_url=pr.html_url,
            title=pr.title[:500],
            author_name=pr.author_login,
            author_avatar_url=pr.author_avatar_url,
            metadata={
                "number": pr.number,
                "state": pr_state,
                "head_branch": pr.head_branch,
                "base_branch": pr.base_branch,
                "repository": payload.repository,
                "merged_at": pr.merged_at.isoformat() if pr.merged_at else None,
                "additions": pr.additions,
                "deletions": pr.deletions,
                "changed_files": pr.changed_files,
                "manual_link": True,
            },
        )

        link, created = await self._link_repo.create_if_not_exists(link)

        # Record activity if created
        if created:
            activity = Activity(
                workspace_id=payload.workspace_id,
                issue_id=payload.issue_id,
                actor_id=payload.actor_id,
                activity_type=ActivityType.LINKED_TO_NOTE,
                field="integration_link",
                new_value=f"#{pr.number}",
                activity_metadata={
                    "link_type": "pull_request",
                    "repository": payload.repository,
                    "pr_title": pr.title[:200],
                },
            )
            await self._activity_repo.create(activity)

        logger.info(
            "Linked PR to issue",
            extra={
                "issue_id": str(payload.issue_id),
                "pr_number": pr.number,
                "created": created,
            },
        )

        return LinkPullRequestResult(
            link=link,
            created=created,
            pr_title=pr.title,
            pr_state=pr_state,
        )


__all__ = [
    "BulkLinkResult",
    "LinkCommitError",
    "LinkCommitPayload",
    "LinkCommitResult",
    "LinkCommitService",
    "LinkPullRequestPayload",
    "LinkPullRequestResult",
]
