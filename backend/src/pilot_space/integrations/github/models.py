"""GitHub API data models.

Data classes for GitHub API responses.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class GitHubUser:
    """GitHub user profile."""

    id: int
    login: str
    name: str | None
    email: str | None
    avatar_url: str


@dataclass
class GitHubRepository:
    """GitHub repository information."""

    id: int
    name: str
    full_name: str
    private: bool
    default_branch: str
    description: str | None
    html_url: str


@dataclass
class GitHubCommit:
    """GitHub commit information."""

    sha: str
    message: str
    author_name: str
    author_email: str
    author_avatar_url: str | None
    html_url: str
    timestamp: datetime
    additions: int = 0
    deletions: int = 0
    files_changed: int = 0


@dataclass
class GitHubPullRequest:
    """GitHub pull request information."""

    number: int
    title: str
    body: str | None
    state: str  # open, closed
    merged: bool
    merged_at: datetime | None
    html_url: str
    head_branch: str
    base_branch: str
    author_login: str
    author_avatar_url: str | None
    additions: int = 0
    deletions: int = 0
    changed_files: int = 0


@dataclass
class RateLimitInfo:
    """GitHub rate limit information."""

    limit: int
    remaining: int
    reset_at: datetime
    used: int = 0


__all__ = [
    "GitHubCommit",
    "GitHubPullRequest",
    "GitHubRepository",
    "GitHubUser",
    "RateLimitInfo",
]
