"""GitHub integration for Pilot Space.

Provides:
- OAuth authentication flow
- Webhook handling for push/PR events
- Commit/PR linking to issues
- Auto-transition on PR events

Components:
- GitHubClient: API client with OAuth and rate limiting
- GitHubWebhookHandler: Webhook signature verification and parsing
- GitHubSyncService: Commit/PR synchronization
"""

from pilot_space.integrations.github.client import (
    GITHUB_API_URL,
    GITHUB_OAUTH_URL,
    GitHubClient,
)
from pilot_space.integrations.github.exceptions import (
    GitHubAPIError,
    GitHubAuthError,
    GitHubRateLimitError,
)
from pilot_space.integrations.github.models import (
    GitHubCommit,
    GitHubPullRequest,
    GitHubRepository,
    GitHubUser,
    RateLimitInfo,
)
from pilot_space.integrations.github.sync import (
    GitHubSyncService,
    IssueReference,
    SyncResult,
)
from pilot_space.integrations.github.webhooks import (
    GitHubEventType,
    GitHubPRAction,
    GitHubWebhookHandler,
    ParsedPREvent,
    ParsedPushEvent,
    WebhookPayload,
    WebhookProcessingError,
    WebhookVerificationError,
)

__all__ = [
    # Client
    "GITHUB_API_URL",
    "GITHUB_OAUTH_URL",
    "GitHubAPIError",
    "GitHubAuthError",
    "GitHubClient",
    "GitHubCommit",
    "GitHubEventType",
    "GitHubPRAction",
    "GitHubPullRequest",
    "GitHubRateLimitError",
    "GitHubRepository",
    "GitHubSyncService",
    "GitHubUser",
    "GitHubWebhookHandler",
    "IssueReference",
    "ParsedPREvent",
    "ParsedPushEvent",
    "RateLimitInfo",
    "SyncResult",
    "WebhookPayload",
    "WebhookProcessingError",
    "WebhookVerificationError",
]
