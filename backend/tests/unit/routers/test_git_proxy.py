"""Unit tests for git proxy router endpoints.

Tests workspace isolation, request/response mapping, and error propagation.
The _get_provider helper is mocked to return a mock GitProvider so we can
test routing logic without real GitHub API calls.

Pattern: call endpoint functions directly (same as test_github_branch_links.py).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from pilot_space.api.v1.routers.git_proxy import (
    _get_provider,
    create_branch,
    create_commit,
    create_pull_request,
    delete_branch,
    get_default_branch,
    get_file_content,
    get_repo_status,
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
    FileContent,
    GitHubGitProvider,
    GitProviderAuthError,
    GitProviderNotFoundError,
    GitProviderRateLimitError,
    PullRequestResult,
)
from pilot_space.domain.exceptions import AppError, NotFoundError
from pilot_space.infrastructure.database.models import IntegrationProvider

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

WORKSPACE_ID = uuid4()
OWNER = "acme"
REPO = "widget"


def _make_session() -> AsyncMock:
    return AsyncMock()


def _make_current_user() -> MagicMock:
    user = MagicMock()
    user.user_id = uuid4()
    return user


def _make_integration(workspace_id=None, is_active=True):
    """Build a mock Integration ORM object."""
    integration = MagicMock()
    integration.id = uuid4()
    integration.workspace_id = workspace_id or WORKSPACE_ID
    integration.is_active = is_active
    integration.access_token = "encrypted-token"  # pragma: allowlist secret
    integration.provider = IntegrationProvider.GITHUB
    return integration


def _make_provider_mock() -> AsyncMock:
    """Build a mock GitProvider."""
    mock = AsyncMock(spec=GitHubGitProvider)
    mock.aclose = AsyncMock()
    return mock


# ---------------------------------------------------------------------------
# _get_provider isolation tests
# ---------------------------------------------------------------------------


class TestGetProvider:
    """Tests for the _get_provider helper."""

    @pytest.mark.asyncio
    async def test_raises_not_found_when_no_integration(self) -> None:
        """Raises NotFoundError when no GitHub integration exists for workspace."""
        session = _make_session()

        with patch("pilot_space.api.v1.routers.git_proxy.IntegrationRepository") as MockRepo:
            repo_instance = AsyncMock()
            repo_instance.get_by_provider = AsyncMock(return_value=None)
            MockRepo.return_value = repo_instance

            with pytest.raises(NotFoundError):
                await _get_provider(session, WORKSPACE_ID, OWNER, REPO)

    @pytest.mark.asyncio
    async def test_raises_app_error_when_integration_inactive(self) -> None:
        """Raises AppError when the integration is inactive."""
        session = _make_session()
        integration = _make_integration(is_active=False)

        with patch("pilot_space.api.v1.routers.git_proxy.IntegrationRepository") as MockRepo:
            repo_instance = AsyncMock()
            repo_instance.get_by_provider = AsyncMock(return_value=integration)
            MockRepo.return_value = repo_instance

            with pytest.raises(AppError):
                await _get_provider(session, WORKSPACE_ID, OWNER, REPO)

    @pytest.mark.asyncio
    async def test_raises_not_found_for_wrong_workspace(self) -> None:
        """Raises NotFoundError when integration belongs to different workspace."""
        session = _make_session()
        other_workspace_id = uuid4()
        integration = _make_integration(workspace_id=other_workspace_id)

        with patch("pilot_space.api.v1.routers.git_proxy.IntegrationRepository") as MockRepo:
            repo_instance = AsyncMock()
            repo_instance.get_by_provider = AsyncMock(return_value=integration)
            MockRepo.return_value = repo_instance

            with pytest.raises(NotFoundError):
                await _get_provider(session, WORKSPACE_ID, OWNER, REPO)

    @pytest.mark.asyncio
    async def test_returns_github_provider_on_success(self) -> None:
        """Returns a GitHubGitProvider when integration is active and workspace matches."""
        session = _make_session()
        integration = _make_integration()

        with (
            patch("pilot_space.api.v1.routers.git_proxy.IntegrationRepository") as MockRepo,
            patch(
                "pilot_space.api.v1.routers.git_proxy.decrypt_api_key",
                return_value="plain-token",
            ),
        ):
            repo_instance = AsyncMock()
            repo_instance.get_by_provider = AsyncMock(return_value=integration)
            MockRepo.return_value = repo_instance

            provider = await _get_provider(session, WORKSPACE_ID, OWNER, REPO)

        assert isinstance(provider, GitHubGitProvider)


# ---------------------------------------------------------------------------
# list_branches
# ---------------------------------------------------------------------------


class TestListBranches:
    @pytest.mark.asyncio
    async def test_list_branches_returns_branch_list(self) -> None:
        """GET branches returns BranchListResponse with all branches."""
        session = _make_session()
        current_user = _make_current_user()

        mock_provider = AsyncMock()
        mock_provider.get_branches = AsyncMock(
            return_value=[
                BranchInfo(name="main", sha="abc", is_default=True, is_protected=True),
                BranchInfo(name="feat/x", sha="def", is_default=False, is_protected=False),
            ]
        )

        with patch(
            "pilot_space.api.v1.routers.git_proxy._get_provider",
            new_callable=AsyncMock,
            return_value=mock_provider,
        ):
            result = await list_branches(session, current_user, WORKSPACE_ID, OWNER, REPO)

        assert len(result.branches) == 2
        assert result.branches[0].name == "main"
        assert result.branches[0].is_default is True
        assert result.total == 2

    @pytest.mark.asyncio
    async def test_list_branches_propagates_auth_error(self) -> None:
        """GitProviderAuthError propagates from list_branches endpoint."""
        session = _make_session()
        current_user = _make_current_user()

        mock_provider = AsyncMock()
        mock_provider.get_branches = AsyncMock(side_effect=GitProviderAuthError("Bad token"))

        with (
            patch(
                "pilot_space.api.v1.routers.git_proxy._get_provider",
                new_callable=AsyncMock,
                return_value=mock_provider,
            ),
            pytest.raises(GitProviderAuthError),
        ):
            await list_branches(session, current_user, WORKSPACE_ID, OWNER, REPO)


# ---------------------------------------------------------------------------
# create_branch
# ---------------------------------------------------------------------------


class TestCreateBranch:
    @pytest.mark.asyncio
    async def test_create_branch_returns_201(self) -> None:
        """POST branches returns the new branch info."""
        session = _make_session()
        current_user = _make_current_user()
        body = CreateBranchRequest(name="feat/new", source_branch="main")

        mock_provider = AsyncMock()
        mock_provider.create_branch = AsyncMock(
            return_value=BranchInfo(name="feat/new", sha="xyz", is_default=False)
        )

        with patch(
            "pilot_space.api.v1.routers.git_proxy._get_provider",
            new_callable=AsyncMock,
            return_value=mock_provider,
        ):
            result = await create_branch(session, current_user, WORKSPACE_ID, OWNER, REPO, body)

        assert result.name == "feat/new"
        assert result.sha == "xyz"
        mock_provider.create_branch.assert_called_once_with("feat/new", "main")


# ---------------------------------------------------------------------------
# delete_branch
# ---------------------------------------------------------------------------


class TestDeleteBranch:
    @pytest.mark.asyncio
    async def test_delete_branch_calls_provider(self) -> None:
        """DELETE branch calls provider.delete_branch with correct name."""
        session = _make_session()
        current_user = _make_current_user()

        mock_provider = AsyncMock()
        mock_provider.delete_branch = AsyncMock(return_value=None)

        with patch(
            "pilot_space.api.v1.routers.git_proxy._get_provider",
            new_callable=AsyncMock,
            return_value=mock_provider,
        ):
            response = await delete_branch(
                session, current_user, WORKSPACE_ID, OWNER, REPO, "feat/old"
            )

        mock_provider.delete_branch.assert_called_once_with("feat/old")
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_branch_propagates_not_found(self) -> None:
        """GitProviderNotFoundError propagates from delete_branch."""
        session = _make_session()
        current_user = _make_current_user()

        mock_provider = AsyncMock()
        mock_provider.delete_branch = AsyncMock(
            side_effect=GitProviderNotFoundError("Branch not found")
        )

        with (
            patch(
                "pilot_space.api.v1.routers.git_proxy._get_provider",
                new_callable=AsyncMock,
                return_value=mock_provider,
            ),
            pytest.raises(GitProviderNotFoundError),
        ):
            await delete_branch(session, current_user, WORKSPACE_ID, OWNER, REPO, "nonexistent")


# ---------------------------------------------------------------------------
# get_default_branch
# ---------------------------------------------------------------------------


class TestGetDefaultBranch:
    @pytest.mark.asyncio
    async def test_get_default_branch_returns_dict(self) -> None:
        """GET default-branch returns {'default_branch': 'main'}."""
        session = _make_session()
        current_user = _make_current_user()

        mock_provider = AsyncMock()
        mock_provider.get_default_branch = AsyncMock(return_value="main")

        with patch(
            "pilot_space.api.v1.routers.git_proxy._get_provider",
            new_callable=AsyncMock,
            return_value=mock_provider,
        ):
            result = await get_default_branch(session, current_user, WORKSPACE_ID, OWNER, REPO)

        assert result == {"default_branch": "main"}


# ---------------------------------------------------------------------------
# get_file_content
# ---------------------------------------------------------------------------


class TestGetFileContent:
    @pytest.mark.asyncio
    async def test_get_file_content_returns_decoded_content(self) -> None:
        """GET file returns FileContentResponse with decoded content."""
        session = _make_session()
        current_user = _make_current_user()

        mock_provider = AsyncMock()
        mock_provider.get_file_content = AsyncMock(
            return_value=FileContent(
                content="print('hello')\n",
                sha="file-sha",
                size=16,
            )
        )

        with patch(
            "pilot_space.api.v1.routers.git_proxy._get_provider",
            new_callable=AsyncMock,
            return_value=mock_provider,
        ):
            result = await get_file_content(
                session, current_user, WORKSPACE_ID, OWNER, REPO, "src/main.py", ref="main"
            )

        assert result.content == "print('hello')\n"
        assert result.sha == "file-sha"
        mock_provider.get_file_content.assert_called_once_with("src/main.py", "main")

    @pytest.mark.asyncio
    async def test_get_file_content_too_large_raises_validation_error(self) -> None:
        """Files exceeding 1 MB raise ValidationError."""
        from pilot_space.domain.exceptions import ValidationError

        session = _make_session()
        current_user = _make_current_user()

        # Create content > 1 MB
        big_content = "x" * (1_048_576 + 1)
        mock_provider = AsyncMock()
        mock_provider.get_file_content = AsyncMock(
            return_value=FileContent(content=big_content, sha="sha", size=len(big_content))
        )
        mock_provider.aclose = AsyncMock()

        with (
            patch(
                "pilot_space.api.v1.routers.git_proxy._get_provider",
                new_callable=AsyncMock,
                return_value=mock_provider,
            ),
            pytest.raises(ValidationError, match="1 MB"),
        ):
            await get_file_content(
                session, current_user, WORKSPACE_ID, OWNER, REPO, "big.py", ref="main"
            )


# ---------------------------------------------------------------------------
# get_repo_status
# ---------------------------------------------------------------------------


class TestGetRepoStatus:
    @pytest.mark.asyncio
    async def test_get_repo_status_returns_changed_files(self) -> None:
        """GET status returns RepoStatusResponse with file diffs."""
        session = _make_session()
        current_user = _make_current_user()

        mock_provider = AsyncMock()
        mock_provider.get_repo_status = AsyncMock(
            return_value=[
                ChangedFile(path="src/app.py", status="modified", additions=3, deletions=1),
            ]
        )

        with patch(
            "pilot_space.api.v1.routers.git_proxy._get_provider",
            new_callable=AsyncMock,
            return_value=mock_provider,
        ):
            result = await get_repo_status(
                session,
                current_user,
                WORKSPACE_ID,
                OWNER,
                REPO,
                base_branch="main",
                head_branch="feat/x",
            )

        assert result.total_files == 1
        assert result.files[0].path == "src/app.py"
        assert result.base_branch == "main"
        assert result.head_branch == "feat/x"


# ---------------------------------------------------------------------------
# create_commit
# ---------------------------------------------------------------------------


class TestCreateCommit:
    @pytest.mark.asyncio
    async def test_create_commit_returns_commit_response(self) -> None:
        """POST commits returns CommitResponse with sha and URL."""
        session = _make_session()
        current_user = _make_current_user()
        body = CommitRequest(
            branch="main",
            message="fix: update config",
            files=[FileChangeSchema(path="config.py", content="x = 1", action="update")],
        )

        mock_provider = AsyncMock()
        mock_provider.create_commit = AsyncMock(
            return_value=CommitResult(
                sha="abc123",
                html_url="https://github.com/acme/widget/commit/abc123",
                message="fix: update config",
            )
        )

        with patch(
            "pilot_space.api.v1.routers.git_proxy._get_provider",
            new_callable=AsyncMock,
            return_value=mock_provider,
        ):
            result = await create_commit(session, current_user, WORKSPACE_ID, OWNER, REPO, body)

        assert result.sha == "abc123"
        assert "commit/abc123" in result.html_url
        assert result.message == "fix: update config"

    @pytest.mark.asyncio
    async def test_create_commit_propagates_rate_limit_error(self) -> None:
        """GitProviderRateLimitError propagates from create_commit endpoint."""
        session = _make_session()
        current_user = _make_current_user()
        body = CommitRequest(
            branch="main",
            message="fix: something",
            files=[FileChangeSchema(path="f.py", content="x", action="update")],
        )

        mock_provider = AsyncMock()
        mock_provider.create_commit = AsyncMock(
            side_effect=GitProviderRateLimitError("Rate limited", retry_after=30)
        )

        with (
            patch(
                "pilot_space.api.v1.routers.git_proxy._get_provider",
                new_callable=AsyncMock,
                return_value=mock_provider,
            ),
            pytest.raises(GitProviderRateLimitError),
        ):
            await create_commit(session, current_user, WORKSPACE_ID, OWNER, REPO, body)


# ---------------------------------------------------------------------------
# create_pull_request
# ---------------------------------------------------------------------------


class TestCreatePullRequest:
    @pytest.mark.asyncio
    async def test_create_pr_returns_pr_response(self) -> None:
        """POST pulls returns PRResponse with number and URL."""
        session = _make_session()
        current_user = _make_current_user()
        body = CreatePRRequest(
            title="Add feature X",
            body="Description",
            head="feat/x",
            base="main",
        )

        mock_provider = AsyncMock()
        mock_provider.create_pull_request = AsyncMock(
            return_value=PullRequestResult(
                number=7,
                html_url="https://github.com/acme/widget/pull/7",
                title="Add feature X",
                draft=False,
            )
        )

        with patch(
            "pilot_space.api.v1.routers.git_proxy._get_provider",
            new_callable=AsyncMock,
            return_value=mock_provider,
        ):
            result = await create_pull_request(
                session, current_user, WORKSPACE_ID, OWNER, REPO, body
            )

        assert result.number == 7
        assert result.html_url == "https://github.com/acme/widget/pull/7"
        assert result.draft is False
        mock_provider.create_pull_request.assert_called_once_with(
            "Add feature X", "Description", "feat/x", "main", draft=False
        )
