"""GitHub Git Data API methods.

Provides low-level git operations (blobs, trees, commits, refs, compare,
branches, pull requests) via the GitHub Git Data API and related endpoints.

These methods are mixed into GitHubClient.
"""

from __future__ import annotations

from typing import Any

from pilot_space.integrations.github.exceptions import GitHubAPIError


class GitDataMixin:
    """Mixin providing GitHub Git Data API methods.

    Requires the host class to have a ``_request`` method with the same
    signature as ``GitHubClient._request``.
    """

    # Typed stub so Pyright knows about _request on the mixin.
    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any]: ...

    # =========================================================================
    # Git Data API (blobs, trees, commits, refs)
    # =========================================================================

    async def get_ref(
        self,
        owner: str,
        repo: str,
        branch: str,
    ) -> dict[str, Any]:
        """Get a git ref (branch pointer).

        Args:
            owner: Repository owner.
            repo: Repository name.
            branch: Branch name.

        Returns:
            Ref data with object.sha.
        """
        data = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/git/refs/heads/{branch}",
        )
        if not isinstance(data, dict):
            raise GitHubAPIError("Unexpected response format")
        return data

    async def get_git_commit(
        self,
        owner: str,
        repo: str,
        sha: str,
    ) -> dict[str, Any]:
        """Get a git commit object (for tree SHA).

        Args:
            owner: Repository owner.
            repo: Repository name.
            sha: Commit SHA.

        Returns:
            Git commit data with tree.sha.
        """
        data = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/git/commits/{sha}",
        )
        if not isinstance(data, dict):
            raise GitHubAPIError("Unexpected response format")
        return data

    async def create_blob(
        self,
        owner: str,
        repo: str,
        content: str,
        encoding: str = "utf-8",
    ) -> str:
        """Create a blob in the repository.

        Args:
            owner: Repository owner.
            repo: Repository name.
            content: Blob content.
            encoding: Content encoding ("utf-8" or "base64").

        Returns:
            SHA of the created blob.
        """
        data = await self._request(
            "POST",
            f"/repos/{owner}/{repo}/git/blobs",
            json={"content": content, "encoding": encoding},
        )
        if not isinstance(data, dict):
            raise GitHubAPIError("Unexpected response format")
        return data["sha"]

    async def create_tree(
        self,
        owner: str,
        repo: str,
        base_tree: str,
        tree_entries: list[dict[str, str]],
    ) -> str:
        """Create a tree object.

        Args:
            owner: Repository owner.
            repo: Repository name.
            base_tree: SHA of the base tree.
            tree_entries: List of tree entry dicts (path, mode, type, sha).

        Returns:
            SHA of the created tree.
        """
        data = await self._request(
            "POST",
            f"/repos/{owner}/{repo}/git/trees",
            json={"base_tree": base_tree, "tree": tree_entries},
        )
        if not isinstance(data, dict):
            raise GitHubAPIError("Unexpected response format")
        return data["sha"]

    async def create_git_commit(
        self,
        owner: str,
        repo: str,
        message: str,
        tree_sha: str,
        parent_shas: list[str],
    ) -> str:
        """Create a git commit object.

        Args:
            owner: Repository owner.
            repo: Repository name.
            message: Commit message.
            tree_sha: SHA of the tree.
            parent_shas: List of parent commit SHAs.

        Returns:
            SHA of the created commit.
        """
        data = await self._request(
            "POST",
            f"/repos/{owner}/{repo}/git/commits",
            json={
                "message": message,
                "tree": tree_sha,
                "parents": parent_shas,
            },
        )
        if not isinstance(data, dict):
            raise GitHubAPIError("Unexpected response format")
        return data["sha"]

    async def update_ref(
        self,
        owner: str,
        repo: str,
        branch: str,
        sha: str,
    ) -> dict[str, Any]:
        """Update a git ref to point to a new SHA.

        Args:
            owner: Repository owner.
            repo: Repository name.
            branch: Branch name.
            sha: New commit SHA.

        Returns:
            Updated ref data.
        """
        data = await self._request(
            "PATCH",
            f"/repos/{owner}/{repo}/git/refs/heads/{branch}",
            json={"sha": sha},
        )
        if not isinstance(data, dict):
            raise GitHubAPIError("Unexpected response format")
        return data

    async def compare_commits(
        self,
        owner: str,
        repo: str,
        base: str,
        head: str,
    ) -> dict[str, Any]:
        """Compare two commits.

        Args:
            owner: Repository owner.
            repo: Repository name.
            base: Base ref.
            head: Head ref.

        Returns:
            Comparison data with files, ahead_by, behind_by, total_commits.
        """
        data = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/compare/{base}...{head}",
        )
        if not isinstance(data, dict):
            raise GitHubAPIError("Unexpected response format")
        return data

    async def get_file_content(
        self,
        owner: str,
        repo: str,
        path: str,
        ref: str,
    ) -> dict[str, Any]:
        """Get file content from a repository.

        Args:
            owner: Repository owner.
            repo: Repository name.
            path: File path in the repository.
            ref: Branch name or commit SHA.

        Returns:
            File data with content and encoding.
        """
        data = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/contents/{path}",
            params={"ref": ref},
        )
        if not isinstance(data, dict):
            raise GitHubAPIError("Unexpected response format")
        return data

    async def list_branches(
        self,
        owner: str,
        repo: str,
        *,
        page: int = 1,
        per_page: int = 30,
    ) -> list[dict[str, Any]]:
        """List branches in a repository.

        Args:
            owner: Repository owner.
            repo: Repository name.
            page: Page number.
            per_page: Results per page.

        Returns:
            List of branch data.
        """
        data = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/branches",
            params={"page": page, "per_page": per_page},
        )
        if not isinstance(data, list):
            raise GitHubAPIError("Unexpected response format")
        return data

    async def create_branch(
        self,
        owner: str,
        repo: str,
        name: str,
        from_sha: str,
    ) -> dict[str, Any]:
        """Create a new branch.

        Args:
            owner: Repository owner.
            repo: Repository name.
            name: New branch name.
            from_sha: SHA to branch from.

        Returns:
            Created ref data.
        """
        data = await self._request(
            "POST",
            f"/repos/{owner}/{repo}/git/refs",
            json={"ref": f"refs/heads/{name}", "sha": from_sha},
        )
        if not isinstance(data, dict):
            raise GitHubAPIError("Unexpected response format")
        return data

    async def delete_branch(
        self,
        owner: str,
        repo: str,
        name: str,
    ) -> None:
        """Delete a branch.

        Args:
            owner: Repository owner.
            repo: Repository name.
            name: Branch name to delete.
        """
        await self._request(
            "DELETE",
            f"/repos/{owner}/{repo}/git/refs/heads/{name}",
        )

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
    ) -> dict[str, Any]:
        """Create a pull request.

        Args:
            owner: Repository owner.
            repo: Repository name.
            title: PR title.
            body: PR body.
            head: Head branch.
            base: Base branch.
            draft: Whether to create as draft.

        Returns:
            Created PR data.
        """
        data = await self._request(
            "POST",
            f"/repos/{owner}/{repo}/pulls",
            json={
                "title": title,
                "body": body,
                "head": head,
                "base": base,
                "draft": draft,
            },
        )
        if not isinstance(data, dict):
            raise GitHubAPIError("Unexpected response format")
        return data

    async def get_repo_info(
        self,
        owner: str,
        repo: str,
    ) -> dict[str, Any]:
        """Get repository information (including default branch).

        Args:
            owner: Repository owner.
            repo: Repository name.

        Returns:
            Repository data.
        """
        data = await self._request("GET", f"/repos/{owner}/{repo}")
        if not isinstance(data, dict):
            raise GitHubAPIError("Unexpected response format")
        return data


__all__ = ["GitDataMixin"]
