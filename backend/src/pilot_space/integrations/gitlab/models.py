"""GitLab API data models.

Data classes for GitLab API responses.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GitLabProject:
    """GitLab project information."""

    id: int
    name: str
    path_with_namespace: str
    default_branch: str
    web_url: str


@dataclass
class GitLabBranch:
    """GitLab branch information."""

    name: str
    commit_sha: str
    is_default: bool = False
    is_protected: bool = False


__all__ = [
    "GitLabBranch",
    "GitLabProject",
]
