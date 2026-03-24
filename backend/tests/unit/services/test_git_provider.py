"""Tests for git provider resolution and detection."""

from __future__ import annotations

import pytest

from pilot_space.application.services.git_provider import (
    GitHubGitProvider,
    GitLabGitProvider,
    detect_provider,
    resolve_provider,
)


class TestResolveProvider:
    def test_resolve_provider_github(self) -> None:
        provider = resolve_provider("github", "test-token")
        assert isinstance(provider, GitHubGitProvider)

    def test_resolve_provider_gitlab(self) -> None:
        provider = resolve_provider("gitlab", "test-token")
        assert isinstance(provider, GitLabGitProvider)

    def test_resolve_provider_unknown_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported git provider"):
            resolve_provider("bitbucket", "test-token")


class TestDetectProvider:
    def test_detect_github_https(self) -> None:
        assert detect_provider("https://github.com/org/repo.git") == "github"

    def test_detect_github_ssh(self) -> None:
        assert detect_provider("git@github.com:org/repo.git") == "github"

    def test_detect_gitlab_https(self) -> None:
        assert detect_provider("https://gitlab.com/org/repo.git") == "gitlab"

    def test_detect_gitlab_ssh(self) -> None:
        assert detect_provider("git@gitlab.com:org/repo.git") == "gitlab"

    def test_detect_unknown_raises(self) -> None:
        with pytest.raises(ValueError, match="Cannot determine git provider"):
            detect_provider("https://bitbucket.org/org/repo.git")

    def test_detect_github_without_git_suffix(self) -> None:
        assert detect_provider("https://github.com/org/repo") == "github"
