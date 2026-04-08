"""GitHub webhook handler with signature verification.

T178: Create GitHubWebhookHandler for processing webhook events.
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from uuid import UUID

    from pilot_space.infrastructure.queue.supabase_queue import SupabaseQueueClient

logger = get_logger(__name__)


class GitHubEventType(StrEnum):
    """Supported GitHub webhook event types."""

    PUSH = "push"
    PULL_REQUEST = "pull_request"
    PULL_REQUEST_REVIEW = "pull_request_review"
    ISSUE_COMMENT = "issue_comment"
    CHECK_SUITE = "check_suite"


class GitHubPRAction(StrEnum):
    """Pull request actions we care about."""

    OPENED = "opened"
    CLOSED = "closed"
    REOPENED = "reopened"
    MERGED = "merged"  # Virtual action (closed + merged)
    SYNCHRONIZE = "synchronize"


class WebhookVerificationError(Exception):
    """Raised when webhook signature verification fails."""


class WebhookProcessingError(Exception):
    """Raised when webhook processing fails."""


@dataclass
class WebhookPayload:
    """Parsed webhook payload.

    Attributes:
        event_type: GitHub event type.
        action: Event action (for PR events).
        delivery_id: Unique delivery ID for idempotency.
        repository: Repository full name (owner/repo).
        sender_login: GitHub username who triggered the event.
        raw_payload: Full raw payload.
        timestamp: When the event was received.
    """

    event_type: GitHubEventType
    action: str | None
    delivery_id: str
    repository: str
    sender_login: str
    raw_payload: dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=UTC))


@dataclass
class ParsedPushEvent:
    """Parsed push event data."""

    ref: str  # refs/heads/branch-name
    before_sha: str
    after_sha: str
    commits: list[dict[str, Any]]
    repository: str
    pusher: str

    @property
    def branch(self) -> str:
        """Get branch name from ref."""
        return self.ref.removeprefix("refs/heads/")

    @property
    def is_branch_delete(self) -> bool:
        """Check if this is a branch deletion."""
        return self.after_sha == "0" * 40


@dataclass
class ParsedPREvent:
    """Parsed pull request event data."""

    action: GitHubPRAction
    number: int
    title: str
    body: str | None
    state: str  # open, closed
    merged: bool
    head_branch: str
    base_branch: str
    html_url: str
    author_login: str
    repository: str


@dataclass
class ParsedCheckSuiteEvent:
    """Parsed check_suite event data."""

    action: str  # "completed" | "requested" | "rerequested"
    conclusion: (
        str | None
    )  # "success" | "failure" | "neutral" | "cancelled" | "timed_out" | "action_required" | "skipped"
    head_sha: str
    head_branch: str | None
    repository: str
    pr_urls: list[str]  # URLs of related PRs from pull_requests array

    @property
    def ci_status(self) -> str:
        """Map GitHub conclusion to our internal ci_status."""
        if self.action != "completed":
            return "pending"
        if self.conclusion == "success":
            return "success"
        if self.conclusion in ("failure", "timed_out", "action_required", "cancelled"):
            return "failure"
        if self.conclusion in ("neutral", "skipped"):
            return "neutral"
        return "pending"


class GitHubWebhookHandler:
    """Handler for GitHub webhook events.

    Provides:
    - HMAC-SHA256 signature verification
    - Event parsing and validation
    - Idempotent processing via delivery ID
    - Queue-based async processing for heavy operations
    """

    def __init__(
        self,
        webhook_secret: str,
        queue: SupabaseQueueClient | None = None,
    ) -> None:
        """Initialize webhook handler.

        Args:
            webhook_secret: Secret for signature verification.
            queue: Optional queue for async processing.
        """
        self._secret = webhook_secret.encode()
        self._queue = queue
        self._processed_deliveries: set[str] = set()

    def verify_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        """Verify webhook signature using HMAC-SHA256.

        Args:
            payload: Raw request body bytes.
            signature: X-Hub-Signature-256 header value.

        Returns:
            True if signature is valid.

        Raises:
            WebhookVerificationError: If signature is invalid.
        """
        if not signature.startswith("sha256="):
            raise WebhookVerificationError("Invalid signature format")

        expected = hmac.new(
            self._secret,
            payload,
            hashlib.sha256,
        ).hexdigest()

        received = signature.removeprefix("sha256=")

        if not hmac.compare_digest(expected, received):
            raise WebhookVerificationError("Signature verification failed")

        return True

    def parse_event(
        self,
        event_type: str,
        delivery_id: str,
        payload: dict[str, Any],
    ) -> WebhookPayload:
        """Parse raw webhook payload.

        Args:
            event_type: X-GitHub-Event header value.
            delivery_id: X-GitHub-Delivery header value.
            payload: Parsed JSON payload.

        Returns:
            WebhookPayload with parsed data.

        Raises:
            WebhookProcessingError: If event type is not supported.
        """
        try:
            event = GitHubEventType(event_type)
        except ValueError as e:
            raise WebhookProcessingError(f"Unsupported event type: {event_type}") from e

        repository = payload.get("repository", {}).get("full_name", "")
        sender = payload.get("sender", {}).get("login", "")
        action = payload.get("action")

        return WebhookPayload(
            event_type=event,
            action=action,
            delivery_id=delivery_id,
            repository=repository,
            sender_login=sender,
            raw_payload=payload,
        )

    def is_duplicate(self, delivery_id: str) -> bool:
        """Check if delivery has already been processed.

        Args:
            delivery_id: GitHub delivery ID.

        Returns:
            True if already processed.
        """
        return delivery_id in self._processed_deliveries

    def mark_processed(self, delivery_id: str) -> None:
        """Mark delivery as processed.

        Args:
            delivery_id: GitHub delivery ID.
        """
        self._processed_deliveries.add(delivery_id)
        # Keep set bounded (LRU-like behavior)
        if len(self._processed_deliveries) > 10000:
            # Remove oldest entries (first added)
            oldest = list(self._processed_deliveries)[:5000]
            for item in oldest:
                self._processed_deliveries.discard(item)

    def parse_push_event(self, payload: dict[str, Any]) -> ParsedPushEvent:
        """Parse push event payload.

        Args:
            payload: Raw push event payload.

        Returns:
            ParsedPushEvent with commit data.
        """
        return ParsedPushEvent(
            ref=payload.get("ref", ""),
            before_sha=payload.get("before", ""),
            after_sha=payload.get("after", ""),
            commits=payload.get("commits", []),
            repository=payload.get("repository", {}).get("full_name", ""),
            pusher=payload.get("pusher", {}).get("name", ""),
        )

    def parse_pr_event(self, payload: dict[str, Any]) -> ParsedPREvent:
        """Parse pull request event payload.

        Args:
            payload: Raw PR event payload.

        Returns:
            ParsedPREvent with PR data.
        """
        pr = payload.get("pull_request", {})
        action_str = payload.get("action", "")

        # Determine effective action
        try:
            action = GitHubPRAction(action_str)
        except ValueError:
            action = GitHubPRAction.OPENED  # Default

        # Check for merged
        if action == GitHubPRAction.CLOSED and pr.get("merged", False):
            action = GitHubPRAction.MERGED

        return ParsedPREvent(
            action=action,
            number=pr.get("number", 0),
            title=pr.get("title", ""),
            body=pr.get("body"),
            state=pr.get("state", ""),
            merged=pr.get("merged", False),
            head_branch=pr.get("head", {}).get("ref", ""),
            base_branch=pr.get("base", {}).get("ref", ""),
            html_url=pr.get("html_url", ""),
            author_login=pr.get("user", {}).get("login", ""),
            repository=payload.get("repository", {}).get("full_name", ""),
        )

    def parse_check_suite_event(self, payload: dict[str, Any]) -> ParsedCheckSuiteEvent:
        """Parse check_suite event payload.

        Args:
            payload: Raw check_suite event payload.

        Returns:
            ParsedCheckSuiteEvent with CI status data.
        """
        check_suite = payload.get("check_suite", {})
        # Build PR URLs from embedded pull_requests array (may be empty for non-PR pushes)
        pr_urls = [
            pr.get("html_url", "")
            for pr in check_suite.get("pull_requests", [])
            if pr.get("html_url")
        ]
        return ParsedCheckSuiteEvent(
            action=payload.get("action", ""),
            conclusion=check_suite.get("conclusion"),
            head_sha=check_suite.get("head_sha", ""),
            head_branch=check_suite.get("head_branch"),
            repository=payload.get("repository", {}).get("full_name", ""),
            pr_urls=pr_urls,
        )

    async def enqueue_for_processing(
        self,
        workspace_id: UUID,
        integration_id: UUID,
        webhook: WebhookPayload,
    ) -> str | None:
        """Enqueue webhook for async processing.

        Args:
            workspace_id: Workspace UUID.
            integration_id: Integration UUID.
            webhook: Parsed webhook payload.

        Returns:
            Queue message ID or None if no queue configured.
        """
        if not self._queue:
            logger.warning("No queue configured, skipping async processing")
            return None

        queue_payload = {
            "task_type": "github_webhook",
            "workspace_id": str(workspace_id),
            "integration_id": str(integration_id),
            "event_type": webhook.event_type.value,
            "action": webhook.action,
            "delivery_id": webhook.delivery_id,
            "repository": webhook.repository,
            "sender_login": webhook.sender_login,
            "raw_payload": webhook.raw_payload,
            "timestamp": webhook.timestamp.isoformat(),
        }

        return await self._queue.enqueue("ai_normal", queue_payload)


__all__ = [
    "GitHubEventType",
    "GitHubPRAction",
    "GitHubWebhookHandler",
    "ParsedCheckSuiteEvent",
    "ParsedPREvent",
    "ParsedPushEvent",
    "WebhookPayload",
    "WebhookProcessingError",
    "WebhookVerificationError",
]
