"""GitHub API exceptions.

Exception classes for GitHub API errors.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


class GitHubAPIError(Exception):
    """Base exception for GitHub API errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: dict[str, Any] | None = None,
    ) -> None:
        """Initialize error.

        Args:
            message: Error message.
            status_code: HTTP status code (optional).
            response_body: Response body (optional).
        """
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body or {}


class GitHubRateLimitError(GitHubAPIError):
    """Raised when GitHub rate limit is exceeded."""

    def __init__(
        self,
        reset_at: datetime,
        remaining: int = 0,
    ) -> None:
        """Initialize rate limit error.

        Args:
            reset_at: When rate limit resets.
            remaining: Remaining requests.
        """
        super().__init__(
            f"GitHub rate limit exceeded. Resets at {reset_at.isoformat()}",
            status_code=429,
        )
        self.reset_at = reset_at
        self.remaining = remaining


class GitHubAuthError(GitHubAPIError):
    """Raised when GitHub authentication fails."""


__all__ = [
    "GitHubAPIError",
    "GitHubAuthError",
    "GitHubRateLimitError",
]
