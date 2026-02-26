"""Unit tests for GitHub MCP tools (github_tools.py).

Tests input validation and integration-not-found branches.
All DB access and external GitHub API calls are mocked.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from pilot_space.ai.tools.github_tools import (
    get_pr_details,
    get_pr_diff,
    post_pr_comment,
    search_code_in_repo,
)
from pilot_space.ai.tools.mcp_server import ToolContext

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ctx(workspace_id: str | None = None) -> ToolContext:
    """Create a ToolContext with a mock db_session."""
    return ToolContext(
        db_session=AsyncMock(),
        workspace_id=workspace_id or str(uuid4()),
        user_id=str(uuid4()),
    )


def _make_integration(
    *,
    default_repo: str = "acme/api",
    access_token: str = "enc-token",
) -> MagicMock:
    """Return a mock Integration with settings for a default repository."""
    m = MagicMock()
    m.id = uuid4()
    m.workspace_id = uuid4()
    m.settings = {"default_repository": default_repo}
    m.access_token = access_token
    return m


# ---------------------------------------------------------------------------
# get_pr_details
# ---------------------------------------------------------------------------


class TestGetPRDetails:
    async def test_invalid_pr_number_zero_returns_error(self) -> None:
        ctx = _make_ctx()
        result = await get_pr_details(pr_number=0, ctx=ctx)
        assert "error" in result
        assert result["found"] is False

    async def test_invalid_pr_number_negative_returns_error(self) -> None:
        ctx = _make_ctx()
        result = await get_pr_details(pr_number=-5, ctx=ctx)
        assert "error" in result
        assert result["found"] is False

    async def test_no_integration_returns_not_found(self) -> None:
        ctx = _make_ctx()
        with patch(
            "pilot_space.ai.tools.github_tools._get_github_integration",
            new=AsyncMock(return_value=(None, "No active GitHub integration found")),
        ):
            result = await get_pr_details(pr_number=1, ctx=ctx)

        assert result["found"] is False
        assert "error" in result

    async def test_valid_pr_number_returns_pr_data(self) -> None:
        ctx = _make_ctx()
        integration = _make_integration()

        mock_pr = MagicMock()
        mock_pr.number = 7
        mock_pr.title = "feat: add login"
        mock_pr.body = "Description"
        mock_pr.state = "open"
        mock_pr.html_url = "https://github.com/acme/api/pull/7"
        mock_pr.merged = False
        mock_pr.draft = False
        mock_pr.author_login = "alice"
        mock_pr.author_avatar_url = "https://avatars.example.com/alice"
        mock_pr.head_branch = "feat/login"
        mock_pr.base_branch = "main"
        mock_pr.additions = 10
        mock_pr.deletions = 2
        mock_pr.changed_files = 3
        mock_pr.merged_at = None
        mock_pr.labels = []
        mock_pr.requested_reviewers = []

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get_pull_request = AsyncMock(return_value=mock_pr)

        with (
            patch(
                "pilot_space.ai.tools.github_tools._get_github_integration",
                new=AsyncMock(return_value=(integration, None)),
            ),
            patch(
                "pilot_space.ai.tools.github_tools.decrypt_api_key",
                return_value="plain-token",
            ),
            patch(
                "pilot_space.ai.tools.github_tools.GitHubClient",
                return_value=mock_client,
            ),
        ):
            result = await get_pr_details(pr_number=7, ctx=ctx)

        assert result["found"] is True
        assert result["pr"]["number"] == 7
        assert result["pr"]["title"] == "feat: add login"


# ---------------------------------------------------------------------------
# get_pr_diff
# ---------------------------------------------------------------------------


class TestGetPRDiff:
    async def test_invalid_pr_number_zero_returns_error(self) -> None:
        ctx = _make_ctx()
        result = await get_pr_diff(pr_number=0, ctx=ctx)
        assert "error" in result
        assert result["found"] is False

    async def test_invalid_pr_number_negative_returns_error(self) -> None:
        ctx = _make_ctx()
        result = await get_pr_diff(pr_number=-1, ctx=ctx)
        assert "error" in result
        assert result["found"] is False

    async def test_no_integration_returns_not_found(self) -> None:
        ctx = _make_ctx()
        with patch(
            "pilot_space.ai.tools.github_tools._get_github_integration",
            new=AsyncMock(return_value=(None, "No active GitHub integration found")),
        ):
            result = await get_pr_diff(pr_number=5, ctx=ctx)

        assert result["found"] is False
        assert "error" in result


# ---------------------------------------------------------------------------
# search_code_in_repo
# ---------------------------------------------------------------------------


class TestSearchCodeInRepo:
    async def test_empty_query_returns_error(self) -> None:
        ctx = _make_ctx()
        result = await search_code_in_repo(query="", ctx=ctx)
        assert "error" in result
        assert result["found"] is False

    async def test_whitespace_only_query_returns_error(self) -> None:
        ctx = _make_ctx()
        result = await search_code_in_repo(query="   ", ctx=ctx)
        assert "error" in result
        assert result["found"] is False

    async def test_no_integration_returns_not_found(self) -> None:
        ctx = _make_ctx()
        with patch(
            "pilot_space.ai.tools.github_tools._get_github_integration",
            new=AsyncMock(return_value=(None, "No active GitHub integration found")),
        ):
            result = await search_code_in_repo(query="def login", ctx=ctx)

        assert result["found"] is False

    async def test_valid_query_returns_note_key(self) -> None:
        ctx = _make_ctx()
        integration = _make_integration()

        with patch(
            "pilot_space.ai.tools.github_tools._get_github_integration",
            new=AsyncMock(return_value=(integration, None)),
        ):
            result = await search_code_in_repo(query="def authenticate", ctx=ctx)

        assert result["found"] is True
        assert "note" in result
        assert "not" in result["note"].lower() or "not yet" in result["note"].lower()

    async def test_valid_query_returns_empty_matches(self) -> None:
        ctx = _make_ctx()
        integration = _make_integration()

        with patch(
            "pilot_space.ai.tools.github_tools._get_github_integration",
            new=AsyncMock(return_value=(integration, None)),
        ):
            result = await search_code_in_repo(query="class UserService", ctx=ctx)

        assert result["matches"] == []

    async def test_full_query_includes_repo_filter(self) -> None:
        ctx = _make_ctx()
        integration = _make_integration(default_repo="myorg/myrepo")

        with patch(
            "pilot_space.ai.tools.github_tools._get_github_integration",
            new=AsyncMock(return_value=(integration, None)),
        ):
            result = await search_code_in_repo(query="def login", ctx=ctx)

        assert "repo:myorg/myrepo" in result["query"]


# ---------------------------------------------------------------------------
# post_pr_comment
# ---------------------------------------------------------------------------


class TestPostPRComment:
    async def test_empty_body_returns_error(self) -> None:
        ctx = _make_ctx()
        result = await post_pr_comment(pr_number=1, body="", ctx=ctx)
        assert "error" in result
        assert result["posted"] is False

    async def test_whitespace_body_returns_error(self) -> None:
        ctx = _make_ctx()
        result = await post_pr_comment(pr_number=1, body="   ", ctx=ctx)
        assert "error" in result
        assert result["posted"] is False

    async def test_invalid_pr_number_zero_returns_error(self) -> None:
        ctx = _make_ctx()
        result = await post_pr_comment(pr_number=0, body="LGTM", ctx=ctx)
        assert "error" in result
        assert result["posted"] is False

    async def test_invalid_pr_number_negative_returns_error(self) -> None:
        ctx = _make_ctx()
        result = await post_pr_comment(pr_number=-3, body="Looks good", ctx=ctx)
        assert "error" in result
        assert result["posted"] is False

    async def test_line_without_path_returns_error(self) -> None:
        ctx = _make_ctx()
        result = await post_pr_comment(
            pr_number=5,
            body="Nit: rename this",
            ctx=ctx,
            path="",
            line=10,
        )
        assert "error" in result
        assert result["posted"] is False

    async def test_no_integration_returns_not_posted(self) -> None:
        ctx = _make_ctx()
        with patch(
            "pilot_space.ai.tools.github_tools._get_github_integration",
            new=AsyncMock(return_value=(None, "No active GitHub integration found")),
        ):
            result = await post_pr_comment(pr_number=1, body="Looks good", ctx=ctx)

        assert result["posted"] is False
        assert "error" in result

    async def test_valid_general_comment_posted(self) -> None:
        ctx = _make_ctx()
        integration = _make_integration()

        mock_comment = {
            "id": 999,
            "html_url": "https://github.com/acme/api/pull/1#issuecomment-999",
        }

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post_comment = AsyncMock(return_value=mock_comment)

        with (
            patch(
                "pilot_space.ai.tools.github_tools._get_github_integration",
                new=AsyncMock(return_value=(integration, None)),
            ),
            patch(
                "pilot_space.ai.tools.github_tools.decrypt_api_key",
                return_value="plain-token",
            ),
            patch(
                "pilot_space.ai.tools.github_tools.GitHubClient",
                return_value=mock_client,
            ),
        ):
            result = await post_pr_comment(pr_number=1, body="LGTM, ship it!", ctx=ctx)

        assert result["posted"] is True
        assert result["comment_id"] == 999
        assert result["type"] == "general_comment"
