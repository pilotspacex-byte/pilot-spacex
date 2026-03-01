"""Unit tests for the branch-creation endpoint in github_links router.

Tests the RLS pre-check logic, error mapping (409/400/500), and
the workspace-isolation guard by mocking repository and service layers.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from pilot_space.api.v1.routers.github_links import create_branch_for_issue
from pilot_space.api.v1.schemas.integration import CreateBranchRequest
from pilot_space.application.services.integration.create_branch_service import (
    CreateBranchError,
    CreateBranchResult,
)
from pilot_space.infrastructure.database.models import IntegrationLink, IntegrationLinkType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_integration(workspace_id=None):
    integration = MagicMock()
    integration.workspace_id = workspace_id or uuid4()
    integration.is_active = True
    return integration


def _make_issue(workspace_id=None):
    issue = MagicMock()
    issue.workspace_id = workspace_id or uuid4()
    return issue


def _make_link():
    link = MagicMock(spec=IntegrationLink)
    link.id = uuid4()
    link.integration_id = uuid4()
    link.issue_id = uuid4()
    link.link_type = IntegrationLinkType.BRANCH
    link.external_id = "feat/ps-1-test"
    link.external_url = "https://github.com/acme/api/tree/feat/ps-1-test"
    link.title = "feat/ps-1-test"
    link.author_name = None
    link.author_avatar_url = None
    link.link_metadata = {"name": "feat/ps-1-test", "repository": "acme/api"}
    from datetime import UTC, datetime

    link.created_at = datetime.now(UTC)
    return link


def _make_request(branch_name="feat/ps-1-test"):
    return CreateBranchRequest(
        repository="acme/api",
        branch_name=branch_name,
        base_branch="main",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCreateBranchForIssueRLS:
    """Workspace isolation checks."""

    @pytest.mark.asyncio
    async def test_raises_404_when_integration_not_found(self) -> None:
        """Endpoint returns 404 if integration_id does not resolve."""
        session = AsyncMock()
        integration_repo = AsyncMock()
        integration_repo.get_by_id = AsyncMock(return_value=None)

        with (
            patch(
                "pilot_space.api.v1.routers.github_links.IntegrationRepository",
                return_value=integration_repo,
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await create_branch_for_issue(
                session=session,
                current_user=MagicMock(),
                current_user_id=uuid4(),
                issue_id=uuid4(),
                integration_id=uuid4(),
                request=_make_request(),
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_404_when_issue_workspace_mismatches_integration(self) -> None:
        """Issue from a different workspace is rejected even after RLS context is set."""
        workspace_a = uuid4()
        workspace_b = uuid4()
        integration = _make_integration(workspace_id=workspace_a)
        issue = _make_issue(workspace_id=workspace_b)  # Different workspace!

        session = AsyncMock()
        integration_repo = AsyncMock()
        integration_repo.get_by_id = AsyncMock(return_value=integration)
        issue_repo = AsyncMock()
        issue_repo.get_by_id_with_relations = AsyncMock(return_value=issue)

        with (
            patch(
                "pilot_space.api.v1.routers.github_links.IntegrationRepository",
                return_value=integration_repo,
            ),
            patch(
                "pilot_space.api.v1.routers.github_links.IssueRepository",
                return_value=issue_repo,
            ),
            patch("pilot_space.api.v1.routers.github_links.set_rls_context", AsyncMock()),
            pytest.raises(HTTPException) as exc_info,
        ):
            await create_branch_for_issue(
                session=session,
                current_user=MagicMock(),
                current_user_id=uuid4(),
                issue_id=uuid4(),
                integration_id=uuid4(),
                request=_make_request(),
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_404_when_issue_not_found(self) -> None:
        """Returns 404 when issue does not exist (RLS filtered it out)."""
        workspace_id = uuid4()
        integration = _make_integration(workspace_id=workspace_id)

        session = AsyncMock()
        integration_repo = AsyncMock()
        integration_repo.get_by_id = AsyncMock(return_value=integration)
        issue_repo = AsyncMock()
        issue_repo.get_by_id_with_relations = AsyncMock(return_value=None)

        with (
            patch(
                "pilot_space.api.v1.routers.github_links.IntegrationRepository",
                return_value=integration_repo,
            ),
            patch(
                "pilot_space.api.v1.routers.github_links.IssueRepository",
                return_value=issue_repo,
            ),
            patch("pilot_space.api.v1.routers.github_links.set_rls_context", AsyncMock()),
            pytest.raises(HTTPException) as exc_info,
        ):
            await create_branch_for_issue(
                session=session,
                current_user=MagicMock(),
                current_user_id=uuid4(),
                issue_id=uuid4(),
                integration_id=uuid4(),
                request=_make_request(),
            )

        assert exc_info.value.status_code == 404


class TestCreateBranchForIssueErrors:
    """Error mapping tests."""

    @pytest.mark.asyncio
    async def test_duplicate_branch_returns_409(self) -> None:
        """ValueError from service (duplicate) maps to 409 Conflict."""
        workspace_id = uuid4()
        integration = _make_integration(workspace_id=workspace_id)
        issue = _make_issue(workspace_id=workspace_id)

        session = AsyncMock()
        integration_repo = AsyncMock()
        integration_repo.get_by_id = AsyncMock(return_value=integration)
        issue_repo = AsyncMock()
        issue_repo.get_by_id_with_relations = AsyncMock(return_value=issue)
        service = AsyncMock()
        service.execute = AsyncMock(side_effect=ValueError("already linked"))

        with (
            patch(
                "pilot_space.api.v1.routers.github_links.IntegrationRepository",
                return_value=integration_repo,
            ),
            patch(
                "pilot_space.api.v1.routers.github_links.IssueRepository",
                return_value=issue_repo,
            ),
            patch("pilot_space.api.v1.routers.github_links.set_rls_context", AsyncMock()),
            patch(
                "pilot_space.api.v1.routers.github_links.IntegrationLinkRepository",
                return_value=AsyncMock(),
            ),
            patch(
                "pilot_space.api.v1.routers.github_links.ActivityRepository",
                return_value=AsyncMock(),
            ),
            patch(
                "pilot_space.api.v1.routers.github_links.CreateBranchService",
                return_value=service,
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await create_branch_for_issue(
                session=session,
                current_user=MagicMock(),
                current_user_id=uuid4(),
                issue_id=uuid4(),
                integration_id=uuid4(),
                request=_make_request(),
            )

        assert exc_info.value.status_code == 409
        assert "already linked" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_create_branch_error_returns_400_sanitized(self) -> None:
        """CreateBranchError maps to 400; GitHub detail is NOT leaked."""
        workspace_id = uuid4()
        integration = _make_integration(workspace_id=workspace_id)
        issue = _make_issue(workspace_id=workspace_id)

        session = AsyncMock()
        integration_repo = AsyncMock()
        integration_repo.get_by_id = AsyncMock(return_value=integration)
        issue_repo = AsyncMock()
        issue_repo.get_by_id_with_relations = AsyncMock(return_value=issue)
        service = AsyncMock()
        service.execute = AsyncMock(
            side_effect=CreateBranchError("Failed to create branch via GitHub API")
        )

        with (
            patch(
                "pilot_space.api.v1.routers.github_links.IntegrationRepository",
                return_value=integration_repo,
            ),
            patch(
                "pilot_space.api.v1.routers.github_links.IssueRepository",
                return_value=issue_repo,
            ),
            patch("pilot_space.api.v1.routers.github_links.set_rls_context", AsyncMock()),
            patch(
                "pilot_space.api.v1.routers.github_links.IntegrationLinkRepository",
                return_value=AsyncMock(),
            ),
            patch(
                "pilot_space.api.v1.routers.github_links.ActivityRepository",
                return_value=AsyncMock(),
            ),
            patch(
                "pilot_space.api.v1.routers.github_links.CreateBranchService",
                return_value=service,
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await create_branch_for_issue(
                session=session,
                current_user=MagicMock(),
                current_user_id=uuid4(),
                issue_id=uuid4(),
                integration_id=uuid4(),
                request=_make_request(),
            )

        assert exc_info.value.status_code == 400
        # Generic message — must NOT contain raw GitHub API details
        assert "GitHub API" not in exc_info.value.detail
        assert "Failed to create branch" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_happy_path_returns_201_link(self) -> None:
        """Successful creation returns 201 with IntegrationLinkResponse."""
        from pilot_space.api.v1.schemas.integration import IntegrationLinkResponse

        workspace_id = uuid4()
        integration = _make_integration(workspace_id=workspace_id)
        issue = _make_issue(workspace_id=workspace_id)
        link = _make_link()
        branch_result = CreateBranchResult(link=link, created=True, branch_name="feat/ps-1-test")

        session = AsyncMock()
        integration_repo = AsyncMock()
        integration_repo.get_by_id = AsyncMock(return_value=integration)
        issue_repo = AsyncMock()
        issue_repo.get_by_id_with_relations = AsyncMock(return_value=issue)
        service = AsyncMock()
        service.execute = AsyncMock(return_value=branch_result)

        with (
            patch(
                "pilot_space.api.v1.routers.github_links.IntegrationRepository",
                return_value=integration_repo,
            ),
            patch(
                "pilot_space.api.v1.routers.github_links.IssueRepository",
                return_value=issue_repo,
            ),
            patch("pilot_space.api.v1.routers.github_links.set_rls_context", AsyncMock()),
            patch(
                "pilot_space.api.v1.routers.github_links.IntegrationLinkRepository",
                return_value=AsyncMock(),
            ),
            patch(
                "pilot_space.api.v1.routers.github_links.ActivityRepository",
                return_value=AsyncMock(),
            ),
            patch(
                "pilot_space.api.v1.routers.github_links.CreateBranchService",
                return_value=service,
            ),
            patch.object(
                IntegrationLinkResponse,
                "model_validate",
                return_value=MagicMock(spec=IntegrationLinkResponse),
            ),
        ):
            result = await create_branch_for_issue(
                session=session,
                current_user=MagicMock(),
                current_user_id=uuid4(),
                issue_id=uuid4(),
                integration_id=uuid4(),
                request=_make_request(),
            )

        assert result is not None
        session.commit.assert_awaited_once()
