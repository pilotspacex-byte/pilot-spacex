"""Tests for Phase 15 Related Issues endpoints.

RELISS-01: semantic suggestions  RELISS-02: manual linking
RELISS-03: reason enrichment    RELISS-04: dismissal

These are Wave 0 test stubs. Each test is marked xfail(strict=False) so
the suite exits 0 while implementation is pending (phase 15 plans 02+).
Test bodies contain the minimal assertion shape that drives the green
implementation — they will become real assertions when the router is built.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession


pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# RELISS-01: Semantic suggestions
# ---------------------------------------------------------------------------


@pytest.mark.xfail(strict=False, reason="Wave 0 stub: RELISS-01 not yet implemented")
async def test_get_suggestions_returns_scored_issues(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """RELISS-01: GET /workspaces/{wid}/issues/{id}/related-suggestions returns list with similarity scores.

    Expected response shape:
        [
            {
                "issue_id": "<uuid>",
                "title": "...",
                "similarity_score": 0.87,
                "reason": "Semantic match (87%)"
            },
            ...
        ]
    """
    # function-local imports prevent import failure from breaking file
    from pilot_space.api.v1.routers.related_issues import router  # noqa: F401

    workspace_id = uuid4()
    issue_id = uuid4()

    response = await authenticated_client.get(
        f"/api/v1/workspaces/{workspace_id}/issues/{issue_id}/related-suggestions",
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert all("similarity_score" in item for item in data)
    pytest.fail("Not implemented")


@pytest.mark.xfail(strict=False, reason="Wave 0 stub: RELISS-01 not yet implemented")
async def test_suggestions_exclude_self(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """RELISS-01: Self-issue is absent from related-suggestions results."""
    # function-local imports prevent import failure from breaking file
    from pilot_space.api.v1.routers.related_issues import router  # noqa: F401

    workspace_id = uuid4()
    issue_id = uuid4()

    response = await authenticated_client.get(
        f"/api/v1/workspaces/{workspace_id}/issues/{issue_id}/related-suggestions",
    )

    assert response.status_code == 200
    data = response.json()
    issue_ids_in_result = [item["issue_id"] for item in data]
    assert str(issue_id) not in issue_ids_in_result
    pytest.fail("Not implemented")


# ---------------------------------------------------------------------------
# RELISS-02: Manual linking
# ---------------------------------------------------------------------------


@pytest.mark.xfail(strict=False, reason="Wave 0 stub: RELISS-02 not yet implemented")
async def test_create_related_link(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
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
    # function-local imports prevent import failure from breaking file
    from pilot_space.api.v1.routers.related_issues import router  # noqa: F401

    workspace_id = uuid4()
    source_id = uuid4()
    target_id = uuid4()

    response = await authenticated_client.post(
        f"/api/v1/workspaces/{workspace_id}/issues/{source_id}/relations",
        json={"target_issue_id": str(target_id), "link_type": "related"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["link_type"] == "related"
    assert data["source_issue_id"] == str(source_id)
    assert data["target_issue_id"] == str(target_id)
    pytest.fail("Not implemented")


@pytest.mark.xfail(strict=False, reason="Wave 0 stub: RELISS-02 not yet implemented")
async def test_delete_related_link(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """RELISS-02: DELETE /workspaces/{wid}/issues/{id}/relations/{link_id} soft-deletes."""
    # function-local imports prevent import failure from breaking file
    from pilot_space.api.v1.routers.related_issues import router  # noqa: F401

    workspace_id = uuid4()
    issue_id = uuid4()
    link_id = uuid4()

    response = await authenticated_client.delete(
        f"/api/v1/workspaces/{workspace_id}/issues/{issue_id}/relations/{link_id}",
    )

    assert response.status_code == 204
    pytest.fail("Not implemented")


@pytest.mark.xfail(strict=False, reason="Wave 0 stub: RELISS-02 not yet implemented")
async def test_create_duplicate_link_returns_409(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """RELISS-02: Bidirectional duplicate check — creating the same relation returns 409."""
    # function-local imports prevent import failure from breaking file
    from pilot_space.api.v1.routers.related_issues import router  # noqa: F401

    workspace_id = uuid4()
    source_id = uuid4()
    target_id = uuid4()

    # First call (succeeds)
    await authenticated_client.post(
        f"/api/v1/workspaces/{workspace_id}/issues/{source_id}/relations",
        json={"target_issue_id": str(target_id), "link_type": "related"},
    )

    # Duplicate call (must fail with 409)
    response = await authenticated_client.post(
        f"/api/v1/workspaces/{workspace_id}/issues/{source_id}/relations",
        json={"target_issue_id": str(target_id), "link_type": "related"},
    )

    assert response.status_code == 409
    pytest.fail("Not implemented")


# ---------------------------------------------------------------------------
# RELISS-03: Reason enrichment
# ---------------------------------------------------------------------------


@pytest.mark.xfail(strict=False, reason="Wave 0 stub: RELISS-03 not yet implemented")
async def test_suggestion_reason_enrichment(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """RELISS-03: reason field present and one of: 'same project', 'shared note', 'Semantic match (N%)'."""
    # function-local imports prevent import failure from breaking file
    from pilot_space.api.v1.routers.related_issues import router  # noqa: F401

    workspace_id = uuid4()
    issue_id = uuid4()

    response = await authenticated_client.get(
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
    pytest.fail("Not implemented")


# ---------------------------------------------------------------------------
# RELISS-04: Dismissal
# ---------------------------------------------------------------------------


@pytest.mark.xfail(strict=False, reason="Wave 0 stub: RELISS-04 not yet implemented")
async def test_dismiss_suggestion(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """RELISS-04: POST /workspaces/{wid}/issues/{id}/related-suggestions/{tid}/dismiss creates dismissal row."""
    # function-local imports prevent import failure from breaking file
    from pilot_space.infrastructure.database.repositories.issue_suggestion_dismissal_repository import (  # noqa: F401
        IssueSuggestionDismissalRepository,
    )

    workspace_id = uuid4()
    source_id = uuid4()
    target_id = uuid4()

    response = await authenticated_client.post(
        f"/api/v1/workspaces/{workspace_id}/issues/{source_id}/related-suggestions/{target_id}/dismiss",
    )

    assert response.status_code == 204
    pytest.fail("Not implemented")


@pytest.mark.xfail(strict=False, reason="Wave 0 stub: RELISS-04 not yet implemented")
async def test_dismissed_not_returned(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """RELISS-04: Dismissed target absent from subsequent GET suggestions."""
    # function-local imports prevent import failure from breaking file
    from pilot_space.infrastructure.database.repositories.issue_suggestion_dismissal_repository import (  # noqa: F401
        IssueSuggestionDismissalRepository,
    )

    workspace_id = uuid4()
    source_id = uuid4()
    target_id = uuid4()

    # Dismiss the target
    await authenticated_client.post(
        f"/api/v1/workspaces/{workspace_id}/issues/{source_id}/related-suggestions/{target_id}/dismiss",
    )

    # Subsequent GET must not include the dismissed target
    response = await authenticated_client.get(
        f"/api/v1/workspaces/{workspace_id}/issues/{source_id}/related-suggestions",
    )

    assert response.status_code == 200
    data = response.json()
    issue_ids_in_result = [item["issue_id"] for item in data]
    assert str(target_id) not in issue_ids_in_result
    pytest.fail("Not implemented")
