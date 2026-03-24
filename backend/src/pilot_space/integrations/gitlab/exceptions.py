"""GitLab API exceptions.

Exception classes for GitLab API errors.
"""

from __future__ import annotations

from typing import Any


class GitLabAPIError(Exception):
    """Base exception for GitLab API errors."""

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


class GitLabRateLimitError(GitLabAPIError):
    """Raised when GitLab rate limit is exceeded."""


class GitLabAuthError(GitLabAPIError):
    """Raised when GitLab authentication fails."""


__all__ = [
    "GitLabAPIError",
    "GitLabAuthError",
    "GitLabRateLimitError",
]
