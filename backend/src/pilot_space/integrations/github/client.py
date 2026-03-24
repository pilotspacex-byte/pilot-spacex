"""GitHub API client with OAuth and rate limiting."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Self

import httpx

from pilot_space.infrastructure.logging import get_logger
from pilot_space.integrations.github.exceptions import (
    GitHubAPIError,
    GitHubAuthError,
    GitHubRateLimitError,
)
from pilot_space.integrations.github.git_data import GitDataMixin
from pilot_space.integrations.github.models import (
    GitHubCommit,
    GitHubPullRequest,
    GitHubRepository,
    GitHubUser,
    RateLimitInfo,
)

logger = get_logger(__name__)

# GitHub API endpoints
GITHUB_API_URL = "https://api.github.com"
GITHUB_OAUTH_URL = "https://github.com/login/oauth"


@dataclass
class GitHubClient(GitDataMixin):
    """GitHub API client with OAuth, rate limiting, and Git Data API (via mixin)."""

    access_token: str
    _http_client: httpx.AsyncClient = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize HTTP client with auth headers."""
        self._http_client = httpx.AsyncClient(
            base_url=GITHUB_API_URL,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.access_token}",
                "X-GitHub-Api-Version": "2022-11-28",
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
    # OAuth
    # =========================================================================

    @staticmethod
    async def exchange_code(
        client_id: str,
        client_secret: str,
        code: str,
        redirect_uri: str | None = None,
    ) -> tuple[str, str | None]:
        """Exchange OAuth code for access token.

        Args:
            client_id: GitHub OAuth app client ID.
            client_secret: GitHub OAuth app client secret.
            code: Authorization code from OAuth flow.
            redirect_uri: Redirect URI (optional).

        Returns:
            Tuple of (access_token, refresh_token or None).

        Raises:
            GitHubAuthError: If code exchange fails.
        """
        async with httpx.AsyncClient() as client:
            data = {
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
            }
            if redirect_uri:
                data["redirect_uri"] = redirect_uri

            response = await client.post(
                f"{GITHUB_OAUTH_URL}/access_token",
                data=data,
                headers={"Accept": "application/json"},
            )

            if response.status_code != 200:
                raise GitHubAuthError(
                    f"Failed to exchange code: {response.text}",
                    status_code=response.status_code,
                )

            result = response.json()
            if "error" in result:
                raise GitHubAuthError(
                    f"OAuth error: {result.get('error_description', result['error'])}",
                )

            return result["access_token"], result.get("refresh_token")

    @staticmethod
    def get_authorize_url(
        client_id: str,
        redirect_uri: str,
        scope: str = "repo read:user user:email",
        state: str | None = None,
    ) -> str:
        """Generate GitHub OAuth authorization URL.

        Args:
            client_id: GitHub OAuth app client ID.
            redirect_uri: Redirect URI after authorization.
            scope: OAuth scopes.
            state: CSRF state parameter.

        Returns:
            Authorization URL.
        """
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
        }
        if state:
            params["state"] = state

        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{GITHUB_OAUTH_URL}/authorize?{query}"

    # =========================================================================
    # API Request Helpers
    # =========================================================================

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
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
            GitHubRateLimitError: If rate limited.
            GitHubAuthError: If authentication fails.
            GitHubAPIError: For other API errors.
        """
        response = await self._http_client.request(
            method,
            path,
            json=json,
            params=params,
        )

        # Check rate limit headers
        remaining = int(response.headers.get("X-RateLimit-Remaining", "1000"))
        reset_ts = int(response.headers.get("X-RateLimit-Reset", "0"))

        if response.status_code == 429 or remaining == 0:
            reset_at = datetime.fromtimestamp(reset_ts, tz=UTC)
            raise GitHubRateLimitError(reset_at=reset_at, remaining=remaining)

        if response.status_code == 401:
            raise GitHubAuthError(
                "GitHub authentication failed",
                status_code=401,
            )

        if response.status_code == 403:
            body = response.json() if response.content else {}
            raise GitHubAuthError(
                f"GitHub access forbidden: {body.get('message', 'Unknown error')}",
                status_code=403,
                response_body=body,
            )

        if response.status_code >= 400:
            body = response.json() if response.content else {}
            raise GitHubAPIError(
                f"GitHub API error: {body.get('message', response.text)}",
                status_code=response.status_code,
                response_body=body,
            )

        # Handle 204 No Content (e.g. DELETE operations)
        if response.status_code == 204 or not response.content:
            return {}

        return response.json()

    async def _paginate(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        max_pages: int = 10,
    ) -> list[dict[str, Any]]:
        """Fetch paginated results.

        Args:
            path: API path.
            params: Query parameters.
            max_pages: Maximum pages to fetch.

        Returns:
            Combined list of results.
        """
        results: list[dict[str, Any]] = []
        page_params = {**(params or {}), "per_page": 100, "page": 1}

        for _ in range(max_pages):
            response = await self._request("GET", path, params=page_params)
            if not isinstance(response, list):
                break

            results.extend(response)

            if len(response) < 100:
                break

            page_params["page"] += 1

        return results

    # =========================================================================
    # User Operations
    # =========================================================================

    async def get_current_user(self) -> GitHubUser:
        """Get authenticated user profile.

        Returns:
            GitHubUser with profile info.
        """
        data = await self._request("GET", "/user")
        if not isinstance(data, dict):
            raise GitHubAPIError("Unexpected response format")

        return GitHubUser(
            id=data["id"],
            login=data["login"],
            name=data.get("name"),
            email=data.get("email"),
            avatar_url=data["avatar_url"],
        )

    # =========================================================================
    # Repository Operations
    # =========================================================================

    async def get_repos(
        self,
        *,
        visibility: str = "all",
        sort: str = "updated",
    ) -> list[GitHubRepository]:
        """Get repositories accessible to the user.

        Args:
            visibility: Filter by visibility (all, public, private).
            sort: Sort by (created, updated, pushed, full_name).

        Returns:
            List of repositories.
        """
        data = await self._paginate(
            "/user/repos",
            params={"visibility": visibility, "sort": sort},
        )

        return [
            GitHubRepository(
                id=repo["id"],
                name=repo["name"],
                full_name=repo["full_name"],
                private=repo["private"],
                default_branch=repo["default_branch"],
                description=repo.get("description"),
                html_url=repo["html_url"],
            )
            for repo in data
        ]

    async def get_repo(self, owner: str, repo: str) -> GitHubRepository:
        """Get a specific repository.

        Args:
            owner: Repository owner.
            repo: Repository name.

        Returns:
            GitHubRepository info.
        """
        data = await self._request("GET", f"/repos/{owner}/{repo}")
        if not isinstance(data, dict):
            raise GitHubAPIError("Unexpected response format")

        return GitHubRepository(
            id=data["id"],
            name=data["name"],
            full_name=data["full_name"],
            private=data["private"],
            default_branch=data["default_branch"],
            description=data.get("description"),
            html_url=data["html_url"],
        )

    # =========================================================================
    # Commit Operations
    # =========================================================================

    async def get_commits(
        self,
        owner: str,
        repo: str,
        *,
        sha: str | None = None,
        since: datetime | None = None,
        per_page: int = 30,
    ) -> list[GitHubCommit]:
        """Get commits for a repository.

        Args:
            owner: Repository owner.
            repo: Repository name.
            sha: Branch or commit SHA to start from.
            since: Only commits after this date.
            per_page: Number of commits per page.

        Returns:
            List of commits.
        """
        params: dict[str, Any] = {"per_page": per_page}
        if sha:
            params["sha"] = sha
        if since:
            params["since"] = since.isoformat()

        data = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/commits",
            params=params,
        )
        if not isinstance(data, list):
            raise GitHubAPIError("Unexpected response format")

        return [
            GitHubCommit(
                sha=c["sha"],
                message=c["commit"]["message"],
                author_name=c["commit"]["author"]["name"],
                author_email=c["commit"]["author"]["email"],
                author_avatar_url=c["author"]["avatar_url"] if c.get("author") else None,
                html_url=c["html_url"],
                timestamp=datetime.fromisoformat(
                    c["commit"]["author"]["date"].replace("Z", "+00:00")
                ),
            )
            for c in data
        ]

    async def get_commit(
        self,
        owner: str,
        repo: str,
        sha: str,
    ) -> GitHubCommit:
        """Get a specific commit with stats.

        Args:
            owner: Repository owner.
            repo: Repository name.
            sha: Commit SHA.

        Returns:
            GitHubCommit with full details.
        """
        data = await self._request("GET", f"/repos/{owner}/{repo}/commits/{sha}")
        if not isinstance(data, dict):
            raise GitHubAPIError("Unexpected response format")

        return GitHubCommit(
            sha=data["sha"],
            message=data["commit"]["message"],
            author_name=data["commit"]["author"]["name"],
            author_email=data["commit"]["author"]["email"],
            author_avatar_url=data["author"]["avatar_url"] if data.get("author") else None,
            html_url=data["html_url"],
            timestamp=datetime.fromisoformat(
                data["commit"]["author"]["date"].replace("Z", "+00:00")
            ),
            additions=data["stats"]["additions"],
            deletions=data["stats"]["deletions"],
            files_changed=len(data.get("files", [])),
        )

    # =========================================================================
    # Pull Request Operations
    # =========================================================================

    async def get_pull_requests(
        self,
        owner: str,
        repo: str,
        *,
        state: str = "all",
        per_page: int = 30,
    ) -> list[GitHubPullRequest]:
        """Get pull requests for a repository.

        Args:
            owner: Repository owner.
            repo: Repository name.
            state: Filter by state (open, closed, all).
            per_page: Number of PRs per page.

        Returns:
            List of pull requests.
        """
        data = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/pulls",
            params={"state": state, "per_page": per_page},
        )
        if not isinstance(data, list):
            raise GitHubAPIError("Unexpected response format")

        return [
            GitHubPullRequest(
                number=pr["number"],
                title=pr["title"],
                body=pr.get("body"),
                state=pr["state"],
                merged=pr.get("merged_at") is not None,
                merged_at=(
                    datetime.fromisoformat(pr["merged_at"].replace("Z", "+00:00"))
                    if pr.get("merged_at")
                    else None
                ),
                html_url=pr["html_url"],
                head_branch=pr["head"]["ref"],
                base_branch=pr["base"]["ref"],
                author_login=pr["user"]["login"],
                author_avatar_url=pr["user"].get("avatar_url"),
            )
            for pr in data
        ]

    async def get_pull_request(
        self,
        owner: str,
        repo: str,
        number: int,
    ) -> GitHubPullRequest:
        """Get a specific pull request.

        Args:
            owner: Repository owner.
            repo: Repository name.
            number: PR number.

        Returns:
            GitHubPullRequest with full details.
        """
        data = await self._request("GET", f"/repos/{owner}/{repo}/pulls/{number}")
        if not isinstance(data, dict):
            raise GitHubAPIError("Unexpected response format")

        return GitHubPullRequest(
            number=data["number"],
            title=data["title"],
            body=data.get("body"),
            state=data["state"],
            merged=data.get("merged", False),
            merged_at=(
                datetime.fromisoformat(data["merged_at"].replace("Z", "+00:00"))
                if data.get("merged_at")
                else None
            ),
            html_url=data["html_url"],
            head_branch=data["head"]["ref"],
            base_branch=data["base"]["ref"],
            author_login=data["user"]["login"],
            author_avatar_url=data["user"].get("avatar_url"),
            additions=data["additions"],
            deletions=data["deletions"],
            changed_files=data["changed_files"],
            draft=data.get("draft", False),
            labels=[lbl["name"] for lbl in data.get("labels", [])],
            requested_reviewers=[rv["login"] for rv in data.get("requested_reviewers", [])],
        )

    async def post_comment(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        body: str,
    ) -> dict[str, Any]:
        """Post a comment on an issue or PR.

        Args:
            owner: Repository owner.
            repo: Repository name.
            issue_number: Issue or PR number.
            body: Comment body (markdown).

        Returns:
            Created comment data.
        """
        result = await self._request(
            "POST",
            f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
            json={"body": body},
        )
        if not isinstance(result, dict):
            raise GitHubAPIError("Unexpected response format")
        return result

    async def get_pull_request_files(
        self,
        owner: str,
        repo: str,
        pr_number: int,
    ) -> list[dict[str, Any]]:
        """Get list of changed files in a PR.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pr_number: PR number.

        Returns:
            List of file information dictionaries.
        """
        result = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/pulls/{pr_number}/files",
            params={"per_page": 100},
        )
        if isinstance(result, list):
            return result
        return []

    async def post_review_comment(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        path: str,
        line: int,
        body: str,
    ) -> dict[str, Any]:
        """Post a review comment on a specific line of a PR.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pr_number: PR number.
            path: File path.
            line: Line number.
            body: Comment body.

        Returns:
            Created comment data.
        """
        result = await self._request(
            "POST",
            f"/repos/{owner}/{repo}/pulls/{pr_number}/comments",
            json={
                "body": body,
                "path": path,
                "line": line,
                "side": "RIGHT",
            },
        )
        if not isinstance(result, dict):
            raise GitHubAPIError("Unexpected response format")
        return result

    # =========================================================================
    # Webhook Operations
    # =========================================================================

    async def create_webhook(
        self,
        owner: str,
        repo: str,
        webhook_url: str,
        webhook_secret: str,
        events: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a webhook on a repository.

        Args:
            owner: Repository owner.
            repo: Repository name.
            webhook_url: URL to receive webhook events.
            webhook_secret: Webhook secret for signature verification.
            events: List of events to subscribe to.

        Returns:
            Created webhook data.
        """
        if events is None:
            events = ["push", "pull_request", "pull_request_review"]

        result = await self._request(
            "POST",
            f"/repos/{owner}/{repo}/hooks",
            json={
                "name": "web",
                "active": True,
                "events": events,
                "config": {
                    "url": webhook_url,
                    "secret": webhook_secret,
                    "content_type": "json",
                    "insecure_ssl": "0",
                },
            },
        )
        if not isinstance(result, dict):
            raise GitHubAPIError("Unexpected response format")
        return result

    async def delete_webhook(
        self,
        owner: str,
        repo: str,
        hook_id: int,
    ) -> None:
        """Delete a webhook from a repository.

        Args:
            owner: Repository owner.
            repo: Repository name.
            hook_id: Webhook ID to delete.
        """
        await self._http_client.delete(f"/repos/{owner}/{repo}/hooks/{hook_id}")

    # =========================================================================
    # Rate Limit
    # =========================================================================

    async def get_rate_limit(self) -> RateLimitInfo:
        """Get current rate limit status.

        Returns:
            RateLimitInfo with limits and usage.
        """
        data = await self._request("GET", "/rate_limit")
        if not isinstance(data, dict):
            raise GitHubAPIError("Unexpected response format")

        core = data["resources"]["core"]
        return RateLimitInfo(
            limit=core["limit"],
            remaining=core["remaining"],
            used=core["used"],
            reset_at=datetime.fromtimestamp(core["reset"], tz=UTC),
        )


__all__ = ["GITHUB_API_URL", "GITHUB_OAUTH_URL", "GitHubClient"]
