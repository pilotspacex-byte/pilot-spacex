"""Unit tests for GitHubWebhookHandler.

Covers signature verification, event parsing, and idempotency tracking.
"""

from __future__ import annotations

import hashlib
import hmac
from unittest.mock import patch

import pytest

from pilot_space.integrations.github.webhooks import (
    GitHubEventType,
    GitHubPRAction,
    GitHubWebhookHandler,
    ParsedPREvent,
    ParsedPushEvent,
    WebhookProcessingError,
    WebhookVerificationError,
)

SECRET = "test-webhook-secret"  # pragma: allowlist secret


def _make_signature(secret: str, payload: bytes) -> str:
    """Generate valid HMAC-SHA256 signature for payload."""
    digest = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


@pytest.fixture
def handler() -> GitHubWebhookHandler:
    return GitHubWebhookHandler(webhook_secret=SECRET)


# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------


class TestVerifySignature:
    def test_valid_signature_returns_true(self, handler: GitHubWebhookHandler) -> None:
        payload = b'{"action": "opened"}'
        sig = _make_signature(SECRET, payload)
        assert handler.verify_signature(payload, sig) is True

    def test_invalid_signature_raises(self, handler: GitHubWebhookHandler) -> None:
        payload = b'{"action": "opened"}'
        bad_sig = "sha256=" + "a" * 64
        with pytest.raises(WebhookVerificationError, match="Signature verification failed"):
            handler.verify_signature(payload, bad_sig)

    def test_missing_sha256_prefix_raises(self, handler: GitHubWebhookHandler) -> None:
        payload = b'{"action": "opened"}'
        # Provide a raw hex digest without the "sha256=" prefix
        raw_digest = hmac.new(SECRET.encode(), payload, hashlib.sha256).hexdigest()
        with pytest.raises(WebhookVerificationError, match="Invalid signature format"):
            handler.verify_signature(payload, raw_digest)

    def test_empty_payload_with_correct_hmac_passes(self, handler: GitHubWebhookHandler) -> None:
        payload = b""
        sig = _make_signature(SECRET, payload)
        assert handler.verify_signature(payload, sig) is True

    def test_uses_hmac_compare_digest(self, handler: GitHubWebhookHandler) -> None:
        payload = b'{"ping": true}'
        sig = _make_signature(SECRET, payload)
        with patch("pilot_space.integrations.github.webhooks.hmac.compare_digest") as mock_cd:
            mock_cd.return_value = True
            result = handler.verify_signature(payload, sig)
        mock_cd.assert_called_once()
        assert result is True


# ---------------------------------------------------------------------------
# Event parsing
# ---------------------------------------------------------------------------


class TestParseEvent:
    def test_push_event_returns_webhook_payload(self, handler: GitHubWebhookHandler) -> None:
        raw = {
            "repository": {"full_name": "acme/api"},
            "sender": {"login": "alice"},
        }
        wh = handler.parse_event(
            event_type="push",
            delivery_id="delivery-001",
            payload=raw,
        )
        assert wh.event_type == GitHubEventType.PUSH
        assert wh.delivery_id == "delivery-001"
        assert wh.repository == "acme/api"
        assert wh.sender_login == "alice"
        assert wh.action is None

    def test_pull_request_event_parsed_with_action(self, handler: GitHubWebhookHandler) -> None:
        raw = {
            "action": "opened",
            "repository": {"full_name": "acme/api"},
            "sender": {"login": "bob"},
        }
        wh = handler.parse_event(
            event_type="pull_request",
            delivery_id="delivery-002",
            payload=raw,
        )
        assert wh.event_type == GitHubEventType.PULL_REQUEST
        assert wh.action == "opened"
        assert wh.repository == "acme/api"

    def test_unsupported_event_type_raises(self, handler: GitHubWebhookHandler) -> None:
        raw = {"repository": {"full_name": "acme/api"}, "sender": {"login": "bot"}}
        with pytest.raises(WebhookProcessingError, match="Unsupported event type"):
            handler.parse_event(
                event_type="star",
                delivery_id="delivery-003",
                payload=raw,
            )


# ---------------------------------------------------------------------------
# Push event parsing
# ---------------------------------------------------------------------------


class TestParsePushEvent:
    def test_parse_push_event_fields(self, handler: GitHubWebhookHandler) -> None:
        raw = {
            "ref": "refs/heads/main",
            "before": "abc123",
            "after": "def456",
            "commits": [{"id": "def456", "message": "fix: something"}],
            "repository": {"full_name": "acme/api"},
            "pusher": {"name": "alice"},
        }
        push = handler.parse_push_event(raw)
        assert isinstance(push, ParsedPushEvent)
        assert push.branch == "main"
        assert push.before_sha == "abc123"
        assert push.after_sha == "def456"
        assert len(push.commits) == 1
        assert push.pusher == "alice"

    def test_branch_delete_detected(self, handler: GitHubWebhookHandler) -> None:
        raw = {
            "ref": "refs/heads/feature-x",
            "before": "abc123",
            "after": "0" * 40,
            "commits": [],
            "repository": {"full_name": "acme/api"},
            "pusher": {"name": "alice"},
        }
        push = handler.parse_push_event(raw)
        assert push.is_branch_delete is True


# ---------------------------------------------------------------------------
# PR event parsing
# ---------------------------------------------------------------------------


class TestParsePREvent:
    def test_parse_pr_opened(self, handler: GitHubWebhookHandler) -> None:
        raw = {
            "action": "opened",
            "pull_request": {
                "number": 42,
                "title": "feat: add login",
                "body": "Implements login flow",
                "state": "open",
                "merged": False,
                "head": {"ref": "feat/login"},
                "base": {"ref": "main"},
                "html_url": "https://github.com/acme/api/pull/42",
                "user": {"login": "alice"},
            },
            "repository": {"full_name": "acme/api"},
        }
        pr = handler.parse_pr_event(raw)
        assert isinstance(pr, ParsedPREvent)
        assert pr.number == 42
        assert pr.action == GitHubPRAction.OPENED
        assert pr.merged is False
        assert pr.author_login == "alice"
        assert pr.repository == "acme/api"

    def test_closed_and_merged_action_becomes_merged(self, handler: GitHubWebhookHandler) -> None:
        raw = {
            "action": "closed",
            "pull_request": {
                "number": 7,
                "title": "Fixes PS-1",
                "body": None,
                "state": "closed",
                "merged": True,
                "head": {"ref": "feat/x"},
                "base": {"ref": "main"},
                "html_url": "https://github.com/acme/api/pull/7",
                "user": {"login": "bob"},
            },
            "repository": {"full_name": "acme/api"},
        }
        pr = handler.parse_pr_event(raw)
        assert pr.action == GitHubPRAction.MERGED
        assert pr.merged is True


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


class TestIdempotency:
    def test_new_delivery_not_duplicate(self, handler: GitHubWebhookHandler) -> None:
        assert handler.is_duplicate("new-id-xyz") is False

    def test_repeated_delivery_is_duplicate(self, handler: GitHubWebhookHandler) -> None:
        handler.mark_processed("delivery-abc")
        assert handler.is_duplicate("delivery-abc") is True

    def test_mark_then_check_round_trip(self, handler: GitHubWebhookHandler) -> None:
        delivery = "round-trip-id"
        assert handler.is_duplicate(delivery) is False
        handler.mark_processed(delivery)
        assert handler.is_duplicate(delivery) is True
