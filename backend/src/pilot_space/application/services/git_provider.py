"""Git provider abstraction layer.

Defines a provider-agnostic interface for git operations (branches, file
content, commits, pull requests) with a concrete GitHub implementation.

The router never deals with provider-specific logic — everything goes
through the GitProvider ABC.
"""

from __future__ import annotations

import base64
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import httpx

from pilot_space.domain.exceptions import AppError, ConflictError, ValidationError
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# Git provider exception hierarchy
# ============================================================================


class GitProviderError(AppError):
    """Base class for git provider errors (502 Bad Gateway)."""

    error_code: str = "git_provider_error"
    http_status: int = 502


class GitProviderAuthError(GitProviderError):
    """Authentication failure with the git provider (401)."""

    error_code: str = "git_auth_error"
    http_status: int = 401


class GitProviderRateLimitError(GitProviderError):
    """Git provider rate limit exceeded (429)."""

    error_code: str = "git_rate_limit"
    http_status: int = 429

    def __init__(self, message: str, *, retry_after: int | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class GitProviderNotFoundError(GitProviderError):
    """Resource not found at the git provider (404)."""

    error_code: str = "git_not_found"
    http_status: int = 404


# ============================================================================
# Dataclasses
# ============================================================================


@dataclass
class BranchInfo:
    """Branch metadata."""

    name: str
    sha: str
    is_default: bool = False
    is_protected: bool = False


@dataclass
class FileContent:
    """File content at a specific ref."""

    content: str
    sha: str
    size: int
    encoding: str = "utf-8"


@dataclass
class ChangedFile:
    """A file changed between two refs."""

    path: str
    status: str  # added, modified, removed, renamed
    additions: int = 0
    deletions: int = 0
    patch: str | None = None


@dataclass
class CommitResult:
    """Result of creating a commit."""

    sha: str
    html_url: str
    message: str


@dataclass
class PullRequestResult:
    """Result of creating a pull/merge request."""

    number: int
    html_url: str
    title: str
    draft: bool = False


@dataclass
class FileChange:
    """A file to be included in a commit."""

    path: str
    content: str | None = None
    encoding: str = "utf-8"
    action: str = "update"  # update, create, delete


# ============================================================================
# GitProvider ABC
# ============================================================================


class GitProvider(ABC):
    """Abstract base class for git provider operations.

    Implementations wrap provider-specific APIs and expose a unified
    interface for the application layer.
    """

    @abstractmethod
    async def get_branches(self) -> list[BranchInfo]:
        """List all branches for the repository."""

    @abstractmethod
    async def get_default_branch(self) -> str:
        """Get the default branch name (e.g. 'main')."""

    @abstractmethod
    async def create_branch(self, name: str, source_branch: str) -> BranchInfo:
        """Create a new branch from source_branch.

        Args:
            name: New branch name.
            source_branch: Branch or SHA to create from.

        Returns:
            BranchInfo for the created branch.
        """

    @abstractmethod
    async def delete_branch(self, name: str) -> None:
        """Delete a branch by name."""

    @abstractmethod
    async def get_file_content(self, path: str, ref: str) -> FileContent:
        """Get file content at a specific ref.

        Args:
            path: File path within the repository.
            ref: Branch name or commit SHA.

        Returns:
            FileContent with decoded content and sha.
        """

    @abstractmethod
    async def get_repo_status(self, base_branch: str, head_branch: str) -> list[ChangedFile]:
        """Get files changed between two branches.

        Args:
            base_branch: Base branch name.
            head_branch: Head branch name.

        Returns:
            List of changed files with diff info.
        """

    @abstractmethod
    async def create_commit(
        self,
        branch: str,
        message: str,
        files: list[FileChange],
    ) -> CommitResult:
        """Create a commit with one or more file changes.

        Args:
            branch: Target branch.
            message: Commit message.
            files: List of file changes to include.

        Returns:
            CommitResult with the new commit SHA and URL.
        """

    @abstractmethod
    async def create_pull_request(
        self,
        title: str,
        body: str,
        head: str,
        base: str,
        *,
        draft: bool = False,
    ) -> PullRequestResult:
        """Create a pull request.

        Args:
            title: PR title.
            body: PR description.
            head: Head branch.
            base: Base branch.
            draft: Whether to create as draft.

        Returns:
            PullRequestResult with number and URL.
        """

    @abstractmethod
    async def compare_branches(
        self,
        base: str,
        head: str,
    ) -> list[ChangedFile]:
        """Compare two branches and return file diffs.

        Args:
            base: Base branch.
            head: Head branch.

        Returns:
            List of changed files with diff info.
        """

    async def aclose(self) -> None:  # noqa: B027
        """Close any underlying resources (e.g. HTTP clients).

        Default no-op; subclasses with HTTP clients should override.
        """


# ============================================================================
# GitHub Implementation
# ============================================================================

_GITHUB_API_URL = "https://api.github.com"


class GitHubGitProvider(GitProvider):
    """GitProvider implementation using the GitHub Git Data API via httpx.

    Uses GitHub REST API v3 directly (no external GitHub client dependency).
    Multi-file commits use the blob -> tree -> commit -> update-ref workflow.
    """

    def __init__(self, token: str, owner: str, repo: str) -> None:
        """Initialize the provider.

        Args:
            token: GitHub OAuth or PAT access token.
            owner: Repository owner (user or org).
            repo: Repository name.
        """
        self._token = token
        self._owner = owner
        self._repo = repo
        self._client = httpx.AsyncClient(
            base_url=_GITHUB_API_URL,
            headers={
                "Accept": "application/vnd.github.v3+json",
                "Authorization": f"token {token}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any]:
        """Make a GitHub API request and map errors to domain exceptions."""
        try:
            response = await self._client.request(method, path, json=json, params=params)
        except httpx.RequestError as err:
            raise GitProviderError(f"GitHub API connection failed: {err}") from err

        if response.status_code == 401:
            raise GitProviderAuthError("GitHub authentication failed")

        if response.status_code == 403:
            body = response.json() if response.content else {}
            # Distinguish rate-limit from plain 403
            if "rate limit" in body.get("message", "").lower():
                retry_after = int(response.headers.get("Retry-After", 60))
                raise GitProviderRateLimitError(
                    "GitHub rate limit exceeded",
                    retry_after=retry_after,
                )
            raise GitProviderAuthError(
                f"GitHub access forbidden: {body.get('message', 'Unknown error')}"
            )

        if response.status_code == 404:
            body = response.json() if response.content else {}
            raise GitProviderNotFoundError(
                f"GitHub resource not found: {body.get('message', path)}"
            )

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            raise GitProviderRateLimitError(
                "GitHub rate limit exceeded",
                retry_after=retry_after,
            )

        if response.status_code == 409:
            body = response.json() if response.content else {}
            raise ConflictError(f"GitHub conflict: {body.get('message', response.text)}")

        if response.status_code in (400, 422):
            body = response.json() if response.content else {}
            raise ValidationError(f"GitHub validation error: {body.get('message', response.text)}")

        if response.status_code >= 400:
            body = response.json() if response.content else {}
            raise GitProviderError(
                f"GitHub API error {response.status_code}: {body.get('message', response.text)}"
            )

        if response.status_code == 204:
            return {}

        return response.json()

    async def _get_head_sha(self, branch: str) -> str:
        """Resolve branch name to HEAD commit SHA."""
        data = await self._request(
            "GET", f"/repos/{self._owner}/{self._repo}/git/refs/heads/{branch}"
        )
        if not isinstance(data, dict):
            raise GitProviderError("Unexpected response from GitHub refs endpoint")
        return data["object"]["sha"]

    async def _get_commit_tree_sha(self, commit_sha: str) -> str:
        """Get the tree SHA of a commit."""
        data = await self._request(
            "GET", f"/repos/{self._owner}/{self._repo}/git/commits/{commit_sha}"
        )
        if not isinstance(data, dict):
            raise GitProviderError("Unexpected response from GitHub commits endpoint")
        return data["tree"]["sha"]

    async def _create_blob(self, content: str, encoding: str) -> str:
        """Create a blob and return its SHA."""
        data = await self._request(
            "POST",
            f"/repos/{self._owner}/{self._repo}/git/blobs",
            json={"content": content, "encoding": encoding},
        )
        if not isinstance(data, dict):
            raise GitProviderError("Unexpected response from GitHub blobs endpoint")
        return data["sha"]

    async def _create_tree(self, base_tree_sha: str, tree_entries: list[dict[str, Any]]) -> str:
        """Create a tree and return its SHA."""
        data = await self._request(
            "POST",
            f"/repos/{self._owner}/{self._repo}/git/trees",
            json={"base_tree": base_tree_sha, "tree": tree_entries},
        )
        if not isinstance(data, dict):
            raise GitProviderError("Unexpected response from GitHub trees endpoint")
        return data["sha"]

    async def _create_git_commit(self, message: str, tree_sha: str, parent_shas: list[str]) -> str:
        """Create a git commit object and return its SHA."""
        data = await self._request(
            "POST",
            f"/repos/{self._owner}/{self._repo}/git/commits",
            json={"message": message, "tree": tree_sha, "parents": parent_shas},
        )
        if not isinstance(data, dict):
            raise GitProviderError("Unexpected response from GitHub git/commits endpoint")
        return data["sha"]

    async def _update_ref(self, branch: str, commit_sha: str) -> None:
        """Update branch reference to point to commit_sha."""
        await self._request(
            "PATCH",
            f"/repos/{self._owner}/{self._repo}/git/refs/heads/{branch}",
            json={"sha": commit_sha, "force": False},
        )

    # ------------------------------------------------------------------
    # GitProvider interface
    # ------------------------------------------------------------------

    async def get_branches(self) -> list[BranchInfo]:
        per_page = 100
        max_pages = 10  # Safety cap: 1000 branches max
        all_branches: list[dict[str, Any]] = []

        for page in range(1, max_pages + 1):
            data = await self._request(
                "GET",
                f"/repos/{self._owner}/{self._repo}/branches",
                params={"per_page": per_page, "page": page},
            )
            if not isinstance(data, list):
                raise GitProviderError("Unexpected response from GitHub branches endpoint")
            all_branches.extend(data)
            if len(data) < per_page:
                break

        # Fetch default branch to mark it
        default = await self.get_default_branch()

        return [
            BranchInfo(
                name=b["name"],
                sha=b["commit"]["sha"],
                is_default=(b["name"] == default),
                is_protected=b.get("protected", False),
            )
            for b in all_branches
        ]

    async def get_default_branch(self) -> str:
        data = await self._request("GET", f"/repos/{self._owner}/{self._repo}")
        if not isinstance(data, dict):
            raise GitProviderError("Unexpected response from GitHub repo endpoint")
        return data["default_branch"]

    async def create_branch(self, name: str, source_branch: str) -> BranchInfo:
        # Resolve source to SHA
        try:
            sha = await self._get_head_sha(source_branch)
        except GitProviderNotFoundError:
            # source_branch may already be a SHA
            sha = source_branch

        await self._request(
            "POST",
            f"/repos/{self._owner}/{self._repo}/git/refs",
            json={"ref": f"refs/heads/{name}", "sha": sha},
        )
        return BranchInfo(name=name, sha=sha)

    async def delete_branch(self, name: str) -> None:
        await self._request(
            "DELETE",
            f"/repos/{self._owner}/{self._repo}/git/refs/heads/{name}",
        )

    async def get_file_content(self, path: str, ref: str) -> FileContent:
        data = await self._request(
            "GET",
            f"/repos/{self._owner}/{self._repo}/contents/{path}",
            params={"ref": ref},
        )
        if not isinstance(data, dict):
            raise GitProviderError("Unexpected response from GitHub contents endpoint")

        raw_content = data.get("content", "")
        encoding = data.get("encoding", "base64")
        sha = data.get("sha", "")
        size = data.get("size", 0)

        if encoding == "base64":
            # GitHub wraps base64 with newlines
            try:
                decoded = base64.b64decode(raw_content.replace("\n", "")).decode("utf-8")
            except UnicodeDecodeError as err:
                raise AppError(
                    f"File contains non-UTF-8 content and cannot be displayed: {path}",
                    error_code="binary_file_content",
                ) from err
        else:
            decoded = raw_content

        return FileContent(content=decoded, sha=sha, size=size)

    async def get_repo_status(self, base_branch: str, head_branch: str) -> list[ChangedFile]:
        return await self.compare_branches(base_branch, head_branch)

    async def create_commit(
        self,
        branch: str,
        message: str,
        files: list[FileChange],
    ) -> CommitResult:
        """Create a multi-file commit via Git Data API.

        Flow: get HEAD SHA -> get tree SHA -> create blobs -> create tree ->
              create commit object -> update ref (retry once on stale ref).
        """
        head_sha = await self._get_head_sha(branch)
        base_tree_sha = await self._get_commit_tree_sha(head_sha)

        tree_entries: list[dict[str, Any]] = []
        for fc in files:
            if fc.action == "delete":
                # Setting sha=None removes the file from the tree
                tree_entries.append(
                    {
                        "path": fc.path,
                        "mode": "100644",
                        "type": "blob",
                        "sha": None,
                    }
                )
            else:
                if fc.content is None:
                    raise GitProviderError(
                        f"File content required for {fc.action} action: {fc.path}"
                    )
                blob_sha = await self._create_blob(fc.content, fc.encoding)
                tree_entries.append(
                    {
                        "path": fc.path,
                        "mode": "100644",
                        "type": "blob",
                        "sha": blob_sha,
                    }
                )

        new_tree_sha = await self._create_tree(base_tree_sha, tree_entries)
        new_commit_sha = await self._create_git_commit(message, new_tree_sha, [head_sha])

        # Update ref — retry once on stale 422 by rebuilding against fresh HEAD
        try:
            await self._update_ref(branch, new_commit_sha)
        except GitProviderError as exc:
            if "422" in str(exc):
                logger.warning("Stale ref on update, re-fetching HEAD and rebuilding commit")
                head_sha = await self._get_head_sha(branch)
                base_tree_sha = await self._get_commit_tree_sha(head_sha)
                new_tree_sha = await self._create_tree(base_tree_sha, tree_entries)
                new_commit_sha = await self._create_git_commit(message, new_tree_sha, [head_sha])
                await self._update_ref(branch, new_commit_sha)
            else:
                raise

        return CommitResult(
            sha=new_commit_sha,
            html_url=f"https://github.com/{self._owner}/{self._repo}/commit/{new_commit_sha}",
            message=message,
        )

    async def create_pull_request(
        self,
        title: str,
        body: str,
        head: str,
        base: str,
        *,
        draft: bool = False,
    ) -> PullRequestResult:
        data = await self._request(
            "POST",
            f"/repos/{self._owner}/{self._repo}/pulls",
            json={"title": title, "body": body, "head": head, "base": base, "draft": draft},
        )
        if not isinstance(data, dict):
            raise GitProviderError("Unexpected response from GitHub pulls endpoint")
        return PullRequestResult(
            number=data["number"],
            html_url=data["html_url"],
            title=data["title"],
            draft=data.get("draft", False),
        )

    async def compare_branches(self, base: str, head: str) -> list[ChangedFile]:
        data = await self._request(
            "GET",
            f"/repos/{self._owner}/{self._repo}/compare/{base}...{head}",
        )
        if not isinstance(data, dict):
            raise GitProviderError("Unexpected response from GitHub compare endpoint")
        return [
            ChangedFile(
                path=f["filename"],
                status=f["status"],
                additions=f.get("additions", 0),
                deletions=f.get("deletions", 0),
                patch=f.get("patch"),
            )
            for f in data.get("files", [])
        ]

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> GitHubGitProvider:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()


# ============================================================================
# GitLab stub (future)
# ============================================================================


class GitLabGitProvider(GitProvider):
    """GitProvider stub for GitLab (not yet implemented)."""

    def __init__(self, token: str, owner: str, repo: str) -> None:
        self._token = token
        self._owner = owner
        self._repo = repo

    async def get_branches(self) -> list[BranchInfo]:
        raise NotImplementedError("GitLab provider not yet implemented")

    async def get_default_branch(self) -> str:
        raise NotImplementedError("GitLab provider not yet implemented")

    async def create_branch(self, name: str, source_branch: str) -> BranchInfo:
        raise NotImplementedError("GitLab provider not yet implemented")

    async def delete_branch(self, name: str) -> None:
        raise NotImplementedError("GitLab provider not yet implemented")

    async def get_file_content(self, path: str, ref: str) -> FileContent:
        raise NotImplementedError("GitLab provider not yet implemented")

    async def get_repo_status(self, base_branch: str, head_branch: str) -> list[ChangedFile]:
        raise NotImplementedError("GitLab provider not yet implemented")

    async def create_commit(
        self,
        branch: str,
        message: str,
        files: list[FileChange],
    ) -> CommitResult:
        raise NotImplementedError("GitLab provider not yet implemented")

    async def create_pull_request(
        self,
        title: str,
        body: str,
        head: str,
        base: str,
        *,
        draft: bool = False,
    ) -> PullRequestResult:
        raise NotImplementedError("GitLab provider not yet implemented")

    async def compare_branches(self, base: str, head: str) -> list[ChangedFile]:
        raise NotImplementedError("GitLab provider not yet implemented")


__all__ = [
    "BranchInfo",
    "ChangedFile",
    "CommitResult",
    "FileChange",
    "FileContent",
    "GitHubGitProvider",
    "GitLabGitProvider",
    "GitProvider",
    "GitProviderAuthError",
    "GitProviderError",
    "GitProviderNotFoundError",
    "GitProviderRateLimitError",
    "PullRequestResult",
]
