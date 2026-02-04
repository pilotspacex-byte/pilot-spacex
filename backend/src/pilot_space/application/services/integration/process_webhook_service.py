"""Process GitHub webhook service.

T182: Create ProcessGitHubWebhookService for handling webhook events.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pilot_space.integrations.github.webhooks import (
    GitHubEventType,
    GitHubPRAction,
    GitHubWebhookHandler,
)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.repositories import (
        ActivityRepository,
        IntegrationLinkRepository,
        IntegrationRepository,
        IssueRepository,
    )
    from pilot_space.integrations.github.sync import GitHubSyncService

logger = logging.getLogger(__name__)


@dataclass
class ProcessWebhookPayload:
    """Payload for processing GitHub webhook.

    Attributes:
        event_type: GitHub event type.
        delivery_id: Unique delivery ID.
        payload: Raw webhook payload.
        signature: X-Hub-Signature-256 header.
    """

    event_type: str
    delivery_id: str
    payload: dict[str, Any]
    signature: str


@dataclass
class ProcessWebhookResult:
    """Result from webhook processing."""

    processed: bool = True
    event_type: str = ""
    action: str | None = None
    links_created: int = 0
    issues_affected: list[str] = field(default_factory=list)
    auto_transitioned: list[str] = field(default_factory=list)
    error: str | None = None


class ProcessGitHubWebhookService:
    """Service for processing GitHub webhooks.

    Handles:
    - Signature verification
    - Event routing
    - Push event processing (commit linking)
    - PR event processing (linking + auto-transition)
    - Idempotent processing via delivery ID
    """

    def __init__(
        self,
        session: AsyncSession,
        integration_repo: IntegrationRepository,
        integration_link_repo: IntegrationLinkRepository,
        issue_repo: IssueRepository,
        activity_repo: ActivityRepository,
        webhook_handler: GitHubWebhookHandler,
        sync_service: GitHubSyncService,
    ) -> None:
        """Initialize service.

        Args:
            session: Async database session.
            integration_repo: Integration repository.
            integration_link_repo: IntegrationLink repository.
            issue_repo: Issue repository.
            activity_repo: Activity repository.
            webhook_handler: Webhook handler.
            sync_service: GitHub sync service.
        """
        self._session = session
        self._integration_repo = integration_repo
        self._link_repo = integration_link_repo
        self._issue_repo = issue_repo
        self._activity_repo = activity_repo
        self._webhook_handler = webhook_handler
        self._sync_service = sync_service

    async def execute(self, payload: ProcessWebhookPayload) -> ProcessWebhookResult:
        """Process a GitHub webhook event.

        Args:
            payload: Webhook payload.

        Returns:
            ProcessWebhookResult with processing status.
        """
        # Check for duplicate delivery
        if self._webhook_handler.is_duplicate(payload.delivery_id):
            logger.info(
                "Duplicate webhook delivery",
                extra={"delivery_id": payload.delivery_id},
            )
            return ProcessWebhookResult(
                processed=False,
                error="Duplicate delivery",
            )

        # Parse event
        try:
            webhook = self._webhook_handler.parse_event(
                event_type=payload.event_type,
                delivery_id=payload.delivery_id,
                payload=payload.payload,
            )
        except Exception as e:
            logger.exception("Failed to parse webhook")
            return ProcessWebhookResult(
                processed=False,
                error=f"Failed to parse: {e}",
            )

        logger.info(
            "Processing GitHub webhook",
            extra={
                "event_type": webhook.event_type.value,
                "action": webhook.action,
                "delivery_id": webhook.delivery_id,
                "repository": webhook.repository,
            },
        )

        # Find integration by repository/account
        repo_parts = webhook.repository.split("/")
        if len(repo_parts) < 2:
            return ProcessWebhookResult(
                processed=False,
                error="Invalid repository format",
            )

        # Route to appropriate handler
        result = ProcessWebhookResult(
            event_type=webhook.event_type.value,
            action=webhook.action,
        )

        try:
            if webhook.event_type == GitHubEventType.PUSH:
                await self._handle_push(webhook.raw_payload, result)
            elif webhook.event_type == GitHubEventType.PULL_REQUEST:
                await self._handle_pull_request(webhook.raw_payload, result)
            elif webhook.event_type == GitHubEventType.PULL_REQUEST_REVIEW:
                await self._handle_pr_review(webhook.raw_payload, result)
            else:
                result.processed = False
                result.error = f"Unhandled event type: {webhook.event_type}"
        except Exception as e:
            logger.exception("Error processing webhook")
            result.processed = False
            result.error = str(e)

        # Mark as processed if successful
        if result.processed:
            self._webhook_handler.mark_processed(payload.delivery_id)

        return result

    async def _handle_push(
        self,
        payload: dict[str, Any],
        result: ProcessWebhookResult,
    ) -> None:
        """Handle push event (commits).

        Args:
            payload: Push event payload.
            result: Result to update.
        """
        # Get installation/account info from payload
        installation_id = str(payload.get("installation", {}).get("id", ""))
        repository = payload.get("repository", {}).get("full_name", "")

        if not installation_id and not repository:
            result.error = "No installation or repository info"
            return

        # Find integrations for this repo
        # For now, search by external_account_name matching repo owner
        repo_owner = repository.split("/")[0] if "/" in repository else ""

        from pilot_space.infrastructure.database.models import IntegrationProvider

        integrations = await self._integration_repo.get_by_external_account(
            provider=IntegrationProvider.GITHUB,
            external_account_id=installation_id or repo_owner,
        )

        if not integrations:
            # Try by account name
            logger.warning(f"No integrations found for {installation_id or repo_owner}")
            result.error = "No matching integration found"
            return

        # Parse push event
        push = self._webhook_handler.parse_push_event(payload)

        if push.is_branch_delete:
            # Skip branch deletions
            return

        # Process for each workspace
        for integration in integrations:
            sync_result = await self._sync_service.sync_push_event(
                workspace_id=integration.workspace_id,
                integration_id=integration.id,
                push=push,
            )

            result.links_created += sync_result.links_created
            if sync_result.issues_matched > 0:
                # Collect affected issue IDs
                for commit in push.commits:
                    refs = self._sync_service.extract_issue_refs(commit.get("message", ""))
                    for ref in refs:
                        result.issues_affected.append(ref.identifier)

    async def _handle_pull_request(
        self,
        payload: dict[str, Any],
        result: ProcessWebhookResult,
    ) -> None:
        """Handle pull request event.

        Args:
            payload: PR event payload.
            result: Result to update.
        """
        installation_id = str(payload.get("installation", {}).get("id", ""))
        repository = payload.get("repository", {}).get("full_name", "")
        repo_owner = repository.split("/")[0] if "/" in repository else ""

        from pilot_space.infrastructure.database.models import IntegrationProvider

        integrations = await self._integration_repo.get_by_external_account(
            provider=IntegrationProvider.GITHUB,
            external_account_id=installation_id or repo_owner,
        )

        if not integrations:
            result.error = "No matching integration found"
            return

        # Parse PR event
        pr = self._webhook_handler.parse_pr_event(payload)

        for integration in integrations:
            # Sync PR link
            sync_result = await self._sync_service.sync_pr_event(
                workspace_id=integration.workspace_id,
                integration_id=integration.id,
                pr=pr,
            )

            result.links_created += sync_result.links_created

            # Handle auto-transition for merged PRs
            if pr.action == GitHubPRAction.MERGED:
                await self._handle_pr_merged(integration.workspace_id, pr, result)

    async def _handle_pr_merged(
        self,
        workspace_id: UUID,
        pr: Any,  # ParsedPREvent
        result: ProcessWebhookResult,
    ) -> None:
        """Handle PR merged event for auto-transition.

        Args:
            workspace_id: Workspace UUID.
            pr: Parsed PR event.
            result: Result to update.
        """
        # Extract issue refs that should be closed
        text = f"{pr.title}\n{pr.body or ''}"
        refs = self._sync_service.extract_issue_refs(text)

        from pilot_space.infrastructure.database.models import StateGroup

        for ref in refs:
            if not ref.is_closing:
                continue

            # Find issue
            issue = await self._issue_repo.get_by_identifier(
                workspace_id=workspace_id,
                project_identifier=ref.project_identifier,
                sequence_id=ref.sequence_id,
            )

            if not issue:
                continue

            # Skip if already completed
            if issue.state and issue.state.group in (
                StateGroup.COMPLETED,
                StateGroup.CANCELLED,
            ):
                continue

            # Auto-transition to done
            # Find "Done" state for this project
            from sqlalchemy import and_, select

            from pilot_space.infrastructure.database.models import State

            done_query = (
                select(State)
                .where(
                    and_(
                        State.project_id == issue.project_id,
                        State.group == StateGroup.COMPLETED,
                        State.is_deleted == False,  # noqa: E712
                    )
                )
                .limit(1)
            )

            done_result = await self._session.execute(done_query)
            done_state = done_result.scalar_one_or_none()

            if done_state:
                from pilot_space.infrastructure.database.models import Activity, ActivityType

                old_state = issue.state
                issue.state_id = done_state.id
                await self._session.flush()

                # Record activity
                activity = Activity(
                    workspace_id=workspace_id,
                    issue_id=issue.id,
                    actor_id=None,  # System action
                    activity_type=ActivityType.STATE_CHANGED,
                    field="state",
                    old_value=old_state.name if old_state else None,
                    new_value=done_state.name,
                    activity_metadata={
                        "auto_transition": True,
                        "trigger": "pr_merged",
                        "pr_number": pr.number,
                        "pr_title": pr.title,
                    },
                )
                self._session.add(activity)
                await self._session.flush()

                result.auto_transitioned.append(ref.identifier)

    async def _handle_pr_review(
        self,
        payload: dict[str, Any],
        _result: ProcessWebhookResult,
    ) -> None:
        """Handle PR review event.

        Args:
            payload: PR review event payload.
            _result: Result to update (unused for now).
        """
        # For now, just log the event
        # Could be used for notification or tracking
        action = payload.get("action", "")
        review_state = payload.get("review", {}).get("state", "")

        logger.info(
            "PR review event",
            extra={
                "action": action,
                "review_state": review_state,
            },
        )


__all__ = [
    "ProcessGitHubWebhookService",
    "ProcessWebhookPayload",
    "ProcessWebhookResult",
]
