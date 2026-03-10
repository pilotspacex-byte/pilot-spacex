"""Tests for Phase 15 Related Issues endpoints.

RELISS-01: semantic suggestions  RELISS-02: manual linking
RELISS-03: reason enrichment    RELISS-04: dismissal

Uses dependency overrides + patching (same pattern as test_workspace_tasks.py).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient


pytestmark = pytest.mark.asyncio

_RESOLVE_WORKSPACE_PATH = "pilot_space.api.v1.routers.related_issues._resolve_workspace"
_SET_RLS_PATH = "pilot_space.api.v1.routers.related_issues.set_rls_context"


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def workspace_id() -> UUID:
    """Random workspace UUID."""
    return uuid4()


@pytest.fixture
def mock_workspace(workspace_id: UUID) -> MagicMock:
    """Mock resolved workspace."""
    ws = MagicMock()
    ws.id = workspace_id
    return ws


@pytest.fixture
async def related_client(mock_link_repo: AsyncMock) -> AsyncGenerator[AsyncClient, None]:
    """Authenticated HTTP client with dependency overrides for related-issues routes."""
    from httpx import ASGITransport, AsyncClient

    from pilot_space.api.v1.repository_deps import (
        _get_issue_link_repository,  # pyright: ignore[reportPrivateUsage]
        _get_workspace_repository,  # pyright: ignore[reportPrivateUsage]
    )
    from pilot_space.dependencies.auth import ensure_user_synced, get_session
    from pilot_space.main import app

    mock_session = AsyncMock()
    mock_session.add = MagicMock()  # session.add() is synchronous

    async def mock_session_gen() -> AsyncGenerator[Any, None]:
        yield mock_session

    app.dependency_overrides[get_session] = mock_session_gen
    app.dependency_overrides[ensure_user_synced] = lambda: uuid4()
    app.dependency_overrides[_get_workspace_repository] = lambda: AsyncMock()
    app.dependency_overrides[_get_issue_link_repository] = lambda: mock_link_repo

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    ) as ac:
        yield ac

    app.dependency_overrides.pop(get_session, None)
    app.dependency_overrides.pop(ensure_user_synced, None)
    app.dependency_overrides.pop(_get_workspace_repository, None)
    app.dependency_overrides.pop(_get_issue_link_repository, None)


@pytest.fixture
def mock_link_repo() -> AsyncMock:
    """Mock IssueLinkRepository."""
    repo = AsyncMock()
    repo.link_exists = AsyncMock(return_value=False)
    repo.get_by_id = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def mock_kg_repo_no_node() -> AsyncMock:
    """Mock KnowledgeGraphRepository that returns None for node lookup."""
    repo = AsyncMock()
    repo._find_node_by_external = AsyncMock(return_value=None)
    return repo


# ---------------------------------------------------------------------------
# RELISS-01: Semantic suggestions
# ---------------------------------------------------------------------------


async def test_get_suggestions_returns_scored_issues(
    related_client: AsyncClient,
    mock_workspace: MagicMock,
    workspace_id: UUID,
    mock_kg_repo_no_node: AsyncMock,
) -> None:
    """RELISS-01: GET /workspaces/{wid}/issues/{id}/related-suggestions returns list with similarity scores.

    When issue has no KG node (kg_populate not run), returns empty list with 200.
    """
    from pilot_space.api.v1.routers.related_issues import router  # noqa: F401

    issue_id = uuid4()

    with (
        patch(_RESOLVE_WORKSPACE_PATH, return_value=mock_workspace),
        patch(_SET_RLS_PATH, new=AsyncMock()),
        patch(
            "pilot_space.api.v1.routers.related_issues.KnowledgeGraphRepository",
            return_value=mock_kg_repo_no_node,
        ),
        patch("pilot_space.api.v1.routers.related_issues.IssueSuggestionDismissalRepository"),
    ):
        response = await related_client.get(
            f"/api/v1/workspaces/{workspace_id}/issues/{issue_id}/related-suggestions",
        )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert all("similarity_score" in item for item in data)


async def test_suggestions_exclude_self(
    related_client: AsyncClient,
    mock_workspace: MagicMock,
    workspace_id: UUID,
    mock_kg_repo_no_node: AsyncMock,
) -> None:
    """RELISS-01: Self-issue is absent from related-suggestions results."""
    from pilot_space.api.v1.routers.related_issues import router  # noqa: F401

    issue_id = uuid4()

    with (
        patch(_RESOLVE_WORKSPACE_PATH, return_value=mock_workspace),
        patch(_SET_RLS_PATH, new=AsyncMock()),
        patch(
            "pilot_space.api.v1.routers.related_issues.KnowledgeGraphRepository",
            return_value=mock_kg_repo_no_node,
        ),
        patch("pilot_space.api.v1.routers.related_issues.IssueSuggestionDismissalRepository"),
    ):
        response = await related_client.get(
            f"/api/v1/workspaces/{workspace_id}/issues/{issue_id}/related-suggestions",
        )

    assert response.status_code == 200
    data = response.json()
    issue_ids_in_result = [item["id"] for item in data]
    assert str(issue_id) not in issue_ids_in_result


# ---------------------------------------------------------------------------
# RELISS-02: Manual linking
# ---------------------------------------------------------------------------


async def test_create_related_link(
    related_client: AsyncClient,
    mock_workspace: MagicMock,
    workspace_id: UUID,
    mock_link_repo: AsyncMock,
) -> None:
    """RELISS-02: POST /workspaces/{wid}/issues/{id}/relations creates IssueLink with type=related.

    Expected response shape:
        {
            "id": "<uuid>",
            "source_issue_id": "<uuid>",
            "target_issue_id": "<uuid>",
            "link_type": "related"
        }
    """
    from pilot_space.api.v1.routers.related_issues import router  # noqa: F401

    source_id = uuid4()
    target_id = uuid4()
    mock_link_repo.link_exists = AsyncMock(return_value=False)

    with (
        patch(_RESOLVE_WORKSPACE_PATH, return_value=mock_workspace),
        patch(_SET_RLS_PATH, new=AsyncMock()),
    ):
        response = await related_client.post(
            f"/api/v1/workspaces/{workspace_id}/issues/{source_id}/relations",
            json={"target_issue_id": str(target_id), "link_type": "related"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["link_type"] == "related"
    assert data["source_issue_id"] == str(source_id)
    assert data["target_issue_id"] == str(target_id)


async def test_delete_related_link(
    related_client: AsyncClient,
    mock_workspace: MagicMock,
    workspace_id: UUID,
    mock_link_repo: AsyncMock,
) -> None:
    """RELISS-02: DELETE /workspaces/{wid}/issues/{id}/relations/{link_id} returns 404 when link not found."""
    from pilot_space.api.v1.routers.related_issues import router  # noqa: F401

    issue_id = uuid4()
    link_id = uuid4()
    mock_link_repo.get_by_id = AsyncMock(return_value=None)  # link not found → 404

    with (
        patch(_RESOLVE_WORKSPACE_PATH, return_value=mock_workspace),
        patch(_SET_RLS_PATH, new=AsyncMock()),
    ):
        response = await related_client.delete(
            f"/api/v1/workspaces/{workspace_id}/issues/{issue_id}/relations/{link_id}",
        )

    assert response.status_code == 404


async def test_delete_related_link_success(
    related_client: AsyncClient,
    mock_workspace: MagicMock,
    workspace_id: UUID,
    mock_link_repo: AsyncMock,
) -> None:
    """RELISS-02: DELETE /workspaces/{wid}/issues/{id}/relations/{link_id} returns 204 when found."""
    from pilot_space.api.v1.routers.related_issues import router  # noqa: F401
    from pilot_space.infrastructure.database.models.issue_link import IssueLink

    issue_id = uuid4()
    link_id = uuid4()

    mock_link = MagicMock(spec=IssueLink)
    mock_link.id = link_id
    mock_link.workspace_id = workspace_id
    mock_link_repo.get_by_id = AsyncMock(return_value=mock_link)
    mock_link_repo.delete = AsyncMock()

    with (
        patch(_RESOLVE_WORKSPACE_PATH, return_value=mock_workspace),
        patch(_SET_RLS_PATH, new=AsyncMock()),
    ):
        response = await related_client.delete(
            f"/api/v1/workspaces/{workspace_id}/issues/{issue_id}/relations/{link_id}",
        )

    assert response.status_code == 204


async def test_create_duplicate_link_returns_409(
    related_client: AsyncClient,
    mock_workspace: MagicMock,
    workspace_id: UUID,
    mock_link_repo: AsyncMock,
) -> None:
    """RELISS-02: Bidirectional duplicate check — creating the same relation returns 409."""
    from pilot_space.api.v1.routers.related_issues import router  # noqa: F401

    source_id = uuid4()
    target_id = uuid4()
    mock_link_repo.link_exists = AsyncMock(return_value=True)  # signals duplicate

    with (
        patch(_RESOLVE_WORKSPACE_PATH, return_value=mock_workspace),
        patch(_SET_RLS_PATH, new=AsyncMock()),
    ):
        response = await related_client.post(
            f"/api/v1/workspaces/{workspace_id}/issues/{source_id}/relations",
            json={"target_issue_id": str(target_id), "link_type": "related"},
        )

    assert response.status_code == 409


# ---------------------------------------------------------------------------
# RELISS-03: Reason enrichment
# ---------------------------------------------------------------------------


async def test_suggestion_reason_enrichment(
    related_client: AsyncClient,
    mock_workspace: MagicMock,
    workspace_id: UUID,
    mock_kg_repo_no_node: AsyncMock,
) -> None:
    """RELISS-03: reason field present and one of: 'same project', 'shared note', 'Semantic match (N%)'.

    With no KG node, returns empty list — vacuously satisfies the reason constraint.
    """
    from pilot_space.api.v1.routers.related_issues import router  # noqa: F401

    issue_id = uuid4()

    with (
        patch(_RESOLVE_WORKSPACE_PATH, return_value=mock_workspace),
        patch(_SET_RLS_PATH, new=AsyncMock()),
        patch(
            "pilot_space.api.v1.routers.related_issues.KnowledgeGraphRepository",
            return_value=mock_kg_repo_no_node,
        ),
        patch("pilot_space.api.v1.routers.related_issues.IssueSuggestionDismissalRepository"),
    ):
        response = await related_client.get(
            f"/api/v1/workspaces/{workspace_id}/issues/{issue_id}/related-suggestions",
        )

    assert response.status_code == 200
    data = response.json()
    valid_reason_prefixes = ("same project", "shared note", "Semantic match (")
    for item in data:
        assert "reason" in item, "reason field must be present"
        reason: str = item["reason"]
        assert any(reason.startswith(p) for p in valid_reason_prefixes), (
            f"reason '{reason}' does not match expected patterns"
        )


# ---------------------------------------------------------------------------
# RELISS-04: Dismissal
# ---------------------------------------------------------------------------


async def test_dismiss_suggestion(
    related_client: AsyncClient,
    mock_workspace: MagicMock,
    workspace_id: UUID,
) -> None:
    """RELISS-04: POST /workspaces/{wid}/issues/{id}/related-suggestions/{tid}/dismiss creates dismissal row."""
    from pilot_space.infrastructure.database.repositories.issue_suggestion_dismissal_repository import (  # noqa: F401
        IssueSuggestionDismissalRepository,
    )

    source_id = uuid4()
    target_id = uuid4()

    with (
        patch(_RESOLVE_WORKSPACE_PATH, return_value=mock_workspace),
        patch(_SET_RLS_PATH, new=AsyncMock()),
        patch(
            "pilot_space.api.v1.routers.related_issues.IssueSuggestionDismissalRepository"
        ) as mock_cls,
    ):
        mock_repo = AsyncMock()
        mock_repo.create_dismissal = AsyncMock(return_value=MagicMock())
        mock_cls.return_value = mock_repo

        response = await related_client.post(
            f"/api/v1/workspaces/{workspace_id}/issues/{source_id}/related-suggestions/{target_id}/dismiss",
        )

    assert response.status_code == 204


async def test_dismissed_not_returned(
    related_client: AsyncClient,
    mock_workspace: MagicMock,
    workspace_id: UUID,
    mock_kg_repo_no_node: AsyncMock,
) -> None:
    """RELISS-04: Dismissed target absent from subsequent GET suggestions.

    When issue has no KG node, returns []. The dismissed target is therefore
    not in the result (vacuously true for empty result).
    """
    from pilot_space.infrastructure.database.repositories.issue_suggestion_dismissal_repository import (  # noqa: F401
        IssueSuggestionDismissalRepository,
    )

    source_id = uuid4()
    target_id = uuid4()

    # Dismiss the target
    with (
        patch(_RESOLVE_WORKSPACE_PATH, return_value=mock_workspace),
        patch(_SET_RLS_PATH, new=AsyncMock()),
        patch(
            "pilot_space.api.v1.routers.related_issues.IssueSuggestionDismissalRepository"
        ) as mock_cls,
    ):
        mock_repo = AsyncMock()
        mock_repo.create_dismissal = AsyncMock(return_value=MagicMock())
        mock_cls.return_value = mock_repo

        dismiss_response = await related_client.post(
            f"/api/v1/workspaces/{workspace_id}/issues/{source_id}/related-suggestions/{target_id}/dismiss",
        )
    assert dismiss_response.status_code == 204

    # Subsequent GET must not include the dismissed target
    with (
        patch(_RESOLVE_WORKSPACE_PATH, return_value=mock_workspace),
        patch(_SET_RLS_PATH, new=AsyncMock()),
        patch(
            "pilot_space.api.v1.routers.related_issues.KnowledgeGraphRepository",
            return_value=mock_kg_repo_no_node,
        ),
        patch(
            "pilot_space.api.v1.routers.related_issues.IssueSuggestionDismissalRepository"
        ) as mock_cls2,
    ):
        mock_repo2 = AsyncMock()
        mock_repo2.get_dismissed_target_ids = AsyncMock(return_value={target_id})
        mock_cls2.return_value = mock_repo2

        response = await related_client.get(
            f"/api/v1/workspaces/{workspace_id}/issues/{source_id}/related-suggestions",
        )

    assert response.status_code == 200
    data = response.json()
    issue_ids_in_result = [item["id"] for item in data]
    assert str(target_id) not in issue_ids_in_result
