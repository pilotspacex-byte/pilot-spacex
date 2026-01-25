"""Integration services for GitHub/Slack.

Services:
- ConnectGitHubService: OAuth connection flow
- ProcessGitHubWebhookService: Webhook processing
- LinkCommitService: Commit-issue linking
- AutoTransitionService: Auto-transition based on PR events
- CommitScannerService: Scheduled commit scanning
"""

from pilot_space.application.services.integration.auto_transition_service import (
    AutoTransitionPayload,
    AutoTransitionResult,
    AutoTransitionService,
)
from pilot_space.application.services.integration.connect_github_service import (
    ConnectGitHubPayload,
    ConnectGitHubResult,
    ConnectGitHubService,
)
from pilot_space.application.services.integration.link_commit_service import (
    LinkCommitPayload,
    LinkCommitResult,
    LinkCommitService,
    LinkPullRequestPayload,
    LinkPullRequestResult,
)
from pilot_space.application.services.integration.process_webhook_service import (
    ProcessGitHubWebhookService,
    ProcessWebhookPayload,
    ProcessWebhookResult,
)

__all__ = [
    "AutoTransitionPayload",
    "AutoTransitionResult",
    "AutoTransitionService",
    "ConnectGitHubPayload",
    "ConnectGitHubResult",
    "ConnectGitHubService",
    "LinkCommitPayload",
    "LinkCommitResult",
    "LinkCommitService",
    "LinkPullRequestPayload",
    "LinkPullRequestResult",
    "ProcessGitHubWebhookService",
    "ProcessWebhookPayload",
    "ProcessWebhookResult",
]
