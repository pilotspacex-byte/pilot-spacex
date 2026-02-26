"""Unit tests for ProcessGitHubWebhookService.

All dependencies mocked with AsyncMock / MagicMock.
Uses pytest-asyncio (asyncio_mode="auto" in pyproject.toml).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from pilot_space.application.services.integration.process_webhook_service import (
    ProcessGitHubWebhookService,
    ProcessWebhookPayload,
    ProcessWebhookResult,
)
from pilot_space.integrations.github.webhooks import (
    GitHubEventType,
    GitHubPRAction,
    GitHubWebhookHandler,
    ParsedPREvent,
    ParsedPushEvent,
    WebhookPayload,
    WebhookProcessingError,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_webhook_payload(
    event_type: str = "push",
    delivery_id: str = "delivery-001",
    raw: dict[str, Any] | None = None,
    signature: str = "sha256=abc",
) -> ProcessWebhookPayload:
    if raw is None:
        raw = {
            "repository": {"full_name": "acme/api"},
            "sender": {"login": "alice"},
            "installation": {"id": "inst-1"},
        }
    return ProcessWebhookPayload(
        event_type=event_type,
        delivery_id=delivery_id,
        payload=raw,
        signature=signature,
    )


def _make_parsed_webhook(
    event_type: GitHubEventType = GitHubEventType.PUSH,
    delivery_id: str = "delivery-001",
    repository: str = "acme/api",
    action: str | None = None,
    raw: dict[str, Any] | None = None,
) -> WebhookPayload:
    from datetime import UTC, datetime

    return WebhookPayload(
        event_type=event_type,
        action=action,
        delivery_id=delivery_id,
        repository=repository,
        sender_login="alice",
        raw_payload=raw
        or {"repository": {"full_name": repository}, "installation": {"id": "inst-1"}},
        timestamp=datetime.now(tz=UTC),
    )


def _make_push_event(commits: list[dict[str, Any]] | None = None) -> ParsedPushEvent:
    return ParsedPushEvent(
        ref="refs/heads/main",
        before_sha="abc",
        after_sha="def",
        commits=commits or [{"id": "def456", "message": "fix: something"}],
        repository="acme/api",
        pusher="alice",
    )


def _make_pr_event(
    action: GitHubPRAction = GitHubPRAction.OPENED,
    merged: bool = False,
    title: str = "feat: add login",
    body: str | None = None,
) -> ParsedPREvent:
    return ParsedPREvent(
        action=action,
        number=42,
        title=title,
        body=body,
        state="closed" if action == GitHubPRAction.MERGED else "open",
        merged=merged,
        head_branch="feat/login",
        base_branch="main",
        html_url="https://github.com/acme/api/pull/42",
        author_login="alice",
        repository="acme/api",
    )


def _make_integration(workspace_id: Any = None, integration_id: Any = None) -> MagicMock:
    m = MagicMock()
    m.workspace_id = workspace_id or uuid4()
    m.id = integration_id or uuid4()
    return m


def _make_service(
    *,
    handler: GitHubWebhookHandler | None = None,
    sync_service: Any = None,
    integration_repo: Any = None,
    integration_link_repo: Any = None,
    issue_repo: Any = None,
    activity_repo: Any = None,
    session: Any = None,
) -> ProcessGitHubWebhookService:
    return ProcessGitHubWebhookService(
        session=session or MagicMock(),
        integration_repo=integration_repo or AsyncMock(),
        integration_link_repo=integration_link_repo or AsyncMock(),
        issue_repo=issue_repo or AsyncMock(),
        activity_repo=activity_repo or AsyncMock(),
        webhook_handler=handler or MagicMock(spec=GitHubWebhookHandler),
        sync_service=sync_service or AsyncMock(),
    )


# ---------------------------------------------------------------------------
# execute() — routing and duplicate detection
# ---------------------------------------------------------------------------


class TestExecuteDuplicateAndParsing:
    async def test_duplicate_delivery_returns_not_processed(self) -> None:
        handler = MagicMock(spec=GitHubWebhookHandler)
        handler.is_duplicate.return_value = True

        svc = _make_service(handler=handler)
        result = await svc.execute(_make_webhook_payload())

        assert result.processed is False
        assert result.error == "Duplicate delivery"
        handler.mark_processed.assert_not_called()

    async def test_parse_failure_returns_error(self) -> None:
        handler = MagicMock(spec=GitHubWebhookHandler)
        handler.is_duplicate.return_value = False
        handler.parse_event.side_effect = WebhookProcessingError("bad event")

        svc = _make_service(handler=handler)
        result = await svc.execute(_make_webhook_payload(event_type="star"))

        assert result.processed is False
        assert result.error is not None
        assert "bad event" in result.error

    async def test_push_event_routes_to_handle_push(self) -> None:
        handler = MagicMock(spec=GitHubWebhookHandler)
        handler.is_duplicate.return_value = False
        handler.parse_event.return_value = _make_parsed_webhook(event_type=GitHubEventType.PUSH)

        svc = _make_service(handler=handler)
        # Patch internal handler to be a no-op so we don't need DB
        svc._handle_push = AsyncMock()  # type: ignore[method-assign]
        await svc.execute(_make_webhook_payload(event_type="push"))

        svc._handle_push.assert_awaited_once()

    async def test_pr_event_routes_to_handle_pull_request(self) -> None:
        handler = MagicMock(spec=GitHubWebhookHandler)
        handler.is_duplicate.return_value = False
        handler.parse_event.return_value = _make_parsed_webhook(
            event_type=GitHubEventType.PULL_REQUEST, action="opened"
        )

        svc = _make_service(handler=handler)
        svc._handle_pull_request = AsyncMock()  # type: ignore[method-assign]
        await svc.execute(_make_webhook_payload(event_type="pull_request"))

        svc._handle_pull_request.assert_awaited_once()

    async def test_successful_execution_marks_processed(self) -> None:
        handler = MagicMock(spec=GitHubWebhookHandler)
        handler.is_duplicate.return_value = False
        handler.parse_event.return_value = _make_parsed_webhook(event_type=GitHubEventType.PUSH)

        svc = _make_service(handler=handler)
        svc._handle_push = AsyncMock()  # type: ignore[method-assign]
        result = await svc.execute(_make_webhook_payload())

        assert result.processed is True
        handler.mark_processed.assert_called_once_with("delivery-001")


# ---------------------------------------------------------------------------
# _handle_push()
# ---------------------------------------------------------------------------


class TestHandlePush:
    async def test_no_integration_sets_error(self) -> None:
        integration_repo = AsyncMock()
        integration_repo.get_by_external_account.return_value = []

        handler = MagicMock(spec=GitHubWebhookHandler)
        svc = _make_service(handler=handler, integration_repo=integration_repo)

        result = ProcessWebhookResult()
        raw = {
            "repository": {"full_name": "acme/api"},
            "installation": {"id": "inst-1"},
        }
        await svc._handle_push(raw, result)

        assert result.error == "No matching integration found"

    async def test_no_integration_sets_processed_false(self) -> None:
        """Regression: _handle_push must set processed=False, not only error.

        ProcessWebhookResult defaults processed=True; when no integration is
        found the method must flip it to False so execute() never calls
        mark_processed on a delivery that wasn't actually handled.
        """
        integration_repo = AsyncMock()
        integration_repo.get_by_external_account.return_value = []

        handler = MagicMock(spec=GitHubWebhookHandler)
        svc = _make_service(handler=handler, integration_repo=integration_repo)

        result = ProcessWebhookResult()
        assert result.processed is True  # default

        raw = {
            "repository": {"full_name": "acme/api"},
            "installation": {"id": "inst-1"},
        }
        await svc._handle_push(raw, result)

        assert result.processed is False, (
            "_handle_push must set processed=False when no integration is found"
        )

    async def test_happy_path_calls_sync_service(self) -> None:
        from pilot_space.integrations.github.sync import SyncResult

        integration = _make_integration()
        integration_repo = AsyncMock()
        integration_repo.get_by_external_account.return_value = [integration]

        # sync_push_event is async; extract_issue_refs is synchronous — use MagicMock
        sync_service = AsyncMock()
        sync_service.sync_push_event.return_value = SyncResult(links_created=2, issues_matched=1)
        # extract_issue_refs is a regular (non-async) method
        sync_service.extract_issue_refs = MagicMock(return_value=[])

        handler = MagicMock(spec=GitHubWebhookHandler)
        handler.parse_push_event.return_value = _make_push_event()

        svc = _make_service(
            handler=handler,
            integration_repo=integration_repo,
            sync_service=sync_service,
        )

        result = ProcessWebhookResult()
        raw = {
            "repository": {"full_name": "acme/api"},
            "installation": {"id": "inst-1"},
            "ref": "refs/heads/main",
            "before": "abc",
            "after": "def",
            "commits": [{"id": "def456", "message": "fix: something"}],
            "pusher": {"name": "alice"},
        }
        await svc._handle_push(raw, result)

        sync_service.sync_push_event.assert_awaited_once()
        assert result.links_created == 2

    async def test_skips_branch_delete(self) -> None:
        integration = _make_integration()
        integration_repo = AsyncMock()
        integration_repo.get_by_external_account.return_value = [integration]

        sync_service = AsyncMock()
        handler = MagicMock(spec=GitHubWebhookHandler)
        # Return a branch-delete push event
        delete_push = ParsedPushEvent(
            ref="refs/heads/old-branch",
            before_sha="abc",
            after_sha="0" * 40,
            commits=[],
            repository="acme/api",
            pusher="alice",
        )
        handler.parse_push_event.return_value = delete_push

        svc = _make_service(
            handler=handler,
            integration_repo=integration_repo,
            sync_service=sync_service,
        )
        result = ProcessWebhookResult()
        raw = {
            "repository": {"full_name": "acme/api"},
            "installation": {"id": "inst-1"},
        }
        await svc._handle_push(raw, result)

        sync_service.sync_push_event.assert_not_awaited()


# ---------------------------------------------------------------------------
# _handle_pull_request()
# ---------------------------------------------------------------------------


class TestHandlePullRequest:
    async def test_no_integration_sets_error(self) -> None:
        integration_repo = AsyncMock()
        integration_repo.get_by_external_account.return_value = []

        svc = _make_service(integration_repo=integration_repo)
        result = ProcessWebhookResult()
        raw = {
            "repository": {"full_name": "acme/api"},
            "installation": {"id": "inst-1"},
            "action": "opened",
            "pull_request": {},
        }
        await svc._handle_pull_request(raw, result)

        assert result.error == "No matching integration found"

    async def test_happy_path_calls_sync_service(self) -> None:
        from pilot_space.integrations.github.sync import SyncResult

        integration = _make_integration()
        integration_repo = AsyncMock()
        integration_repo.get_by_external_account.return_value = [integration]

        sync_service = AsyncMock()
        sync_service.sync_pr_event.return_value = SyncResult(links_created=1)

        handler = MagicMock(spec=GitHubWebhookHandler)
        handler.parse_pr_event.return_value = _make_pr_event()

        svc = _make_service(
            handler=handler,
            integration_repo=integration_repo,
            sync_service=sync_service,
        )
        result = ProcessWebhookResult()
        raw = {
            "repository": {"full_name": "acme/api"},
            "installation": {"id": "inst-1"},
            "action": "opened",
            "pull_request": {
                "number": 42,
                "title": "feat: add login",
                "body": None,
                "state": "open",
                "merged": False,
                "head": {"ref": "feat/login"},
                "base": {"ref": "main"},
                "html_url": "https://github.com/acme/api/pull/42",
                "user": {"login": "alice"},
            },
        }
        await svc._handle_pull_request(raw, result)

        sync_service.sync_pr_event.assert_awaited_once()

    async def test_merged_pr_with_closing_ref_triggers_handle_pr_merged(self) -> None:
        from pilot_space.integrations.github.sync import SyncResult

        integration = _make_integration()
        integration_repo = AsyncMock()
        integration_repo.get_by_external_account.return_value = [integration]

        sync_service = AsyncMock()
        sync_service.sync_pr_event.return_value = SyncResult(links_created=1)

        merged_pr = _make_pr_event(
            action=GitHubPRAction.MERGED,
            merged=True,
            title="Fixes PS-42",
        )
        handler = MagicMock(spec=GitHubWebhookHandler)
        handler.parse_pr_event.return_value = merged_pr

        svc = _make_service(
            handler=handler,
            integration_repo=integration_repo,
            sync_service=sync_service,
        )
        svc._handle_pr_merged = AsyncMock()  # type: ignore[method-assign]

        raw = {
            "repository": {"full_name": "acme/api"},
            "installation": {"id": "inst-1"},
            "action": "closed",
            "pull_request": {
                "number": 42,
                "title": "Fixes PS-42",
                "body": None,
                "state": "closed",
                "merged": True,
                "head": {"ref": "feat/x"},
                "base": {"ref": "main"},
                "html_url": "https://github.com/acme/api/pull/42",
                "user": {"login": "alice"},
            },
        }
        result = ProcessWebhookResult()
        await svc._handle_pull_request(raw, result)

        svc._handle_pr_merged.assert_awaited_once()

    async def test_non_merged_pr_does_not_call_handle_pr_merged(self) -> None:
        from pilot_space.integrations.github.sync import SyncResult

        integration = _make_integration()
        integration_repo = AsyncMock()
        integration_repo.get_by_external_account.return_value = [integration]

        sync_service = AsyncMock()
        sync_service.sync_pr_event.return_value = SyncResult(links_created=1)

        opened_pr = _make_pr_event(action=GitHubPRAction.OPENED)
        handler = MagicMock(spec=GitHubWebhookHandler)
        handler.parse_pr_event.return_value = opened_pr

        svc = _make_service(
            handler=handler,
            integration_repo=integration_repo,
            sync_service=sync_service,
        )
        svc._handle_pr_merged = AsyncMock()  # type: ignore[method-assign]

        raw = {
            "repository": {"full_name": "acme/api"},
            "installation": {"id": "inst-1"},
            "action": "opened",
            "pull_request": {
                "number": 42,
                "title": "feat: something",
                "body": None,
                "state": "open",
                "merged": False,
                "head": {"ref": "feat/x"},
                "base": {"ref": "main"},
                "html_url": "https://github.com/acme/api/pull/42",
                "user": {"login": "alice"},
            },
        }
        result = ProcessWebhookResult()
        await svc._handle_pull_request(raw, result)

        svc._handle_pr_merged.assert_not_awaited()


# ---------------------------------------------------------------------------
# _handle_pr_review() — graceful skip
# ---------------------------------------------------------------------------


class TestHandlePRReview:
    async def test_pr_review_event_does_not_set_error(self) -> None:
        svc = _make_service()
        result = ProcessWebhookResult()
        raw = {
            "action": "submitted",
            "review": {"state": "approved"},
            "repository": {"full_name": "acme/api"},
        }
        # Should complete without exception and leave result.processed=True
        await svc._handle_pr_review(raw, result)
        assert result.error is None


# ---------------------------------------------------------------------------
# End-to-end: execute() calls mark_processed after push
# ---------------------------------------------------------------------------


class TestExecuteMarkProcessed:
    async def test_mark_processed_called_after_successful_push(self) -> None:
        from pilot_space.integrations.github.sync import SyncResult

        integration = _make_integration()
        integration_repo = AsyncMock()
        integration_repo.get_by_external_account.return_value = [integration]

        sync_service = AsyncMock()
        sync_service.sync_push_event.return_value = SyncResult(links_created=1)
        # extract_issue_refs is synchronous
        sync_service.extract_issue_refs = MagicMock(return_value=[])

        raw = {
            "repository": {"full_name": "acme/api"},
            "installation": {"id": "inst-1"},
            "ref": "refs/heads/main",
            "before": "abc",
            "after": "def",
            "commits": [{"id": "def456", "message": "chore: bump version"}],
            "pusher": {"name": "alice"},
            "sender": {"login": "alice"},
        }

        handler = GitHubWebhookHandler(webhook_secret="test-secret")
        handler.parse_push_event = MagicMock(return_value=_make_push_event())  # type: ignore[method-assign]

        svc = _make_service(
            handler=handler,
            integration_repo=integration_repo,
            sync_service=sync_service,
        )

        webhook_input = ProcessWebhookPayload(
            event_type="push",
            delivery_id="e2e-delivery-001",
            payload=raw,
            signature="sha256=ignored",
        )

        result = await svc.execute(webhook_input)

        assert result.processed is True
        assert handler.is_duplicate("e2e-delivery-001") is True
