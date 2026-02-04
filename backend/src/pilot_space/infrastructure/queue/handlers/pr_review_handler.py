"""PR Review queue job handler.

T195-T195a: Create queue handler for async PR review processing.

Handles:
- Fetching PR diff from GitHub
- Invoking PRReviewAgent with Claude Opus
- Posting inline comments via GitHub API
- Creating summary comment
- Handling partial failures gracefully
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pilot_space.ai.agents.agent_base import AgentContext
from pilot_space.ai.agents.pr_review_agent import (
    PRReviewAgent,
    PRReviewInput,
    PRReviewOutput,
    ReviewComment,
    ReviewSeverity,
)
from pilot_space.ai.prompts.pr_review import format_review_as_markdown
from pilot_space.infrastructure.queue.models import QueueName

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.ai.infrastructure.cost_tracker import CostTracker
    from pilot_space.ai.infrastructure.key_storage import SecureKeyStorage
    from pilot_space.ai.infrastructure.resilience import ResilientExecutor
    from pilot_space.ai.providers.provider_selector import ProviderSelector
    from pilot_space.ai.tools.mcp_server import ToolRegistry
    from pilot_space.infrastructure.database.repositories import (
        AIConfigurationRepository,
        IntegrationRepository,
    )
    from pilot_space.infrastructure.queue.supabase_queue import SupabaseQueueClient
    from pilot_space.integrations.github.client import GitHubClient

logger = logging.getLogger(__name__)

# Queue configuration
PR_REVIEW_QUEUE = QueueName.AI_HIGH
PR_REVIEW_DLQ = QueueName.DEAD_LETTER
PR_REVIEW_VISIBILITY_TIMEOUT = 600  # 10 minutes
PR_REVIEW_MAX_RETRIES = 3


class PRReviewJobStatus(StrEnum):
    """Status of a PR review job."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"  # Completed with some failures


@dataclass
class PRReviewJobPayload:
    """Payload for PR review queue job.

    Attributes:
        job_id: Unique job identifier.
        workspace_id: Workspace requesting the review.
        integration_id: GitHub integration to use.
        repository: Repository in owner/repo format.
        pr_number: Pull request number.
        user_id: User who triggered the review.
        correlation_id: Request correlation ID for tracing.
        post_comments: Whether to post inline comments.
        post_summary: Whether to post summary comment.
        project_context: Additional project context.
    """

    job_id: str
    workspace_id: str
    integration_id: str
    repository: str
    pr_number: int
    user_id: str
    correlation_id: str
    post_comments: bool = True
    post_summary: bool = True
    project_context: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PRReviewJobPayload:
        """Create from dictionary."""
        return cls(
            job_id=data["job_id"],
            workspace_id=data["workspace_id"],
            integration_id=data["integration_id"],
            repository=data["repository"],
            pr_number=data["pr_number"],
            user_id=data["user_id"],
            correlation_id=data.get("correlation_id", ""),
            post_comments=data.get("post_comments", True),
            post_summary=data.get("post_summary", True),
            project_context=data.get("project_context", {}),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "job_id": self.job_id,
            "workspace_id": self.workspace_id,
            "integration_id": self.integration_id,
            "repository": self.repository,
            "pr_number": self.pr_number,
            "user_id": self.user_id,
            "correlation_id": self.correlation_id,
            "post_comments": self.post_comments,
            "post_summary": self.post_summary,
            "project_context": self.project_context,
        }


@dataclass
class PRReviewJobResult:
    """Result from PR review job execution.

    Attributes:
        job_id: Job identifier.
        status: Final job status.
        review_output: Review results (if successful).
        comments_posted: Number of inline comments posted.
        summary_posted: Whether summary was posted.
        error: Error message if failed.
        github_comment_id: ID of summary comment (if posted).
    """

    job_id: str
    status: PRReviewJobStatus
    review_output: PRReviewOutput | None = None
    comments_posted: int = 0
    summary_posted: bool = False
    error: str | None = None
    github_comment_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "comments_posted": self.comments_posted,
            "summary_posted": self.summary_posted,
            "error": self.error,
            "github_comment_id": self.github_comment_id,
            "review_summary": self.review_output.summary if self.review_output else None,
            "critical_count": self.review_output.critical_count if self.review_output else 0,
            "warning_count": self.review_output.warning_count if self.review_output else 0,
            "approval_recommendation": (
                self.review_output.approval_recommendation if self.review_output else None
            ),
        }


class PRReviewJobHandler:
    """Handler for PR review queue jobs.

    Processes PR review requests from the queue:
    1. Fetches PR diff and file contents from GitHub
    2. Invokes PRReviewAgent for AI analysis
    3. Posts inline review comments to GitHub
    4. Posts summary comment with findings
    5. Handles retries and dead-letter queue
    """

    def __init__(
        self,
        session: AsyncSession,
        queue_client: SupabaseQueueClient,
        integration_repo: IntegrationRepository,
        ai_config_repo: AIConfigurationRepository,
        tool_registry: ToolRegistry,
        provider_selector: ProviderSelector,
        cost_tracker: CostTracker,
        resilient_executor: ResilientExecutor,
        key_storage: SecureKeyStorage,
    ) -> None:
        """Initialize handler.

        Args:
            session: Database session.
            queue_client: Supabase queue client.
            integration_repo: Integration repository.
            ai_config_repo: AI configuration repository.
            tool_registry: Registry for MCP tool access.
            provider_selector: Provider/model selection service.
            cost_tracker: Cost tracking service.
            resilient_executor: Retry and circuit breaker service.
            key_storage: Secure API key storage service.
        """
        self._session = session
        self._queue = queue_client
        self._integration_repo = integration_repo
        self._ai_config_repo = ai_config_repo
        self._agent = PRReviewAgent(
            tool_registry=tool_registry,
            provider_selector=provider_selector,
            cost_tracker=cost_tracker,
            resilient_executor=resilient_executor,
            key_storage=key_storage,
        )

    async def execute(self, payload: PRReviewJobPayload) -> PRReviewJobResult:
        """Execute a PR review job.

        Args:
            payload: Job payload.

        Returns:
            Job result with review output.
        """
        logger.info(
            "Starting PR review job",
            extra={
                "job_id": payload.job_id,
                "repository": payload.repository,
                "pr_number": payload.pr_number,
            },
        )

        try:
            # Get GitHub client
            github_client = await self._get_github_client(UUID(payload.integration_id))

            # Fetch PR data
            owner, repo = payload.repository.split("/")
            pr_input = await self._fetch_pr_data(
                github_client,
                owner,
                repo,
                payload.pr_number,
                payload.project_context,
            )

            # Build agent context
            context = await self._build_agent_context(
                workspace_id=UUID(payload.workspace_id),
                user_id=UUID(payload.user_id),
                correlation_id=payload.correlation_id,
            )

            # Execute review (SDK agent returns AgentResult)
            agent_result = await self._agent.run(pr_input, context)

            if not agent_result.success or agent_result.output is None:
                error_msg = agent_result.error or "Review execution failed"
                logger.error(
                    "PR review execution failed",
                    extra={
                        "job_id": payload.job_id,
                        "error": error_msg,
                    },
                )
                return PRReviewJobResult(
                    job_id=payload.job_id,
                    status=PRReviewJobStatus.FAILED,
                    error=error_msg,
                )

            review_output = agent_result.output

            # Post results to GitHub
            comments_posted = 0
            summary_posted = False
            github_comment_id = None

            if payload.post_comments:
                comments_posted = await self._post_inline_comments(
                    github_client,
                    owner,
                    repo,
                    payload.pr_number,
                    review_output.comments,
                )

            if payload.post_summary:
                summary_posted, github_comment_id = await self._post_summary_comment(
                    github_client,
                    owner,
                    repo,
                    payload.pr_number,
                    review_output,
                )

            await github_client.close()

            return PRReviewJobResult(
                job_id=payload.job_id,
                status=PRReviewJobStatus.COMPLETED,
                review_output=review_output,
                comments_posted=comments_posted,
                summary_posted=summary_posted,
                github_comment_id=github_comment_id,
            )

        except Exception as e:
            logger.exception(
                "PR review job failed",
                extra={
                    "job_id": payload.job_id,
                    "error": str(e),
                },
            )
            return PRReviewJobResult(
                job_id=payload.job_id,
                status=PRReviewJobStatus.FAILED,
                error=str(e),
            )

    async def _get_github_client(self, integration_id: UUID) -> GitHubClient:
        """Get authenticated GitHub client for integration.

        Args:
            integration_id: Integration ID.

        Returns:
            Configured GitHubClient.

        Raises:
            ValueError: If integration not found or inactive.
        """
        from pilot_space.infrastructure.encryption import decrypt_api_key
        from pilot_space.integrations.github.client import GitHubClient

        integration = await self._integration_repo.get_by_id(integration_id)
        if not integration:
            raise ValueError(f"Integration {integration_id} not found")

        if not integration.is_active:
            raise ValueError(f"Integration {integration_id} is not active")

        access_token = decrypt_api_key(integration.access_token)
        return GitHubClient(access_token)

    async def _fetch_pr_data(
        self,
        client: GitHubClient,
        owner: str,
        repo: str,
        pr_number: int,
        project_context: dict[str, str],
    ) -> PRReviewInput:
        """Fetch PR data from GitHub.

        Args:
            client: GitHub client.
            owner: Repository owner.
            repo: Repository name.
            pr_number: PR number.
            project_context: Additional context.

        Returns:
            PRReviewInput with PR data.
        """
        # Get PR metadata
        pr = await client.get_pull_request(owner, repo, pr_number)

        # Get diff
        diff = await self._get_pr_diff(client, owner, repo, pr_number)

        # Get changed files with content
        files = await self._get_pr_files(client, owner, repo, pr_number)
        file_contents: dict[str, str] = {}
        changed_files: list[str] = []

        for file_info in files:
            file_path = file_info.get("filename", "")
            changed_files.append(file_path)

            # Skip binary files
            if file_info.get("binary", False):
                continue

            # Get file content if available
            patch = file_info.get("patch", "")
            if patch:
                # Use patch for changed lines context
                file_contents[file_path] = patch

        return PRReviewInput(
            pr_number=pr_number,
            pr_title=pr.title,
            pr_description=pr.body or "",
            diff=diff,
            file_contents=file_contents,
            changed_files=changed_files,
            project_context=project_context,
            base_branch=pr.base_branch,
            head_branch=pr.head_branch,
        )

    async def _get_pr_diff(
        self,
        client: GitHubClient,
        owner: str,
        repo: str,
        pr_number: int,
    ) -> str:
        """Get PR diff from GitHub.

        Args:
            client: GitHub client.
            owner: Repository owner.
            repo: Repository name.
            pr_number: PR number.

        Returns:
            Unified diff string.
        """
        import httpx

        # Use media type for diff format
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(
                f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}",
                headers={
                    "Accept": "application/vnd.github.diff",
                    "Authorization": f"Bearer {client.access_token}",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                timeout=30.0,
            )
            response.raise_for_status()
            return response.text

    async def _get_pr_files(
        self,
        client: GitHubClient,
        owner: str,
        repo: str,
        pr_number: int,
    ) -> list[dict[str, Any]]:
        """Get list of changed files in PR.

        Args:
            client: GitHub client.
            owner: Repository owner.
            repo: Repository name.
            pr_number: PR number.

        Returns:
            List of file information dictionaries.
        """
        return await client.get_pull_request_files(owner, repo, pr_number)

    async def _build_agent_context(
        self,
        workspace_id: UUID,
        user_id: UUID,
        correlation_id: str,
    ) -> AgentContext:
        """Build agent context.

        Args:
            workspace_id: Workspace ID.
            user_id: User ID.
            correlation_id: Correlation ID.

        Returns:
            Configured AgentContext.
        """
        return AgentContext(
            workspace_id=workspace_id,
            user_id=user_id,
            metadata={"correlation_id": correlation_id},
        )

    async def _post_inline_comments(
        self,
        client: GitHubClient,
        owner: str,
        repo: str,
        pr_number: int,
        comments: list[ReviewComment],
    ) -> int:
        """Post inline review comments to GitHub.

        Args:
            client: GitHub client.
            owner: Repository owner.
            repo: Repository name.
            pr_number: PR number.
            comments: Review comments to post.

        Returns:
            Number of comments successfully posted.
        """
        posted = 0

        # Group critical and warning comments for inline posting
        important_comments = [
            c for c in comments if c.severity in (ReviewSeverity.CRITICAL, ReviewSeverity.WARNING)
        ]

        # Limit inline comments to avoid spam
        max_inline_comments = 25
        for comment in important_comments[:max_inline_comments]:
            try:
                body = self._format_inline_comment(comment)
                await self._post_pr_review_comment(
                    client,
                    owner,
                    repo,
                    pr_number,
                    comment.file_path,
                    comment.line_number,
                    body,
                )
                posted += 1
            except Exception as e:
                logger.warning(
                    "Failed to post inline comment",
                    extra={
                        "file": comment.file_path,
                        "line": comment.line_number,
                        "error": str(e),
                    },
                )

        return posted

    async def _post_pr_review_comment(
        self,
        client: GitHubClient,
        owner: str,
        repo: str,
        pr_number: int,
        path: str,
        line: int,
        body: str,
    ) -> dict[str, Any]:
        """Post a single review comment on a PR.

        Args:
            client: GitHub client.
            owner: Repository owner.
            repo: Repository name.
            pr_number: PR number.
            path: File path.
            line: Line number.
            body: Comment body.

        Returns:
            Created comment data.
        """
        return await client.post_review_comment(owner, repo, pr_number, path, line, body)

    def _format_inline_comment(self, comment: ReviewComment) -> str:
        """Format a review comment for inline display.

        Args:
            comment: Review comment.

        Returns:
            Formatted markdown string.
        """
        severity_icons = {
            ReviewSeverity.CRITICAL: ":red_circle:",
            ReviewSeverity.WARNING: ":orange_circle:",
            ReviewSeverity.SUGGESTION: ":large_blue_circle:",
            ReviewSeverity.INFO: ":white_circle:",
        }

        icon = severity_icons.get(comment.severity, ":speech_balloon:")
        parts = [
            f"{icon} **{comment.severity.value.upper()}** ({comment.category.value})\n\n",
            comment.message,
        ]

        if comment.suggestion:
            parts.append(f"\n\n**Suggested fix:**\n```\n{comment.suggestion}\n```")

        return "".join(parts)

    async def _post_summary_comment(
        self,
        client: GitHubClient,
        owner: str,
        repo: str,
        pr_number: int,
        output: PRReviewOutput,
    ) -> tuple[bool, int | None]:
        """Post summary comment to PR.

        Args:
            client: GitHub client.
            owner: Repository owner.
            repo: Repository name.
            pr_number: PR number.
            output: Review output.

        Returns:
            Tuple of (success, comment_id).
        """
        try:
            summary_markdown = format_review_as_markdown(output)
            result = await client.post_comment(owner, repo, pr_number, summary_markdown)
            return True, result.get("id")
        except Exception as e:
            logger.warning(
                "Failed to post summary comment",
                extra={"error": str(e)},
            )
            return False, None


async def handle_pr_review_job(
    session: AsyncSession,
    queue_client: SupabaseQueueClient,
    integration_repo: IntegrationRepository,
    ai_config_repo: AIConfigurationRepository,
    tool_registry: ToolRegistry,
    provider_selector: ProviderSelector,
    cost_tracker: CostTracker,
    resilient_executor: ResilientExecutor,
    key_storage: SecureKeyStorage,
    payload: PRReviewJobPayload,
) -> PRReviewJobResult:
    """Process a single PR review job from the queue.

    Args:
        session: Database session.
        queue_client: Queue client.
        integration_repo: Integration repository.
        ai_config_repo: AI configuration repository.
        tool_registry: Registry for MCP tool access.
        provider_selector: Provider/model selection service.
        cost_tracker: Cost tracking service.
        resilient_executor: Retry and circuit breaker service.
        key_storage: Secure API key storage service.
        payload: Job payload.

    Returns:
        Job result.
    """
    handler = PRReviewJobHandler(
        session=session,
        queue_client=queue_client,
        integration_repo=integration_repo,
        ai_config_repo=ai_config_repo,
        tool_registry=tool_registry,
        provider_selector=provider_selector,
        cost_tracker=cost_tracker,
        resilient_executor=resilient_executor,
        key_storage=key_storage,
    )
    return await handler.execute(payload)


__all__ = [
    "PR_REVIEW_DLQ",
    "PR_REVIEW_MAX_RETRIES",
    "PR_REVIEW_QUEUE",
    "PR_REVIEW_VISIBILITY_TIMEOUT",
    "PRReviewJobHandler",
    "PRReviewJobPayload",
    "PRReviewJobResult",
    "PRReviewJobStatus",
    "handle_pr_review_job",
]
