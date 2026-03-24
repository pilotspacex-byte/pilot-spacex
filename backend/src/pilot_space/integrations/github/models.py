"""GitHub API data models.

Data classes for GitHub API responses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


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
    draft: bool = False
    labels: list[str] = field(default_factory=list)
    requested_reviewers: list[str] = field(default_factory=list)


@dataclass
class RateLimitInfo:
    """GitHub rate limit information."""

    limit: int
    remaining: int
    reset_at: datetime
    used: int = 0


@dataclass
class GitBlob:
    """GitHub git blob."""

    sha: str


@dataclass
class GitTreeEntry:
    """Entry in a git tree."""

    path: str
    mode: str
    type: str
    sha: str


@dataclass
class GitRef:
    """GitHub git ref (branch pointer)."""

    ref: str
    sha: str


@dataclass
class GitCompareResult:
    """Result of comparing two commits."""

    files: list[dict[str, Any]]
    ahead_by: int
    behind_by: int
    total_commits: int


__all__ = [
    "GitBlob",
    "GitCompareResult",
    "GitHubCommit",
    "GitHubPullRequest",
    "GitHubRepository",
    "GitHubUser",
    "GitRef",
    "GitTreeEntry",
    "RateLimitInfo",
]
