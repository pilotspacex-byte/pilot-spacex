"""GitHub sync service for commit/PR linking.

T179: Create GitHubSyncService for syncing commits and PRs.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pilot_space.infrastructure.database.models import (
    IntegrationLink,
    IntegrationLinkType,
)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.repositories import (
        IntegrationLinkRepository,
        IssueRepository,
    )
    from pilot_space.integrations.github.client import (
        GitHubCommit,
        GitHubPullRequest,
    )
    from pilot_space.integrations.github.webhooks import (
        ParsedPREvent,
        ParsedPushEvent,
    )

logger = logging.getLogger(__name__)

# Pattern to match issue references like PILOT-123, ABC-456
ISSUE_REF_PATTERN = re.compile(r"([A-Z]{2,10})-(\d+)", re.IGNORECASE)

# Common prefixes that indicate fixes/closes
FIX_PREFIXES = ("fix", "fixes", "fixed", "close", "closes", "closed", "resolve", "resolves")


@dataclass
class IssueReference:
    """Parsed issue reference from commit message."""

    identifier: str  # e.g., "PILOT-123"
    project_identifier: str  # e.g., "PILOT"
    sequence_id: int  # e.g., 123
    is_closing: bool = False  # True if message indicates this closes the issue


@dataclass
class SyncResult:
    """Result from sync operation."""

    links_created: int = 0
    links_updated: int = 0
    issues_matched: int = 0
    errors: list[str] | None = None


class GitHubSyncService:
    """Service for syncing GitHub data to IntegrationLinks.

    Provides:
    - Issue reference extraction from commit messages
    - Commit link creation
    - PR link creation
    - Branch link creation
    """

    def __init__(
        self,
        session: AsyncSession,
        integration_link_repo: IntegrationLinkRepository,
        issue_repo: IssueRepository,
    ) -> None:
        """Initialize sync service.

        Args:
            session: Async database session.
            integration_link_repo: IntegrationLink repository.
            issue_repo: Issue repository.
        """
        self._session = session
        self._link_repo = integration_link_repo
        self._issue_repo = issue_repo

    def extract_issue_refs(self, text: str) -> list[IssueReference]:
        """Extract issue references from text.

        Matches patterns like:
        - PILOT-123
        - Fixes ABC-456
        - Closes: XYZ-789

        Args:
            text: Text to search (commit message, PR title/body).

        Returns:
            List of IssueReference objects.
        """
        if not text:
            return []

        refs: list[IssueReference] = []
        seen: set[str] = set()

        # Find all matches
        for match in ISSUE_REF_PATTERN.finditer(text):
            project_id = match.group(1).upper()
            seq_id = int(match.group(2))
            identifier = f"{project_id}-{seq_id}"

            if identifier in seen:
                continue
            seen.add(identifier)

            # Check if preceded by fix/close keyword
            start = match.start()
            prefix_text = text[max(0, start - 20) : start].lower().strip()
            is_closing = any(prefix_text.endswith(p) for p in FIX_PREFIXES)

            refs.append(
                IssueReference(
                    identifier=identifier,
                    project_identifier=project_id,
                    sequence_id=seq_id,
                    is_closing=is_closing,
                )
            )

        return refs

    async def find_issue_by_identifier(
        self,
        workspace_id: UUID,
        identifier: str,
    ) -> UUID | None:
        """Find issue UUID by identifier (e.g., PILOT-123).

        Args:
            workspace_id: Workspace UUID.
            identifier: Issue identifier.

        Returns:
            Issue UUID or None if not found.
        """
        parts = identifier.split("-")
        if len(parts) != 2:
            return None

        project_identifier = parts[0]
        try:
            sequence_id = int(parts[1])
        except ValueError:
            return None

        issue = await self._issue_repo.find_by_identifier(
            workspace_id=workspace_id,
            project_identifier=project_identifier,
            sequence_id=sequence_id,
        )
        return issue.id if issue else None

    async def sync_commit(
        self,
        workspace_id: UUID,
        integration_id: UUID,
        commit: GitHubCommit,
        repository: str,
    ) -> SyncResult:
        """Sync a single commit to linked issues.

        Args:
            workspace_id: Workspace UUID.
            integration_id: Integration UUID.
            commit: GitHub commit data.
            repository: Repository full name.

        Returns:
            SyncResult with operation counts.
        """
        result = SyncResult()

        # Extract issue references
        refs = self.extract_issue_refs(commit.message)
        if not refs:
            return result

        for ref in refs:
            issue_id = await self.find_issue_by_identifier(workspace_id, ref.identifier)
            if not issue_id:
                continue

            result.issues_matched += 1

            # Create link
            link = IntegrationLink(
                workspace_id=workspace_id,
                integration_id=integration_id,
                issue_id=issue_id,
                link_type=IntegrationLinkType.COMMIT,
                external_id=commit.sha,
                external_url=commit.html_url,
                title=commit.message.split("\n")[0][:500],  # First line, max 500
                author_name=commit.author_name,
                author_avatar_url=commit.author_avatar_url,
                link_metadata={
                    "sha": commit.sha,
                    "message": commit.message[:2000],  # Truncate
                    "repository": repository,
                    "timestamp": commit.timestamp.isoformat(),
                    "additions": commit.additions,
                    "deletions": commit.deletions,
                    "files_changed": commit.files_changed,
                    "is_closing": ref.is_closing,
                },
            )

            _, created = await self._link_repo.create_if_not_exists(link)
            if created:
                result.links_created += 1
            else:
                result.links_updated += 1

        return result

    async def sync_pull_request(
        self,
        workspace_id: UUID,
        integration_id: UUID,
        pr: GitHubPullRequest,
        repository: str,
    ) -> SyncResult:
        """Sync a pull request to linked issues.

        Args:
            workspace_id: Workspace UUID.
            integration_id: Integration UUID.
            pr: GitHub PR data.
            repository: Repository full name.

        Returns:
            SyncResult with operation counts.
        """
        result = SyncResult()

        # Extract refs from title and body
        text = f"{pr.title}\n{pr.body or ''}"
        refs = self.extract_issue_refs(text)
        if not refs:
            return result

        for ref in refs:
            issue_id = await self.find_issue_by_identifier(workspace_id, ref.identifier)
            if not issue_id:
                continue

            result.issues_matched += 1

            # Determine PR state
            pr_state = "merged" if pr.merged else pr.state

            link = IntegrationLink(
                workspace_id=workspace_id,
                integration_id=integration_id,
                issue_id=issue_id,
                link_type=IntegrationLinkType.PULL_REQUEST,
                external_id=str(pr.number),
                external_url=pr.html_url,
                title=pr.title[:500],
                author_name=pr.author_login,
                author_avatar_url=pr.author_avatar_url,
                link_metadata={
                    "number": pr.number,
                    "state": pr_state,
                    "head_branch": pr.head_branch,
                    "base_branch": pr.base_branch,
                    "repository": repository,
                    "merged_at": pr.merged_at.isoformat() if pr.merged_at else None,
                    "additions": pr.additions,
                    "deletions": pr.deletions,
                    "changed_files": pr.changed_files,
                    "is_closing": ref.is_closing,
                },
            )

            _, created = await self._link_repo.create_if_not_exists(link)
            if created:
                result.links_created += 1
            else:
                result.links_updated += 1

        return result

    async def sync_push_event(
        self,
        workspace_id: UUID,
        integration_id: UUID,
        push: ParsedPushEvent,
    ) -> SyncResult:
        """Sync a push event (multiple commits).

        Args:
            workspace_id: Workspace UUID.
            integration_id: Integration UUID.
            push: Parsed push event.

        Returns:
            Aggregated SyncResult.
        """
        result = SyncResult()
        errors: list[str] = []

        for commit_data in push.commits:
            try:
                # Parse commit data from webhook payload
                commit_result = await self._sync_commit_from_webhook(
                    workspace_id,
                    integration_id,
                    commit_data,
                    push.repository,
                    push.branch,
                )
                result.links_created += commit_result.links_created
                result.links_updated += commit_result.links_updated
                result.issues_matched += commit_result.issues_matched
            except Exception as e:
                sha = commit_data.get("id", "unknown")[:8]
                errors.append(f"Commit {sha}: {e!s}")
                logger.exception(f"Error syncing commit {sha}")

        if errors:
            result.errors = errors

        return result

    async def _sync_commit_from_webhook(
        self,
        workspace_id: UUID,
        integration_id: UUID,
        commit_data: dict[str, Any],
        repository: str,
        branch: str,
    ) -> SyncResult:
        """Sync a commit from webhook payload format.

        Args:
            workspace_id: Workspace UUID.
            integration_id: Integration UUID.
            commit_data: Commit data from webhook.
            repository: Repository full name.
            branch: Branch name.

        Returns:
            SyncResult.
        """
        result = SyncResult()

        message = commit_data.get("message", "")
        refs = self.extract_issue_refs(message)
        if not refs:
            return result

        sha = commit_data.get("id", "")
        author = commit_data.get("author", {})
        timestamp = commit_data.get("timestamp", "")

        for ref in refs:
            issue_id = await self.find_issue_by_identifier(workspace_id, ref.identifier)
            if not issue_id:
                continue

            result.issues_matched += 1

            link = IntegrationLink(
                workspace_id=workspace_id,
                integration_id=integration_id,
                issue_id=issue_id,
                link_type=IntegrationLinkType.COMMIT,
                external_id=sha,
                external_url=commit_data.get("url", ""),
                title=message.split("\n")[0][:500],
                author_name=author.get("name", ""),
                author_avatar_url=None,  # Not in webhook payload
                link_metadata={
                    "sha": sha,
                    "message": message[:2000],
                    "repository": repository,
                    "branch": branch,
                    "timestamp": timestamp,
                    "is_closing": ref.is_closing,
                    "added": commit_data.get("added", []),
                    "removed": commit_data.get("removed", []),
                    "modified": commit_data.get("modified", []),
                },
            )

            _, created = await self._link_repo.create_if_not_exists(link)
            if created:
                result.links_created += 1
            else:
                result.links_updated += 1

        return result

    async def sync_pr_event(
        self,
        workspace_id: UUID,
        integration_id: UUID,
        pr: ParsedPREvent,
    ) -> SyncResult:
        """Sync a PR event from webhook.

        Args:
            workspace_id: Workspace UUID.
            integration_id: Integration UUID.
            pr: Parsed PR event.

        Returns:
            SyncResult.
        """
        result = SyncResult()

        text = f"{pr.title}\n{pr.body or ''}"
        refs = self.extract_issue_refs(text)
        if not refs:
            return result

        pr_state = "merged" if pr.merged else pr.state

        for ref in refs:
            issue_id = await self.find_issue_by_identifier(workspace_id, ref.identifier)
            if not issue_id:
                continue

            result.issues_matched += 1

            link = IntegrationLink(
                workspace_id=workspace_id,
                integration_id=integration_id,
                issue_id=issue_id,
                link_type=IntegrationLinkType.PULL_REQUEST,
                external_id=str(pr.number),
                external_url=pr.html_url,
                title=pr.title[:500],
                author_name=pr.author_login,
                author_avatar_url=None,  # Not in parsed event
                link_metadata={
                    "number": pr.number,
                    "state": pr_state,
                    "head_branch": pr.head_branch,
                    "base_branch": pr.base_branch,
                    "repository": pr.repository,
                    "is_closing": ref.is_closing,
                },
            )

            _, created = await self._link_repo.create_if_not_exists(link)
            if created:
                result.links_created += 1
            else:
                result.links_updated += 1

        return result


__all__ = [
    "GitHubSyncService",
    "IssueReference",
    "SyncResult",
]
