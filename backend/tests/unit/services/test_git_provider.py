"""Unit tests for GitHubGitProvider.

Tests the GitHub Git Data API integration using mocked httpx responses.
All tests mock the AsyncClient to avoid real network calls.
"""

from __future__ import annotations

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pilot_space.application.services.git_provider import (
    BranchInfo,
    CommitResult,
    FileChange,
    FileContent,
    GitHubGitProvider,
    GitProvider,
    GitProviderAuthError,
    GitProviderError,
    GitProviderNotFoundError,
    GitProviderRateLimitError,
    PullRequestResult,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_provider() -> GitHubGitProvider:
    """Create a GitHubGitProvider with a mocked httpx client."""
    return GitHubGitProvider(token="test-token", owner="acme", repo="widget")


def _mock_response(status_code: int, data: dict | list, headers: dict | None = None) -> MagicMock:
    """Build a mock httpx response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = data
    resp.content = True  # truthy — .json() will be called
    resp.text = str(data)
    resp.headers = headers or {}
    return resp


# ---------------------------------------------------------------------------
# GitProvider ABC
# ---------------------------------------------------------------------------


def test_git_provider_is_abstract() -> None:
    """GitProvider should be an abstract base class."""
    import inspect

    assert inspect.isabstract(GitProvider)


# ---------------------------------------------------------------------------
# get_branches
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_branches_returns_branch_list() -> None:
    """get_branches() returns a list of BranchInfo with is_default flag set."""
    provider = _make_provider()

    branches_data = [
        {"name": "main", "commit": {"sha": "abc123"}, "protected": True},
        {"name": "feat/foo", "commit": {"sha": "def456"}, "protected": False},
    ]
    repo_data = {"default_branch": "main"}

    responses = [
        _mock_response(200, branches_data),
        _mock_response(200, repo_data),  # get_default_branch call
    ]

    with patch.object(provider._client, "request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = responses
        result = await provider.get_branches()

    assert len(result) == 2
    assert result[0].name == "main"
    assert result[0].is_default is True
    assert result[0].is_protected is True
    assert result[0].sha == "abc123"
    assert result[1].name == "feat/foo"
    assert result[1].is_default is False


@pytest.mark.asyncio
async def test_get_branches_401_raises_auth_error() -> None:
    """401 from GitHub raises GitProviderAuthError."""
    provider = _make_provider()

    with patch.object(provider._client, "request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = _mock_response(401, {"message": "Bad credentials"})
        with pytest.raises(GitProviderAuthError):
            await provider.get_branches()


@pytest.mark.asyncio
async def test_get_branches_429_raises_rate_limit_error() -> None:
    """429 from GitHub raises GitProviderRateLimitError."""
    provider = _make_provider()

    with patch.object(provider._client, "request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = _mock_response(
            429,
            {"message": "API rate limit exceeded"},
            headers={"Retry-After": "30"},
        )
        with pytest.raises(GitProviderRateLimitError):
            await provider.get_branches()


# ---------------------------------------------------------------------------
# get_default_branch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_default_branch_returns_name() -> None:
    """get_default_branch() returns the default_branch string."""
    provider = _make_provider()

    with patch.object(provider._client, "request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = _mock_response(200, {"default_branch": "main", "id": 1})
        result = await provider.get_default_branch()

    assert result == "main"


# ---------------------------------------------------------------------------
# get_file_content
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_file_content_decodes_base64() -> None:
    """get_file_content() decodes base64 content from GitHub API."""
    provider = _make_provider()

    raw = "print('hello')\n"
    encoded = base64.b64encode(raw.encode()).decode()

    with patch.object(provider._client, "request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = _mock_response(
            200,
            {
                "content": encoded,
                "encoding": "base64",
                "sha": "file-sha-123",
                "size": len(raw),
            },
        )
        result = await provider.get_file_content("src/main.py", "main")

    assert isinstance(result, FileContent)
    assert result.content == raw
    assert result.sha == "file-sha-123"
    assert result.size == len(raw)


@pytest.mark.asyncio
async def test_get_file_content_404_raises_not_found() -> None:
    """404 from GitHub raises GitProviderNotFoundError."""
    provider = _make_provider()

    with patch.object(provider._client, "request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = _mock_response(404, {"message": "Not Found"})
        with pytest.raises(GitProviderNotFoundError):
            await provider.get_file_content("nonexistent.py", "main")


# ---------------------------------------------------------------------------
# create_commit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_commit_calls_git_data_api_sequence() -> None:
    """create_commit() calls get_ref -> get_commit -> create_blob -> create_tree ->
    create_commit -> update_ref in order."""
    provider = _make_provider()

    # The sequence of GitHub API calls:
    # 1. GET /git/refs/heads/main (get HEAD sha)
    # 2. GET /git/commits/{sha} (get tree sha)
    # 3. POST /git/blobs (create blob)
    # 4. POST /git/trees (create tree)
    # 5. POST /git/commits (create commit)
    # 6. PATCH /git/refs/heads/main (update ref)

    responses = [
        _mock_response(200, {"object": {"sha": "head-sha"}}),  # get ref
        _mock_response(200, {"tree": {"sha": "base-tree-sha"}}),  # get commit
        _mock_response(201, {"sha": "blob-sha"}),  # create blob
        _mock_response(201, {"sha": "new-tree-sha"}),  # create tree
        _mock_response(201, {"sha": "new-commit-sha"}),  # create commit
        _mock_response(
            200, {"ref": "refs/heads/main", "object": {"sha": "new-commit-sha"}}
        ),  # update ref
    ]

    with patch.object(provider._client, "request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = responses
        result = await provider.create_commit(
            branch="main",
            message="fix: update config",
            files=[FileChange(path="config.py", content="x = 1", action="update")],
        )

    assert isinstance(result, CommitResult)
    assert result.sha == "new-commit-sha"
    assert "acme/widget/commit/new-commit-sha" in result.html_url
    assert mock_req.call_count == 6


@pytest.mark.asyncio
async def test_create_commit_skips_blob_for_delete_action() -> None:
    """Deleted files use sha=None in tree (no blob created)."""
    provider = _make_provider()

    responses = [
        _mock_response(200, {"object": {"sha": "head-sha"}}),
        _mock_response(200, {"tree": {"sha": "base-tree-sha"}}),
        # No blob creation for delete
        _mock_response(201, {"sha": "new-tree-sha"}),
        _mock_response(201, {"sha": "new-commit-sha"}),
        _mock_response(200, {"ref": "refs/heads/main", "object": {"sha": "new-commit-sha"}}),
    ]

    with patch.object(provider._client, "request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = responses
        result = await provider.create_commit(
            branch="main",
            message="chore: remove old file",
            files=[FileChange(path="old.py", content="", action="delete")],
        )

    assert result.sha == "new-commit-sha"
    # 5 calls: get_ref, get_commit, create_tree, create_commit, update_ref
    assert mock_req.call_count == 5


# ---------------------------------------------------------------------------
# create_pull_request
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_pull_request_returns_pr_result() -> None:
    """create_pull_request() returns PullRequestResult with number and URL."""
    provider = _make_provider()

    with patch.object(provider._client, "request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = _mock_response(
            201,
            {
                "number": 42,
                "html_url": "https://github.com/acme/widget/pull/42",
                "title": "Add feature X",
                "draft": False,
            },
        )
        result = await provider.create_pull_request(
            title="Add feature X",
            body="Description here",
            head="feat/x",
            base="main",
        )

    assert isinstance(result, PullRequestResult)
    assert result.number == 42
    assert result.html_url == "https://github.com/acme/widget/pull/42"
    assert result.draft is False


# ---------------------------------------------------------------------------
# compare_branches
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compare_branches_returns_changed_files() -> None:
    """compare_branches() maps GitHub compare response to ChangedFile list."""
    provider = _make_provider()

    compare_data = {
        "files": [
            {
                "filename": "src/app.py",
                "status": "modified",
                "additions": 5,
                "deletions": 2,
                "patch": "@@ -1,3 +1,6 @@\n+new line",
            },
            {
                "filename": "tests/test_app.py",
                "status": "added",
                "additions": 20,
                "deletions": 0,
            },
        ]
    }

    with patch.object(provider._client, "request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = _mock_response(200, compare_data)
        result = await provider.compare_branches("main", "feat/x")

    assert len(result) == 2
    assert result[0].path == "src/app.py"
    assert result[0].status == "modified"
    assert result[0].additions == 5
    assert result[0].patch is not None
    assert result[1].path == "tests/test_app.py"
    assert result[1].status == "added"


# ---------------------------------------------------------------------------
# error mapping
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_403_with_rate_limit_message_raises_rate_limit_error() -> None:
    """403 with 'rate limit' in message should raise GitProviderRateLimitError."""
    provider = _make_provider()

    with patch.object(provider._client, "request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = _mock_response(
            403,
            {"message": "API rate limit exceeded for user ID 1"},
            headers={"Retry-After": "60"},
        )
        with pytest.raises(GitProviderRateLimitError):
            await provider.get_default_branch()


@pytest.mark.asyncio
async def test_403_without_rate_limit_message_raises_auth_error() -> None:
    """403 without rate limit message should raise GitProviderAuthError."""
    provider = _make_provider()

    with patch.object(provider._client, "request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = _mock_response(
            403,
            {"message": "Resource not accessible by personal access token"},
        )
        with pytest.raises(GitProviderAuthError):
            await provider.get_default_branch()


@pytest.mark.asyncio
async def test_500_raises_git_provider_error() -> None:
    """5xx from GitHub raises base GitProviderError."""
    provider = _make_provider()

    with patch.object(provider._client, "request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = _mock_response(500, {"message": "Internal Server Error"})
        with pytest.raises(GitProviderError):
            await provider.get_default_branch()


# ---------------------------------------------------------------------------
# create_branch / delete_branch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_branch_returns_branch_info() -> None:
    """create_branch() resolves source SHA and returns BranchInfo."""
    provider = _make_provider()

    with patch.object(provider._client, "request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = [
            _mock_response(200, {"object": {"sha": "source-sha"}}),  # get_head_sha
            _mock_response(201, {"ref": "refs/heads/feat/new", "object": {"sha": "source-sha"}}),
        ]
        result = await provider.create_branch("feat/new", "main")

    assert isinstance(result, BranchInfo)
    assert result.name == "feat/new"
    assert result.sha == "source-sha"


@pytest.mark.asyncio
async def test_delete_branch_calls_delete_endpoint() -> None:
    """delete_branch() calls DELETE on the git refs endpoint."""
    provider = _make_provider()

    with patch.object(provider._client, "request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = _mock_response(204, {})
        # 204 No Content — no JSON body, so content is empty
        mock_req.return_value.content = False
        await provider.delete_branch("feat/old")

    mock_req.assert_called_once()
    call_args = mock_req.call_args
    assert call_args[0][0] == "DELETE"
    assert "refs/heads/feat/old" in call_args[0][1]
