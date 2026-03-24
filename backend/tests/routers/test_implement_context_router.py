"""Unit tests for GET /api/v1/issues/{issue_ref}/implement-context
and PATCH /api/v1/issues/{issue_ref}/state.

Uses dependency_overrides + AsyncClient (ASGI transport) to bypass DI container,
Supabase JWT middleware, and the database. Tests HTTP status codes and RFC 7807
error body shape.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import status

from pilot_space.api.v1.schemas.implement_context import (
    ImplementContextResponse,
    IssueDetail,
    IssueStateDetail,
    LinkedNoteBlock,
    ProjectContext,
    RepositoryContext,
    WorkspaceContext,
)
from pilot_space.application.services.issue.get_implement_context_service import (
    GetImplementContextResult,
)
from pilot_space.domain.exceptions import ForbiddenError, NotFoundError, ValidationError
from pilot_space.infrastructure.database.models import IssuePriority
from pilot_space.infrastructure.database.models.state import StateGroup

pytestmark = pytest.mark.asyncio

_BASE_PATH = "/api/v1/issues"

# ============================================================================
# Helpers
# ============================================================================

_WORKSPACE_ID = uuid4()
_USER_ID = uuid4()
_ISSUE_ID = uuid4()


def _make_context_response() -> ImplementContextResponse:
    """Construct a valid ImplementContextResponse for mocking service returns."""
    issue = IssueDetail(
        id=_ISSUE_ID,
        identifier="PS-42",
        title="Implement login",
        description="As a user...",
        description_html="<p>As a user...</p>",
        acceptance_criteria=["User can log in"],
        status="started",
        priority=IssuePriority.MEDIUM,
        labels=[],
        state=IssueStateDetail(
            id=uuid4(),
            name="In Progress",
            color="#3B82F6",
            group=StateGroup.STARTED,
        ),
        project_id=uuid4(),
        assignee_id=_USER_ID,
    )
    return ImplementContextResponse(
        issue=issue,
        linked_notes=[LinkedNoteBlock(note_title="Sprint notes", relevant_blocks=["block one"])],
        repository=RepositoryContext(
            clone_url="https://github.com/acme/backend",
            default_branch="main",
            provider="github",
        ),
        workspace=WorkspaceContext(slug="acme", name="Acme Corp"),
        project=ProjectContext(name="Pilot Space", tech_stack_summary="FastAPI + React"),
        suggested_branch="feat/ps-42-implement-login",
    )


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_service() -> AsyncMock:
    """Mock GetImplementContextService."""
    return AsyncMock()


@pytest.fixture
def mock_issue_repo() -> MagicMock:
    """Mock IssueRepository (no DB calls needed in unit tests)."""
    repo = MagicMock()
    # get_by_identifier is not called when issue_ref is a valid UUID
    repo.get_by_identifier = AsyncMock(return_value=None)
    return repo


@pytest.fixture
async def implement_client(
    mock_service: AsyncMock,
    mock_issue_repo: MagicMock,
) -> AsyncGenerator[Any, None]:
    """HTTP test client with all required dependencies overridden.

    Overrides:
    - GetImplementContextService (via _get_implement_context_service)
    - IssueRepository (via _get_issue_repository — for identifier resolution)
    - get_current_user_id (JWT auth bypass)
    - get_current_workspace_id (header bypass)
    - get_session (DB session bypass — set_rls_context requires it)
    """
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.api.v1.dependencies_pilot import (
        _get_cli_requester_context,
        _get_implement_context_service,
    )
    from pilot_space.api.v1.repository_deps import _get_issue_repository
    from pilot_space.dependencies.auth import get_current_user_id, get_session
    from pilot_space.dependencies.workspace import get_current_workspace_id
    from pilot_space.main import app

    mock_session = AsyncMock(spec=AsyncSession)

    app.dependency_overrides[_get_implement_context_service] = lambda: mock_service
    app.dependency_overrides[_get_issue_repository] = lambda: mock_issue_repo
    app.dependency_overrides[_get_cli_requester_context] = lambda: (_USER_ID, _WORKSPACE_ID)
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    app.dependency_overrides[get_current_workspace_id] = lambda: _WORKSPACE_ID
    app.dependency_overrides[get_session] = lambda: mock_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.pop(_get_implement_context_service, None)
    app.dependency_overrides.pop(_get_issue_repository, None)
    app.dependency_overrides.pop(_get_cli_requester_context, None)
    app.dependency_overrides.pop(get_current_user_id, None)
    app.dependency_overrides.pop(get_current_workspace_id, None)
    app.dependency_overrides.pop(get_session, None)


# ============================================================================
# Happy path
# ============================================================================


class TestImplementContextRouterHappyPath:
    async def test_200_with_implement_context_response(
        self,
        implement_client: Any,
        mock_service: AsyncMock,
    ) -> None:
        """GET returns 200 with full ImplementContextResponse schema (camelCase keys)."""
        ctx = _make_context_response()
        mock_service.execute.return_value = GetImplementContextResult(context=ctx)

        response = await implement_client.get(
            f"{_BASE_PATH}/{_ISSUE_ID}/implement-context",
            headers={"Authorization": "Bearer test-jwt"},
        )

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        # BaseSchema uses alias_generator=to_camel, so keys are camelCase
        assert body["issue"]["identifier"] == "PS-42"
        assert body["repository"]["cloneUrl"] == "https://github.com/acme/backend"
        assert body["workspace"]["slug"] == "acme"
        assert body["suggestedBranch"] == "feat/ps-42-implement-login"
        assert body["linkedNotes"][0]["noteTitle"] == "Sprint notes"

    async def test_service_receives_correct_payload(
        self,
        implement_client: Any,
        mock_service: AsyncMock,
    ) -> None:
        """Router passes issue_id, workspace_id, and requester_id to service."""
        from pilot_space.application.services.issue.get_implement_context_service import (
            GetImplementContextPayload,
        )

        ctx = _make_context_response()
        mock_service.execute.return_value = GetImplementContextResult(context=ctx)

        await implement_client.get(
            f"{_BASE_PATH}/{_ISSUE_ID}/implement-context",
            headers={"Authorization": "Bearer test-jwt"},
        )

        mock_service.execute.assert_awaited_once()
        payload: GetImplementContextPayload = mock_service.execute.call_args[0][0]
        assert payload.issue_id == _ISSUE_ID
        assert payload.workspace_id == _WORKSPACE_ID
        assert payload.requester_id == _USER_ID

    async def test_empty_linked_notes_returns_empty_list(
        self,
        implement_client: Any,
        mock_service: AsyncMock,
    ) -> None:
        """Response with no linked notes serializes as empty list, not null."""
        ctx = _make_context_response()
        ctx.linked_notes = []
        mock_service.execute.return_value = GetImplementContextResult(context=ctx)

        response = await implement_client.get(
            f"{_BASE_PATH}/{_ISSUE_ID}/implement-context",
            headers={"Authorization": "Bearer test-jwt"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["linkedNotes"] == []


# ============================================================================
# Error mappings
# ============================================================================


class TestImplementContextRouterErrors:
    async def test_permission_error_returns_403_rfc7807(
        self,
        implement_client: Any,
        mock_service: AsyncMock,
    ) -> None:
        """ForbiddenError from service maps to HTTP 403.

        The global ``app_error_handler`` reads ``http_status`` and ``message``
        from the domain exception and produces an RFC 7807 envelope.
        """
        mock_service.execute.side_effect = ForbiddenError(
            "Only the issue assignee or workspace admins/owners can access implement context"
        )

        response = await implement_client.get(
            f"{_BASE_PATH}/{_ISSUE_ID}/implement-context",
            headers={"Authorization": "Bearer test-jwt"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        body = response.json()
        assert body["status"] == 403
        assert "assignee or workspace admins" in body["detail"]

    async def test_no_github_integration_returns_422_rfc7807(
        self,
        implement_client: Any,
        mock_service: AsyncMock,
    ) -> None:
        """ValidationError('no_github_integration') maps to HTTP 422.

        The ``app_error_handler`` reads ``http_status`` (422) and ``message``
        from the domain exception and produces an RFC 7807 envelope.
        """
        mock_service.execute.side_effect = ValidationError("no_github_integration")

        response = await implement_client.get(
            f"{_BASE_PATH}/{_ISSUE_ID}/implement-context",
            headers={"Authorization": "Bearer test-jwt"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        body = response.json()
        assert body["status"] == 422
        assert "no_github_integration" in body["detail"]

    async def test_issue_not_found_returns_404(
        self,
        implement_client: Any,
        mock_service: AsyncMock,
    ) -> None:
        """NotFoundError('Issue not found: ...') maps to HTTP 404."""
        missing_id = uuid4()
        mock_service.execute.side_effect = NotFoundError(f"Issue not found: {missing_id}")

        response = await implement_client.get(
            f"{_BASE_PATH}/{_ISSUE_ID}/implement-context",
            headers={"Authorization": "Bearer test-jwt"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_workspace_not_found_returns_404(
        self,
        implement_client: Any,
        mock_service: AsyncMock,
    ) -> None:
        """NotFoundError('Workspace not found: ...') maps to HTTP 404."""
        mock_service.execute.side_effect = NotFoundError(f"Workspace not found: {_WORKSPACE_ID}")

        response = await implement_client.get(
            f"{_BASE_PATH}/{_ISSUE_ID}/implement-context",
            headers={"Authorization": "Bearer test-jwt"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_generic_not_found_error_returns_404(
        self,
        implement_client: Any,
        mock_service: AsyncMock,
    ) -> None:
        """Any NotFoundError maps to 404."""
        mock_service.execute.side_effect = NotFoundError("some other error")

        response = await implement_client.get(
            f"{_BASE_PATH}/{_ISSUE_ID}/implement-context",
            headers={"Authorization": "Bearer test-jwt"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_invalid_identifier_format_returns_404(
        self,
        implement_client: Any,
    ) -> None:
        """Path parameter that is neither a UUID nor a valid PS-42 identifier returns 404."""
        response = await implement_client.get(
            f"{_BASE_PATH}/not-a-uuid/implement-context",
            headers={"Authorization": "Bearer test-jwt"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_identifier_format_ps42_triggers_repo_lookup(
        self,
        implement_client: Any,
        mock_issue_repo: MagicMock,
        mock_service: AsyncMock,
    ) -> None:
        """PS-42 format triggers get_by_identifier lookup; returns 404 when not found."""
        mock_issue_repo.get_by_identifier.return_value = None

        response = await implement_client.get(
            f"{_BASE_PATH}/PS-42/implement-context",
            headers={"Authorization": "Bearer test-jwt"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        mock_issue_repo.get_by_identifier.assert_awaited_once_with(
            workspace_id=_WORKSPACE_ID,
            project_identifier="PS",
            sequence_id=42,
        )
        mock_service.execute.assert_not_awaited()

    async def test_403_detail_does_not_contain_requester_id(
        self,
        implement_client: Any,
        mock_service: AsyncMock,
    ) -> None:
        """403 error body must not leak requester_id (information exposure check).

        The ``app_error_handler`` builds the RFC 7807 response from the domain
        exception's ``message``; the requester's UUID must not appear.
        """
        mock_service.execute.side_effect = ForbiddenError("access denied")

        response = await implement_client.get(
            f"{_BASE_PATH}/{_ISSUE_ID}/implement-context",
            headers={"Authorization": "Bearer test-jwt"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        # The requester's UUID must not appear verbatim in the error body
        assert str(_USER_ID) not in response.text

    async def test_422_detail_does_not_contain_workspace_id(
        self,
        implement_client: Any,
        mock_service: AsyncMock,
    ) -> None:
        """422 no_github_integration error must not leak workspace_id.

        The ``app_error_handler`` builds the response from the domain
        exception's ``message``; the workspace_id must not appear.
        """
        mock_service.execute.side_effect = ValidationError("no_github_integration")

        response = await implement_client.get(
            f"{_BASE_PATH}/{_ISSUE_ID}/implement-context",
            headers={"Authorization": "Bearer test-jwt"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert str(_WORKSPACE_ID) not in response.text


# ============================================================================
# Edge: service called exactly once per request
# ============================================================================


class TestImplementContextRouterCallCount:
    async def test_service_called_exactly_once(
        self,
        implement_client: Any,
        mock_service: AsyncMock,
    ) -> None:
        """Service is invoked exactly once per request — no extra calls."""
        ctx = _make_context_response()
        mock_service.execute.return_value = GetImplementContextResult(context=ctx)

        await implement_client.get(
            f"{_BASE_PATH}/{_ISSUE_ID}/implement-context",
            headers={"Authorization": "Bearer test-jwt"},
        )

        assert mock_service.execute.await_count == 1

    async def test_service_not_called_for_invalid_identifier(
        self,
        implement_client: Any,
        mock_service: AsyncMock,
    ) -> None:
        """Service is never called when path param is not a UUID or valid identifier."""
        await implement_client.get(
            f"{_BASE_PATH}/definitely-not-a-uuid/implement-context",
            headers={"Authorization": "Bearer test-jwt"},
        )

        mock_service.execute.assert_not_awaited()
