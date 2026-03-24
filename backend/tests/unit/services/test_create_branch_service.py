"""Unit tests for CreateBranchService.

All external dependencies mocked with AsyncMock / MagicMock.
Uses pytest-asyncio (asyncio_mode="auto" via pyproject.toml).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from pilot_space.application.services.integration.create_branch_service import (
    CreateBranchError,
    CreateBranchPayload,
    CreateBranchService,
)
from pilot_space.domain.exceptions import ConflictError
from pilot_space.infrastructure.database.models import (
    Integration,
    IntegrationLink,
    Issue,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_payload(
    branch_name: str = "feat/ps-1-fix-login",
    base_branch: str = "main",
    repository: str = "acme/api",
) -> CreateBranchPayload:
    return CreateBranchPayload(
        workspace_id=uuid4(),
        issue_id=uuid4(),
        integration_id=uuid4(),
        repository=repository,
        branch_name=branch_name,
        base_branch=base_branch,
        actor_id=uuid4(),
    )


def _make_integration(is_active: bool = True) -> MagicMock:
    integration = MagicMock(spec=Integration)
    integration.is_active = is_active
    integration.access_token = "encrypted-token"
    return integration


def _make_issue() -> MagicMock:
    issue = MagicMock(spec=Issue)
    issue.workspace_id = uuid4()
    return issue


def _make_link(branch_name: str = "feat/ps-1-fix-login") -> MagicMock:
    link = MagicMock(spec=IntegrationLink)
    link.external_id = branch_name
    link.integration_id = uuid4()
    return link


def _make_repos(
    integration: MagicMock | None = None,
    issue: MagicMock | None = None,
    existing_links: list | None = None,
    link_result: tuple | None = None,
) -> tuple[MagicMock, MagicMock, MagicMock, MagicMock]:
    integration_repo = AsyncMock()
    integration_repo.get_by_id = AsyncMock(return_value=integration)

    issue_repo = AsyncMock()
    issue_repo.get_by_id_with_relations = AsyncMock(return_value=issue)

    link_repo = AsyncMock()
    link_repo.get_by_issue = AsyncMock(return_value=existing_links or [])
    created_link = _make_link()
    link_repo.create_if_not_exists = AsyncMock(return_value=link_result or (created_link, True))

    activity_repo = AsyncMock()
    activity_repo.create = AsyncMock(side_effect=lambda a: a)

    return integration_repo, issue_repo, link_repo, activity_repo


def _make_service(
    integration_repo: MagicMock,
    issue_repo: MagicMock,
    link_repo: MagicMock,
    activity_repo: MagicMock,
) -> CreateBranchService:
    session = AsyncMock()
    return CreateBranchService(
        session=session,
        integration_repo=integration_repo,
        integration_link_repo=link_repo,
        issue_repo=issue_repo,
        activity_repo=activity_repo,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCreateBranchServiceSuccess:
    """Happy path tests."""

    @pytest.mark.asyncio
    async def test_creates_branch_and_returns_result(self) -> None:
        """Service creates branch via GitHub and returns CreateBranchResult."""
        payload = _make_payload()
        integration = _make_integration()
        issue = _make_issue()
        created_link = _make_link(payload.branch_name)
        integration_repo, issue_repo, link_repo, activity_repo = _make_repos(
            integration=integration,
            issue=issue,
            link_result=(created_link, True),
        )

        service = _make_service(integration_repo, issue_repo, link_repo, activity_repo)

        with (
            patch(
                "pilot_space.application.services.integration.create_branch_service.decrypt_api_key",
                return_value="plain-token",
            ),
            patch(
                "pilot_space.application.services.integration.create_branch_service.httpx.AsyncClient",
            ) as mock_client_cls,
        ):
            mock_http = AsyncMock()
            ref_resp = MagicMock()
            ref_resp.raise_for_status = MagicMock()
            ref_resp.json = MagicMock(return_value={"object": {"sha": "abc123sha"}})
            mock_http.get = AsyncMock(return_value=ref_resp)
            branch_resp = MagicMock()
            branch_resp.raise_for_status = MagicMock()
            mock_http.post = AsyncMock(return_value=branch_resp)
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await service.execute(payload)

        assert result.created is True
        assert result.branch_name == payload.branch_name
        activity_repo.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_idempotent_link_does_not_duplicate_activity(self) -> None:
        """When link already exists (created=False), no activity is recorded."""
        payload = _make_payload()
        integration = _make_integration()
        issue = _make_issue()
        existing_link = _make_link(payload.branch_name)
        integration_repo, issue_repo, link_repo, activity_repo = _make_repos(
            integration=integration,
            issue=issue,
            link_result=(existing_link, False),
        )

        service = _make_service(integration_repo, issue_repo, link_repo, activity_repo)

        with (
            patch(
                "pilot_space.application.services.integration.create_branch_service.decrypt_api_key",
                return_value="plain-token",
            ),
            patch(
                "pilot_space.application.services.integration.create_branch_service.httpx.AsyncClient",
            ) as mock_client_cls,
        ):
            mock_http = AsyncMock()
            ref_resp = MagicMock()
            ref_resp.raise_for_status = MagicMock()
            ref_resp.json = MagicMock(return_value={"object": {"sha": "abc123sha"}})
            mock_http.get = AsyncMock(return_value=ref_resp)
            branch_resp = MagicMock()
            branch_resp.raise_for_status = MagicMock()
            mock_http.post = AsyncMock(return_value=branch_resp)
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await service.execute(payload)

        assert result.created is False
        activity_repo.create.assert_not_awaited()


class TestCreateBranchServiceValidation:
    """Integration/issue validation error tests."""

    @pytest.mark.asyncio
    async def test_raises_when_integration_not_found(self) -> None:
        """CreateBranchError raised when integration_id does not exist."""
        payload = _make_payload()
        integration_repo, issue_repo, link_repo, activity_repo = _make_repos(integration=None)
        service = _make_service(integration_repo, issue_repo, link_repo, activity_repo)

        with pytest.raises(CreateBranchError, match="Integration not found"):
            await service.execute(payload)

    @pytest.mark.asyncio
    async def test_raises_when_integration_not_active(self) -> None:
        """CreateBranchError raised when integration is inactive."""
        payload = _make_payload()
        integration = _make_integration(is_active=False)
        integration_repo, issue_repo, link_repo, activity_repo = _make_repos(
            integration=integration
        )
        service = _make_service(integration_repo, issue_repo, link_repo, activity_repo)

        with pytest.raises(CreateBranchError, match="Integration is not active"):
            await service.execute(payload)

    @pytest.mark.asyncio
    async def test_raises_when_issue_not_found(self) -> None:
        """CreateBranchError raised when issue_id does not exist."""
        payload = _make_payload()
        integration = _make_integration()
        integration_repo, issue_repo, link_repo, activity_repo = _make_repos(
            integration=integration, issue=None
        )
        service = _make_service(integration_repo, issue_repo, link_repo, activity_repo)

        with pytest.raises(CreateBranchError, match="Issue not found"):
            await service.execute(payload)

    @pytest.mark.asyncio
    async def test_raises_value_error_when_branch_already_linked(self) -> None:
        """ValueError raised when branch link already exists for this issue+integration."""
        payload = _make_payload(branch_name="feat/ps-1-fix-login")
        integration = _make_integration()
        issue = _make_issue()

        # Existing link with same branch name and integration_id
        existing = MagicMock(spec=IntegrationLink)
        existing.external_id = payload.branch_name
        existing.integration_id = payload.integration_id

        integration_repo, issue_repo, link_repo, activity_repo = _make_repos(
            integration=integration,
            issue=issue,
            existing_links=[existing],
        )
        # Override to return integration_id correctly
        integration_repo.get_by_id = AsyncMock(return_value=integration)

        service = _make_service(integration_repo, issue_repo, link_repo, activity_repo)

        with pytest.raises(ConflictError, match="already linked"):
            await service.execute(payload)


class TestCreateBranchServiceGitHubErrors:
    """GitHub API error handling tests."""

    @pytest.mark.asyncio
    async def test_raises_create_branch_error_on_github_api_failure(self) -> None:
        """CreateBranchError raised when GitHub API throws."""
        payload = _make_payload()
        integration = _make_integration()
        issue = _make_issue()
        integration_repo, issue_repo, link_repo, activity_repo = _make_repos(
            integration=integration, issue=issue
        )
        service = _make_service(integration_repo, issue_repo, link_repo, activity_repo)

        with (
            patch(
                "pilot_space.application.services.integration.create_branch_service.decrypt_api_key",
                return_value="plain-token",
            ),
            patch(
                "pilot_space.application.services.integration.create_branch_service.httpx.AsyncClient",
            ) as mock_client_cls,
        ):
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(side_effect=Exception("GitHub 422 Unprocessable"))
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(CreateBranchError, match="Failed to create branch via GitHub API"):
                await service.execute(payload)

        link_repo.create_if_not_exists.assert_not_awaited()
        activity_repo.create.assert_not_awaited()
