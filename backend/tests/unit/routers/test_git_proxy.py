"""Unit tests for the git proxy router endpoints.

Tests all /api/v1/git/* proxy endpoints by mocking the _get_provider helper
to return a mock GitProvider. Covers happy paths, error mapping (429/401/502),
validation (empty commit message, empty files list), and the 1MB file guard.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from pilot_space.api.v1.routers.git_proxy import (
    create_branch,
    create_commit,
    create_pull_request,
    delete_branch,
    get_file_content,
    get_status,
    list_branches,
)
from pilot_space.api.v1.schemas.git_proxy import (
    CommitRequest,
    CreateBranchRequest,
    CreatePRRequest,
    FileChangeSchema,
)
from pilot_space.application.services.git_provider import (
    BranchInfo,
    ChangedFile,
    CommitResult,
    PullRequestResult,
)
from pilot_space.integrations.github.exceptions import (
    GitHubAPIError,
    GitHubAuthError,
    GitHubRateLimitError,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

INTEGRATION_ID = uuid4()


def _mock_user() -> MagicMock:
    user = MagicMock()
    user.user_id = uuid4()
    return user


def _mock_session() -> AsyncMock:
    return AsyncMock()


def _mock_provider() -> AsyncMock:
    """Create a mock GitProvider with all methods as AsyncMock."""
    return AsyncMock()


# ---------------------------------------------------------------------------
# GET /repos/{owner}/{repo}/status
# ---------------------------------------------------------------------------


class TestGetStatus:
    """Tests for the get_status endpoint."""

    @pytest.mark.asyncio
    @patch("pilot_space.api.v1.routers.git_proxy._get_provider")
    async def test_get_status_returns_files(self, mock_get_prov: AsyncMock) -> None:
        provider = _mock_provider()
        provider.get_changed_files.return_value = [
            ChangedFile(
                path="src/main.ts", status="modified", additions=10, deletions=2, patch="@@ ..."
            ),
            ChangedFile(path="README.md", status="added", additions=5, deletions=0),
        ]
        mock_get_prov.return_value = provider

        result = await get_status(
            session=_mock_session(),
            current_user=_mock_user(),
            owner="org",
            repo="repo",
            branch="main",
            base_ref="develop",
            integration_id=INTEGRATION_ID,
        )

        assert result.total_files == 2
        assert result.branch == "main"
        assert result.truncated is False
        assert result.files[0].path == "src/main.ts"

    @pytest.mark.asyncio
    @patch("pilot_space.api.v1.routers.git_proxy._get_provider")
    async def test_get_status_truncated_when_300_files(self, mock_get_prov: AsyncMock) -> None:
        provider = _mock_provider()
        provider.get_changed_files.return_value = [
            ChangedFile(path=f"file_{i}.ts", status="modified") for i in range(300)
        ]
        mock_get_prov.return_value = provider

        result = await get_status(
            session=_mock_session(),
            current_user=_mock_user(),
            owner="org",
            repo="repo",
            branch="main",
            base_ref="develop",
            integration_id=INTEGRATION_ID,
        )

        assert result.truncated is True
        assert result.total_files == 300


# ---------------------------------------------------------------------------
# GET /repos/{owner}/{repo}/files/{path}
# ---------------------------------------------------------------------------


class TestGetFileContent:
    """Tests for the get_file_content endpoint."""

    @pytest.mark.asyncio
    @patch("pilot_space.api.v1.routers.git_proxy._get_provider")
    async def test_get_file_content_returns_content(self, mock_get_prov: AsyncMock) -> None:
        provider = _mock_provider()
        provider.get_file_content.return_value = "console.log('hello');"
        mock_get_prov.return_value = provider

        result = await get_file_content(
            session=_mock_session(),
            current_user=_mock_user(),
            owner="org",
            repo="repo",
            path="src/main.ts",
            ref="main",
            integration_id=INTEGRATION_ID,
        )

        assert result.content == "console.log('hello');"
        assert result.encoding == "utf-8"

    @pytest.mark.asyncio
    @patch("pilot_space.api.v1.routers.git_proxy._get_provider")
    async def test_get_file_content_413_for_large_file(self, mock_get_prov: AsyncMock) -> None:
        provider = _mock_provider()
        # Return content > 1MB
        provider.get_file_content.return_value = "x" * (1_048_577)
        mock_get_prov.return_value = provider

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_file_content(
                session=_mock_session(),
                current_user=_mock_user(),
                owner="org",
                repo="repo",
                path="big_file.bin",
                ref="main",
                integration_id=INTEGRATION_ID,
            )

        assert exc_info.value.status_code == 413
        assert "File too large" in str(exc_info.value.detail)


# ---------------------------------------------------------------------------
# GET /repos/{owner}/{repo}/branches
# ---------------------------------------------------------------------------


class TestListBranches:
    """Tests for the list_branches endpoint."""

    @pytest.mark.asyncio
    @patch("pilot_space.api.v1.routers.git_proxy._get_provider")
    async def test_list_branches_returns_branches(self, mock_get_prov: AsyncMock) -> None:
        provider = _mock_provider()
        provider.list_branches.return_value = [
            BranchInfo(name="main", sha="abc123", is_default=True, is_protected=True),
            BranchInfo(name="develop", sha="def456"),
        ]
        mock_get_prov.return_value = provider

        result = await list_branches(
            session=_mock_session(),
            current_user=_mock_user(),
            owner="org",
            repo="repo",
            integration_id=INTEGRATION_ID,
        )

        assert len(result.branches) == 2
        assert result.branches[0].name == "main"
        assert result.branches[0].is_default is True

    @pytest.mark.asyncio
    @patch("pilot_space.api.v1.routers.git_proxy._get_provider")
    async def test_list_branches_with_search(self, mock_get_prov: AsyncMock) -> None:
        provider = _mock_provider()
        provider.list_branches.return_value = [
            BranchInfo(name="feat/login", sha="abc123"),
        ]
        mock_get_prov.return_value = provider

        result = await list_branches(
            session=_mock_session(),
            current_user=_mock_user(),
            owner="org",
            repo="repo",
            integration_id=INTEGRATION_ID,
            search="feat",
        )

        provider.list_branches.assert_called_once_with(
            "org", "repo", search="feat", page=1, per_page=30
        )
        assert len(result.branches) == 1


# ---------------------------------------------------------------------------
# POST /repos/{owner}/{repo}/commits
# ---------------------------------------------------------------------------


class TestCreateCommit:
    """Tests for the create_commit endpoint."""

    @pytest.mark.asyncio
    @patch("pilot_space.api.v1.routers.git_proxy._get_provider")
    async def test_create_commit_returns_result(self, mock_get_prov: AsyncMock) -> None:
        provider = _mock_provider()
        provider.create_commit.return_value = CommitResult(
            sha="abc123",
            html_url="https://github.com/org/repo/commit/abc123",
            message="fix: typo",
        )
        mock_get_prov.return_value = provider

        body = CommitRequest(
            branch="main",
            message="fix: typo",
            files=[FileChangeSchema(path="README.md", content="# Hello")],
        )

        result = await create_commit(
            session=_mock_session(),
            current_user=_mock_user(),
            owner="org",
            repo="repo",
            integration_id=INTEGRATION_ID,
            body=body,
        )

        assert result.sha == "abc123"
        assert result.html_url == "https://github.com/org/repo/commit/abc123"

    def test_commit_request_rejects_empty_message(self) -> None:
        """CommitRequest validation: message must be non-empty."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CommitRequest(
                branch="main",
                message="",
                files=[FileChangeSchema(path="a.txt", content="x")],
            )

    def test_commit_request_rejects_empty_files(self) -> None:
        """CommitRequest validation: files list must be non-empty."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CommitRequest(
                branch="main",
                message="fix: something",
                files=[],
            )


# ---------------------------------------------------------------------------
# POST /repos/{owner}/{repo}/pulls
# ---------------------------------------------------------------------------


class TestCreatePullRequest:
    """Tests for the create_pull_request endpoint."""

    @pytest.mark.asyncio
    @patch("pilot_space.api.v1.routers.git_proxy._get_provider")
    async def test_create_pull_request_returns_result(self, mock_get_prov: AsyncMock) -> None:
        provider = _mock_provider()
        provider.create_pull_request.return_value = PullRequestResult(
            number=42,
            html_url="https://github.com/org/repo/pull/42",
            title="feat: new feature",
            draft=False,
        )
        mock_get_prov.return_value = provider

        body = CreatePRRequest(
            title="feat: new feature",
            body="Description",
            head="feature-branch",
            base="main",
        )

        result = await create_pull_request(
            session=_mock_session(),
            current_user=_mock_user(),
            owner="org",
            repo="repo",
            integration_id=INTEGRATION_ID,
            body=body,
        )

        assert result.number == 42
        assert result.draft is False

    @pytest.mark.asyncio
    @patch("pilot_space.api.v1.routers.git_proxy._get_provider")
    async def test_create_pull_request_draft(self, mock_get_prov: AsyncMock) -> None:
        provider = _mock_provider()
        provider.create_pull_request.return_value = PullRequestResult(
            number=43,
            html_url="https://github.com/org/repo/pull/43",
            title="wip: draft",
            draft=True,
        )
        mock_get_prov.return_value = provider

        body = CreatePRRequest(
            title="wip: draft",
            body="",
            head="wip-branch",
            base="main",
            draft=True,
        )

        result = await create_pull_request(
            session=_mock_session(),
            current_user=_mock_user(),
            owner="org",
            repo="repo",
            integration_id=INTEGRATION_ID,
            body=body,
        )

        assert result.draft is True
        provider.create_pull_request.assert_called_once_with(
            "org", "repo", "wip: draft", "", "wip-branch", "main", draft=True
        )


# ---------------------------------------------------------------------------
# POST /repos/{owner}/{repo}/branches
# ---------------------------------------------------------------------------


class TestCreateBranch:
    """Tests for the create_branch endpoint."""

    @pytest.mark.asyncio
    @patch("pilot_space.api.v1.routers.git_proxy._get_provider")
    async def test_create_branch_returns_info(self, mock_get_prov: AsyncMock) -> None:
        provider = _mock_provider()
        provider.create_branch.return_value = BranchInfo(name="feat/new", sha="abc123")
        mock_get_prov.return_value = provider

        body = CreateBranchRequest(name="feat/new", from_ref="main")

        result = await create_branch(
            session=_mock_session(),
            current_user=_mock_user(),
            owner="org",
            repo="repo",
            integration_id=INTEGRATION_ID,
            body=body,
        )

        assert result.name == "feat/new"
        assert result.sha == "abc123"


# ---------------------------------------------------------------------------
# DELETE /repos/{owner}/{repo}/branches/{branch_name}
# ---------------------------------------------------------------------------


class TestDeleteBranch:
    """Tests for the delete_branch endpoint."""

    @pytest.mark.asyncio
    @patch("pilot_space.api.v1.routers.git_proxy._get_provider")
    async def test_delete_branch_returns_204(self, mock_get_prov: AsyncMock) -> None:
        provider = _mock_provider()
        provider.delete_branch.return_value = None
        mock_get_prov.return_value = provider

        result = await delete_branch(
            session=_mock_session(),
            current_user=_mock_user(),
            owner="org",
            repo="repo",
            branch_name="feature-x",
            integration_id=INTEGRATION_ID,
        )

        assert result.status_code == 204
        provider.delete_branch.assert_called_once_with("org", "repo", "feature-x")


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Tests for provider error -> HTTP status mapping."""

    @pytest.mark.asyncio
    @patch("pilot_space.api.v1.routers.git_proxy._get_provider")
    async def test_rate_limit_error_returns_429(self, mock_get_prov: AsyncMock) -> None:
        provider = _mock_provider()
        reset_at = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
        provider.get_changed_files.side_effect = GitHubRateLimitError(reset_at=reset_at)
        mock_get_prov.return_value = provider

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_status(
                session=_mock_session(),
                current_user=_mock_user(),
                owner="org",
                repo="repo",
                branch="main",
                base_ref="develop",
                integration_id=INTEGRATION_ID,
            )

        assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    @patch("pilot_space.api.v1.routers.git_proxy._get_provider")
    async def test_auth_error_returns_401(self, mock_get_prov: AsyncMock) -> None:
        provider = _mock_provider()
        provider.list_branches.side_effect = GitHubAuthError("Bad credentials")
        mock_get_prov.return_value = provider

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await list_branches(
                session=_mock_session(),
                current_user=_mock_user(),
                owner="org",
                repo="repo",
                integration_id=INTEGRATION_ID,
            )

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    @patch("pilot_space.api.v1.routers.git_proxy._get_provider")
    async def test_api_error_returns_502(self, mock_get_prov: AsyncMock) -> None:
        provider = _mock_provider()
        provider.get_file_content.side_effect = GitHubAPIError("Server error", status_code=500)
        mock_get_prov.return_value = provider

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_file_content(
                session=_mock_session(),
                current_user=_mock_user(),
                owner="org",
                repo="repo",
                path="file.ts",
                ref="main",
                integration_id=INTEGRATION_ID,
            )

        assert exc_info.value.status_code == 502
