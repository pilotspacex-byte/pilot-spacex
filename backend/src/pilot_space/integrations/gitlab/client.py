"""GitLab API client with rate limiting.

Provides git operations via the GitLab REST API v4.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Self
from urllib.parse import quote

import httpx

from pilot_space.infrastructure.logging import get_logger
from pilot_space.integrations.gitlab.exceptions import (
    GitLabAPIError,
    GitLabAuthError,
    GitLabRateLimitError,
)

logger = get_logger(__name__)

GITLAB_API_URL = "https://gitlab.com/api/v4"


@dataclass
class GitLabClient:
    """GitLab API client using REST API v4.

    Provides:
    - Authenticated API requests
    - Project, commit, branch, merge request operations
    - File and compare operations
    - Rate limit handling

    Attributes:
        access_token: Private token or OAuth token.
        _http_client: httpx async client.
    """

    access_token: str
    _http_client: httpx.AsyncClient = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize HTTP client with auth headers."""
        self._http_client = httpx.AsyncClient(
            base_url=GITLAB_API_URL,
            headers={
                "PRIVATE-TOKEN": self.access_token,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    async def close(self) -> None:
        """Close HTTP client."""
        await self._http_client.aclose()

    async def __aenter__(self) -> Self:
        """Enter async context."""
        return self

    async def __aexit__(self, *args: object) -> None:
        """Exit async context."""
        await self.close()

    # =========================================================================
    # API Request Helpers
    # =========================================================================

    def _project_path(self, owner: str, repo: str) -> str:
        """URL-encode owner/repo for GitLab project path.

        GitLab API requires URL-encoded namespace/project path.

        Args:
            owner: Project namespace (user or group).
            repo: Project name.

        Returns:
            URL-encoded project path.
        """
        return quote(f"{owner}/{repo}", safe="")

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | list[dict[str, Any]] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any]:
        """Make authenticated API request.

        Args:
            method: HTTP method.
            path: API path (without base URL).
            json: Request body (optional).
            params: Query parameters (optional).

        Returns:
            Response JSON.

        Raises:
            GitLabRateLimitError: If rate limited.
            GitLabAuthError: If authentication fails.
            GitLabAPIError: For other API errors.
        """
        response = await self._http_client.request(
            method,
            path,
            json=json,
            params=params,
        )

        # Check rate limit headers
        remaining = response.headers.get("RateLimit-Remaining")
        if remaining is not None and int(remaining) == 0:
            reset_ts = int(response.headers.get("RateLimit-Reset", "0"))
            raise GitLabRateLimitError(
                f"GitLab rate limit exceeded. Resets at {reset_ts}",
                status_code=429,
            )

        if response.status_code == 429:
            raise GitLabRateLimitError(
                "GitLab rate limit exceeded",
                status_code=429,
            )

        if response.status_code == 401:
            raise GitLabAuthError(
                "GitLab authentication failed",
                status_code=401,
            )

        if response.status_code == 403:
            body = response.json() if response.content else {}
            raise GitLabAuthError(
                f"GitLab access forbidden: {body.get('message', 'Unknown error')}",
                status_code=403,
                response_body=body,
            )

        if response.status_code >= 400:
            body = response.json() if response.content else {}
            msg = body.get("message", body.get("error", response.text))
            raise GitLabAPIError(
                f"GitLab API error: {msg}",
                status_code=response.status_code,
                response_body=body,
            )

        # Handle 204 No Content (e.g. DELETE operations)
        if response.status_code == 204 or not response.content:
            return {}

        return response.json()

    # =========================================================================
    # Project Operations
    # =========================================================================

    async def get_project(
        self,
        owner: str,
        repo: str,
    ) -> dict[str, Any]:
        """Get project information.

        Args:
            owner: Project namespace.
            repo: Project name.

        Returns:
            Project data including default_branch.
        """
        data = await self._request(
            "GET",
            f"/projects/{self._project_path(owner, repo)}",
        )
        if not isinstance(data, dict):
            raise GitLabAPIError("Unexpected response format")
        return data

    # =========================================================================
    # Compare & File Operations
    # =========================================================================

    async def compare_commits(
        self,
        owner: str,
        repo: str,
        base: str,
        head: str,
    ) -> dict[str, Any]:
        """Compare two refs.

        Args:
            owner: Project namespace.
            repo: Project name.
            base: Base ref.
            head: Head ref.

        Returns:
            Comparison data with diffs.
        """
        data = await self._request(
            "GET",
            f"/projects/{self._project_path(owner, repo)}/repository/compare",
            params={"from": base, "to": head},
        )
        if not isinstance(data, dict):
            raise GitLabAPIError("Unexpected response format")
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
            owner: Project namespace.
            repo: Project name.
            path: File path in the repository.
            ref: Branch name or commit SHA.

        Returns:
            File data with content and encoding.
        """
        encoded_path = quote(path, safe="")
        data = await self._request(
            "GET",
            f"/projects/{self._project_path(owner, repo)}/repository/files/{encoded_path}",
            params={"ref": ref},
        )
        if not isinstance(data, dict):
            raise GitLabAPIError("Unexpected response format")
        return data

    # =========================================================================
    # Commit Operations
    # =========================================================================

    async def create_commit(
        self,
        owner: str,
        repo: str,
        branch: str,
        message: str,
        actions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Create a commit with multiple file actions.

        GitLab natively supports multi-file commits.

        Args:
            owner: Project namespace.
            repo: Project name.
            branch: Target branch.
            message: Commit message.
            actions: List of file action dicts (action, file_path, content, encoding).

        Returns:
            Commit data with id and web_url.
        """
        data = await self._request(
            "POST",
            f"/projects/{self._project_path(owner, repo)}/repository/commits",
            json={
                "branch": branch,
                "commit_message": message,
                "actions": actions,
            },
        )
        if not isinstance(data, dict):
            raise GitLabAPIError("Unexpected response format")
        return data

    # =========================================================================
    # Branch Operations
    # =========================================================================

    async def list_branches(
        self,
        owner: str,
        repo: str,
        *,
        search: str | None = None,
        page: int = 1,
        per_page: int = 30,
    ) -> list[dict[str, Any]]:
        """List branches in a project.

        Args:
            owner: Project namespace.
            repo: Project name.
            search: Optional search filter.
            page: Page number.
            per_page: Results per page.

        Returns:
            List of branch data.
        """
        params: dict[str, Any] = {"page": page, "per_page": per_page}
        if search:
            params["search"] = search

        data = await self._request(
            "GET",
            f"/projects/{self._project_path(owner, repo)}/repository/branches",
            params=params,
        )
        if not isinstance(data, list):
            raise GitLabAPIError("Unexpected response format")
        return data

    async def create_branch(
        self,
        owner: str,
        repo: str,
        name: str,
        ref: str,
    ) -> dict[str, Any]:
        """Create a new branch.

        Args:
            owner: Project namespace.
            repo: Project name.
            name: New branch name.
            ref: Source ref (branch name or SHA).

        Returns:
            Created branch data.
        """
        data = await self._request(
            "POST",
            f"/projects/{self._project_path(owner, repo)}/repository/branches",
            params={"branch": name, "ref": ref},
        )
        if not isinstance(data, dict):
            raise GitLabAPIError("Unexpected response format")
        return data

    async def delete_branch(
        self,
        owner: str,
        repo: str,
        name: str,
    ) -> None:
        """Delete a branch.

        Args:
            owner: Project namespace.
            repo: Project name.
            name: Branch name to delete.
        """
        encoded_name = quote(name, safe="")
        await self._request(
            "DELETE",
            f"/projects/{self._project_path(owner, repo)}/repository/branches/{encoded_name}",
        )

    # =========================================================================
    # Merge Request Operations
    # =========================================================================

    async def create_merge_request(
        self,
        owner: str,
        repo: str,
        title: str,
        description: str,
        source_branch: str,
        target_branch: str,
    ) -> dict[str, Any]:
        """Create a merge request.

        Args:
            owner: Project namespace.
            repo: Project name.
            title: MR title.
            description: MR description.
            source_branch: Source branch.
            target_branch: Target branch.

        Returns:
            Created MR data with iid and web_url.
        """
        data = await self._request(
            "POST",
            f"/projects/{self._project_path(owner, repo)}/merge_requests",
            json={
                "title": title,
                "description": description,
                "source_branch": source_branch,
                "target_branch": target_branch,
            },
        )
        if not isinstance(data, dict):
            raise GitLabAPIError("Unexpected response format")
        return data


__all__ = ["GITLAB_API_URL", "GitLabClient"]
