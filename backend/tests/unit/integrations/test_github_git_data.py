"""Tests for GitHub Git Data API methods (GitDataMixin on GitHubClient).

Uses httpx MockTransport to avoid real GitHub API calls.
"""

from __future__ import annotations

import httpx
import pytest

from pilot_space.integrations.github.client import GitHubClient
from pilot_space.integrations.github.exceptions import (
    GitHubAPIError,
    GitHubRateLimitError,
)

pytestmark = pytest.mark.asyncio


def _mock_transport(
    responses: dict[str, tuple[int, dict | list]],
) -> httpx.MockTransport:
    """Create a mock transport returning predefined responses by URL path."""

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        for route_path, (status_code, body) in responses.items():
            if path == route_path or path.endswith(route_path):
                return httpx.Response(
                    status_code,
                    json=body,
                    headers={
                        "X-RateLimit-Remaining": "4999",
                        "X-RateLimit-Reset": "1700000000",
                    },
                )
        return httpx.Response(
            404,
            json={"message": "Not Found"},
            headers={
                "X-RateLimit-Remaining": "4999",
                "X-RateLimit-Reset": "1700000000",
            },
        )

    return httpx.MockTransport(handler)


def _make_client(
    responses: dict[str, tuple[int, dict | list]],
) -> GitHubClient:
    """Create a GitHubClient with mocked transport."""
    client = GitHubClient(access_token="test-token")
    client._http_client = httpx.AsyncClient(
        transport=_mock_transport(responses),
        base_url="https://api.github.com",
        headers={"Authorization": "Bearer test-token"},
    )
    return client


class TestGetRef:
    async def test_get_ref_returns_ref_data(self) -> None:
        client = _make_client(
            {
                "/repos/owner/repo/git/refs/heads/main": (
                    200,
                    {
                        "ref": "refs/heads/main",
                        "object": {"sha": "abc123", "type": "commit"},
                    },
                ),
            }
        )
        data = await client.get_ref("owner", "repo", "main")
        assert data["object"]["sha"] == "abc123"
        assert data["ref"] == "refs/heads/main"


class TestCreateBlob:
    async def test_create_blob_returns_sha(self) -> None:
        client = _make_client(
            {
                "/repos/owner/repo/git/blobs": (
                    201,
                    {"sha": "blob-sha-123", "url": "https://api.github.com/..."},
                ),
            }
        )
        sha = await client.create_blob("owner", "repo", "hello world")
        assert sha == "blob-sha-123"


class TestCreateTree:
    async def test_create_tree_returns_sha(self) -> None:
        client = _make_client(
            {
                "/repos/owner/repo/git/trees": (
                    201,
                    {"sha": "tree-sha-456", "url": "https://api.github.com/..."},
                ),
            }
        )
        sha = await client.create_tree(
            "owner",
            "repo",
            "base-tree-sha",
            [{"path": "file.txt", "mode": "100644", "type": "blob", "sha": "blob-sha"}],
        )
        assert sha == "tree-sha-456"


class TestCreateGitCommit:
    async def test_create_git_commit_returns_sha(self) -> None:
        client = _make_client(
            {
                "/repos/owner/repo/git/commits": (
                    201,
                    {"sha": "commit-sha-789", "message": "test commit"},
                ),
            }
        )
        sha = await client.create_git_commit(
            "owner", "repo", "test commit", "tree-sha", ["parent-sha"]
        )
        assert sha == "commit-sha-789"


class TestCompareCommits:
    async def test_compare_commits_returns_file_list(self) -> None:
        client = _make_client(
            {
                "/repos/owner/repo/compare/base...head": (
                    200,
                    {
                        "files": [
                            {
                                "filename": "src/app.py",
                                "status": "modified",
                                "additions": 10,
                                "deletions": 5,
                                "patch": "@@ -1,5 +1,10 @@",
                            }
                        ],
                        "ahead_by": 3,
                        "behind_by": 0,
                        "total_commits": 3,
                    },
                ),
            }
        )
        data = await client.compare_commits("owner", "repo", "base", "head")
        assert len(data["files"]) == 1
        assert data["files"][0]["filename"] == "src/app.py"
        assert data["ahead_by"] == 3


class TestCreatePullRequest:
    async def test_create_pull_request_returns_pr_data(self) -> None:
        client = _make_client(
            {
                "/repos/owner/repo/pulls": (
                    201,
                    {
                        "number": 42,
                        "html_url": "https://github.com/owner/repo/pull/42",
                        "title": "Test PR",
                        "draft": False,
                    },
                ),
            }
        )
        data = await client.create_pull_request(
            "owner", "repo", "Test PR", "PR body", "feature", "main"
        )
        assert data["number"] == 42
        assert data["html_url"] == "https://github.com/owner/repo/pull/42"


class TestRateLimitHandling:
    async def test_rate_limit_error_on_429(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                429,
                json={"message": "rate limit exceeded"},
                headers={
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": "1700000000",
                },
            )

        client = GitHubClient(access_token="test-token")
        client._http_client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="https://api.github.com",
        )
        with pytest.raises(GitHubRateLimitError):
            await client.get_ref("owner", "repo", "main")


class TestUpdateRef:
    async def test_update_ref_returns_updated_data(self) -> None:
        client = _make_client(
            {
                "/repos/owner/repo/git/refs/heads/main": (
                    200,
                    {
                        "ref": "refs/heads/main",
                        "object": {"sha": "new-sha-xyz", "type": "commit"},
                    },
                ),
            }
        )
        data = await client.update_ref("owner", "repo", "main", "new-sha-xyz")
        assert data["object"]["sha"] == "new-sha-xyz"


class TestDeleteBranch:
    async def test_delete_branch_no_content(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                204,
                headers={
                    "X-RateLimit-Remaining": "4999",
                    "X-RateLimit-Reset": "1700000000",
                },
            )

        client = GitHubClient(access_token="test-token")
        client._http_client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="https://api.github.com",
        )
        # Should not raise
        await client.delete_branch("owner", "repo", "feature-branch")


class TestListBranches:
    async def test_list_branches_returns_list(self) -> None:
        client = _make_client(
            {
                "/repos/owner/repo/branches": (
                    200,
                    [
                        {"name": "main", "commit": {"sha": "abc"}, "protected": True},
                        {"name": "dev", "commit": {"sha": "def"}, "protected": False},
                    ],
                ),
            }
        )
        branches = await client.list_branches("owner", "repo")
        assert len(branches) == 2
        assert branches[0]["name"] == "main"


class TestGetFileContent:
    async def test_get_file_content_returns_data(self) -> None:
        client = _make_client(
            {
                "/repos/owner/repo/contents/src/main.py": (
                    200,
                    {
                        "content": "cHJpbnQoJ2hlbGxvJyk=\n",
                        "encoding": "base64",
                        "name": "main.py",
                        "path": "src/main.py",
                    },
                ),
            }
        )
        data = await client.get_file_content("owner", "repo", "src/main.py", "main")
        assert data["encoding"] == "base64"
        assert "content" in data


class TestApiErrorHandling:
    async def test_404_raises_api_error(self) -> None:
        client = _make_client({})
        with pytest.raises(GitHubAPIError, match="Not Found"):
            await client.get_ref("owner", "repo", "nonexistent")
