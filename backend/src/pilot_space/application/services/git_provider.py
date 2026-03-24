"""Git provider abstraction layer.

Defines a provider-agnostic interface for git operations (changed files, diff,
commit, branches, PRs) with concrete implementations for GitHub and GitLab.

The frontend/router never deal with provider-specific logic -- everything goes
through the GitProvider ABC.
"""

from __future__ import annotations

import base64
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from pilot_space.integrations.github.client import GitHubClient
    from pilot_space.integrations.gitlab.client import GitLabClient

logger = get_logger(__name__)


# ============================================================================
# Dataclasses
# ============================================================================


@dataclass
class ChangedFile:
    """A file changed between two refs."""

    path: str
    status: str  # added, modified, removed, renamed
    additions: int = 0
    deletions: int = 0
    patch: str | None = None


@dataclass
class BranchInfo:
    """Branch metadata."""

    name: str
    sha: str
    is_default: bool = False
    is_protected: bool = False


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
    content: str
    encoding: str = "utf-8"
    action: str = "update"  # update, create, delete


# ============================================================================
# GitProvider ABC
# ============================================================================


class GitProvider(ABC):
    """Abstract base class for git provider operations.

    Implementations wrap provider-specific clients (GitHub, GitLab) and expose
    a unified interface for the application layer.
    """

    @abstractmethod
    async def get_changed_files(
        self,
        owner: str,
        repo: str,
        ref: str,
        base_ref: str,
    ) -> list[ChangedFile]:
        """Get files changed between two refs.

        Args:
            owner: Repository owner/namespace.
            repo: Repository name.
            ref: Head ref (branch or SHA).
            base_ref: Base ref to compare against.

        Returns:
            List of changed files with diff info.
        """

    @abstractmethod
    async def get_file_content(
        self,
        owner: str,
        repo: str,
        path: str,
        ref: str,
    ) -> str:
        """Get file content at a specific ref.

        Args:
            owner: Repository owner/namespace.
            repo: Repository name.
            path: File path within the repository.
            ref: Branch name or commit SHA.

        Returns:
            File content as a string.
        """

    @abstractmethod
    async def create_commit(
        self,
        owner: str,
        repo: str,
        branch: str,
        message: str,
        files: list[FileChange],
    ) -> CommitResult:
        """Create a commit with one or more file changes.

        Args:
            owner: Repository owner/namespace.
            repo: Repository name.
            branch: Target branch.
            message: Commit message.
            files: List of file changes to include.

        Returns:
            CommitResult with the new commit SHA and URL.
        """

    @abstractmethod
    async def list_branches(
        self,
        owner: str,
        repo: str,
        *,
        search: str | None = None,
        page: int = 1,
        per_page: int = 30,
    ) -> list[BranchInfo]:
        """List branches in a repository.

        Args:
            owner: Repository owner/namespace.
            repo: Repository name.
            search: Optional search filter.
            page: Page number.
            per_page: Results per page.

        Returns:
            List of branch info.
        """

    @abstractmethod
    async def create_branch(
        self,
        owner: str,
        repo: str,
        name: str,
        from_ref: str,
    ) -> BranchInfo:
        """Create a new branch.

        Args:
            owner: Repository owner/namespace.
            repo: Repository name.
            name: New branch name.
            from_ref: Source ref (branch name or SHA).

        Returns:
            BranchInfo for the created branch.
        """

    @abstractmethod
    async def delete_branch(
        self,
        owner: str,
        repo: str,
        name: str,
    ) -> None:
        """Delete a branch.

        Args:
            owner: Repository owner/namespace.
            repo: Repository name.
            name: Branch name to delete.
        """

    @abstractmethod
    async def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        head: str,
        base: str,
        *,
        draft: bool = False,
    ) -> PullRequestResult:
        """Create a pull/merge request.

        Args:
            owner: Repository owner/namespace.
            repo: Repository name.
            title: PR title.
            body: PR body/description.
            head: Head branch.
            base: Base branch.
            draft: Whether to create as draft.

        Returns:
            PullRequestResult with number and URL.
        """

    @abstractmethod
    async def get_default_branch(
        self,
        owner: str,
        repo: str,
    ) -> str:
        """Get the default branch name for a repository.

        Args:
            owner: Repository owner/namespace.
            repo: Repository name.

        Returns:
            Default branch name (e.g. "main").
        """


# ============================================================================
# GitHub Implementation
# ============================================================================


class GitHubGitProvider(GitProvider):
    """GitProvider implementation using the GitHub Git Data API.

    Wraps GitHubClient and maps responses to the provider-agnostic dataclasses.
    Multi-file commits use the blob -> tree -> commit -> update-ref workflow.
    """

    def __init__(self, client: GitHubClient) -> None:
        self._client = client

    async def get_changed_files(
        self,
        owner: str,
        repo: str,
        ref: str,
        base_ref: str,
    ) -> list[ChangedFile]:
        data = await self._client.compare_commits(owner, repo, base_ref, ref)
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

    async def get_file_content(
        self,
        owner: str,
        repo: str,
        path: str,
        ref: str,
    ) -> str:
        data = await self._client.get_file_content(owner, repo, path, ref)
        content = data.get("content", "")
        encoding = data.get("encoding", "base64")
        if encoding == "base64":
            return base64.b64decode(content).decode("utf-8")
        return content

    async def create_commit(
        self,
        owner: str,
        repo: str,
        branch: str,
        message: str,
        files: list[FileChange],
    ) -> CommitResult:
        """Create a multi-file commit via Git Data API.

        Flow: get ref -> get commit tree -> create blobs -> create tree ->
              create commit -> update ref (with one retry on 422 stale ref).
        """
        # a. Get HEAD SHA for the branch
        ref_data = await self._client.get_ref(owner, repo, branch)
        head_sha = ref_data["object"]["sha"]

        # b. Get the tree SHA from the HEAD commit
        commit_data = await self._client.get_git_commit(owner, repo, head_sha)
        base_tree_sha = commit_data["tree"]["sha"]

        # c. Create blobs for each file
        tree_entries = []
        for fc in files:
            if fc.action == "delete":
                # Omit the file from the new tree to delete it
                continue
            blob_sha = await self._client.create_blob(owner, repo, fc.content, fc.encoding)
            tree_entries.append(
                {
                    "path": fc.path,
                    "mode": "100644",
                    "type": "blob",
                    "sha": blob_sha,
                }
            )

        # d. Create new tree
        new_tree_sha = await self._client.create_tree(owner, repo, base_tree_sha, tree_entries)

        # e. Create commit
        new_commit_sha = await self._client.create_git_commit(
            owner, repo, message, new_tree_sha, [head_sha]
        )

        # f. Update ref (retry once on 422 stale ref)
        try:
            await self._client.update_ref(owner, repo, branch, new_commit_sha)
        except Exception as exc:
            if "422" in str(exc):
                logger.warning("Stale ref on update, retrying once")
                await self._client.update_ref(owner, repo, branch, new_commit_sha)
            else:
                raise

        return CommitResult(
            sha=new_commit_sha,
            html_url=f"https://github.com/{owner}/{repo}/commit/{new_commit_sha}",
            message=message,
        )

    async def list_branches(
        self,
        owner: str,
        repo: str,
        *,
        search: str | None = None,
        page: int = 1,
        per_page: int = 30,
    ) -> list[BranchInfo]:
        branches = await self._client.list_branches(owner, repo, page=page, per_page=per_page)
        # Get default branch for is_default flag
        repo_info = await self._client.get_repo(owner, repo)
        default_branch = repo_info.default_branch

        result = [
            BranchInfo(
                name=b["name"],
                sha=b["commit"]["sha"],
                is_default=(b["name"] == default_branch),
                is_protected=b.get("protected", False),
            )
            for b in branches
        ]

        if search:
            result = [b for b in result if search.lower() in b.name.lower()]

        return result

    async def create_branch(
        self,
        owner: str,
        repo: str,
        name: str,
        from_ref: str,
    ) -> BranchInfo:
        # Resolve from_ref to a SHA if it's a branch name
        try:
            ref_data = await self._client.get_ref(owner, repo, from_ref)
            sha = ref_data["object"]["sha"]
        except Exception:
            # Assume from_ref is already a SHA
            sha = from_ref

        await self._client.create_branch(owner, repo, name, sha)
        return BranchInfo(name=name, sha=sha)

    async def delete_branch(
        self,
        owner: str,
        repo: str,
        name: str,
    ) -> None:
        await self._client.delete_branch(owner, repo, name)

    async def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        head: str,
        base: str,
        *,
        draft: bool = False,
    ) -> PullRequestResult:
        data = await self._client.create_pull_request(
            owner, repo, title, body, head, base, draft=draft
        )
        return PullRequestResult(
            number=data["number"],
            html_url=data["html_url"],
            title=data["title"],
            draft=data.get("draft", False),
        )

    async def get_default_branch(
        self,
        owner: str,
        repo: str,
    ) -> str:
        repo_info = await self._client.get_repo(owner, repo)
        return repo_info.default_branch


# ============================================================================
# GitLab Implementation
# ============================================================================


class GitLabGitProvider(GitProvider):
    """GitProvider implementation using the GitLab REST API v4.

    Wraps GitLabClient and maps responses to the provider-agnostic dataclasses.
    GitLab natively supports multi-file commits (no blob/tree dance needed).
    """

    def __init__(self, client: GitLabClient) -> None:
        self._client = client

    async def get_changed_files(
        self,
        owner: str,
        repo: str,
        ref: str,
        base_ref: str,
    ) -> list[ChangedFile]:
        data = await self._client.compare_commits(owner, repo, base_ref, ref)
        return [
            ChangedFile(
                path=d["new_path"],
                status=_gitlab_status_to_generic(
                    d.get("renamed_file", False),
                    d.get("new_file", False),
                    d.get("deleted_file", False),
                ),
                additions=0,  # GitLab compare doesn't return line counts
                deletions=0,
                patch=d.get("diff"),
            )
            for d in data.get("diffs", [])
        ]

    async def get_file_content(
        self,
        owner: str,
        repo: str,
        path: str,
        ref: str,
    ) -> str:
        data = await self._client.get_file_content(owner, repo, path, ref)
        content = data.get("content", "")
        encoding = data.get("encoding", "base64")
        if encoding == "base64":
            return base64.b64decode(content).decode("utf-8")
        return content

    async def create_commit(
        self,
        owner: str,
        repo: str,
        branch: str,
        message: str,
        files: list[FileChange],
    ) -> CommitResult:
        actions = []
        for fc in files:
            action_type = fc.action
            if action_type == "update":
                action_type = "update"
            elif action_type == "create":
                action_type = "create"
            elif action_type == "delete":
                action_type = "delete"
            actions.append(
                {
                    "action": action_type,
                    "file_path": fc.path,
                    "content": fc.content if fc.action != "delete" else None,
                    "encoding": "text" if fc.encoding == "utf-8" else "base64",
                }
            )

        data = await self._client.create_commit(owner, repo, branch, message, actions)
        commit_id = data.get("id", data.get("short_id", ""))
        return CommitResult(
            sha=commit_id,
            html_url=data.get("web_url", f"https://gitlab.com/{owner}/{repo}/-/commit/{commit_id}"),
            message=message,
        )

    async def list_branches(
        self,
        owner: str,
        repo: str,
        *,
        search: str | None = None,
        page: int = 1,
        per_page: int = 30,
    ) -> list[BranchInfo]:
        branches = await self._client.list_branches(
            owner, repo, search=search, page=page, per_page=per_page
        )
        return [
            BranchInfo(
                name=b["name"],
                sha=b["commit"]["id"],
                is_default=b.get("default", False),
                is_protected=b.get("protected", False),
            )
            for b in branches
        ]

    async def create_branch(
        self,
        owner: str,
        repo: str,
        name: str,
        from_ref: str,
    ) -> BranchInfo:
        data = await self._client.create_branch(owner, repo, name, from_ref)
        return BranchInfo(
            name=data["name"],
            sha=data["commit"]["id"],
        )

    async def delete_branch(
        self,
        owner: str,
        repo: str,
        name: str,
    ) -> None:
        await self._client.delete_branch(owner, repo, name)

    async def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        head: str,
        base: str,
        *,
        draft: bool = False,
    ) -> PullRequestResult:
        data = await self._client.create_merge_request(owner, repo, title, body, head, base)
        return PullRequestResult(
            number=data["iid"],
            html_url=data["web_url"],
            title=data["title"],
            draft=data.get("draft", False),
        )

    async def get_default_branch(
        self,
        owner: str,
        repo: str,
    ) -> str:
        data = await self._client.get_project(owner, repo)
        return data["default_branch"]


# ============================================================================
# Helper functions
# ============================================================================


def _gitlab_status_to_generic(renamed: bool, new_file: bool, deleted: bool) -> str:
    """Map GitLab diff flags to generic status string."""
    if renamed:
        return "renamed"
    if new_file:
        return "added"
    if deleted:
        return "removed"
    return "modified"


_PROVIDER_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"github\.com"), "github"),
    (re.compile(r"gitlab\.com"), "gitlab"),
]


def detect_provider(remote_url: str) -> str:
    """Detect git provider from a remote URL.

    Args:
        remote_url: Git remote URL (HTTPS or SSH).

    Returns:
        Provider type string ("github" or "gitlab").

    Raises:
        ValueError: If provider cannot be determined.
    """
    for pattern, provider_type in _PROVIDER_PATTERNS:
        if pattern.search(remote_url):
            return provider_type
    raise ValueError(f"Cannot determine git provider from URL: {remote_url}")


def resolve_provider(provider_type: str, access_token: str) -> GitProvider:
    """Create a GitProvider instance for the given provider type.

    Args:
        provider_type: "github" or "gitlab".
        access_token: OAuth/PAT access token.

    Returns:
        GitProvider implementation.

    Raises:
        ValueError: If provider_type is not supported.
    """
    if provider_type == "github":
        from pilot_space.integrations.github.client import GitHubClient

        client = GitHubClient(access_token=access_token)
        return GitHubGitProvider(client)

    if provider_type == "gitlab":
        from pilot_space.integrations.gitlab.client import GitLabClient

        client = GitLabClient(access_token=access_token)
        return GitLabGitProvider(client)

    raise ValueError(f"Unsupported git provider: {provider_type}")


__all__ = [
    "BranchInfo",
    "ChangedFile",
    "CommitResult",
    "FileChange",
    "GitHubGitProvider",
    "GitLabGitProvider",
    "GitProvider",
    "PullRequestResult",
    "detect_provider",
    "resolve_provider",
]
