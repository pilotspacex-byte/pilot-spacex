"""Tests for GET /{workspace_id}/issues/{issue_id}/notes endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from pilot_space.api.v1.routers.workspace_issues import list_issue_note_links
from pilot_space.api.v1.schemas.issue import NoteIssueLinkBriefSchema

TEST_USER_ID = UUID("77a6813e-0aa3-400c-8d4e-540b6ed2187a")

_RESOLVE_WORKSPACE = "pilot_space.api.v1.routers.workspace_issues._resolve_workspace"
_SET_RLS_CONTEXT = "pilot_space.api.v1.routers.workspace_issues.set_rls_context"


def _make_link(
    is_deleted: bool = False,
    note_title: str = "My Note",
    note: MagicMock | None = ...,  # type: ignore[assignment]
) -> MagicMock:
    """Create a mock NoteIssueLink."""
    link = MagicMock()
    link.id = uuid4()
    link.note_id = uuid4()
    link.issue_id = uuid4()
    link.link_type = MagicMock()
    link.link_type.value = "EXTRACTED"
    link.is_deleted = is_deleted
    if note is ...:
        link.note = MagicMock()
        link.note.title = note_title
    else:
        link.note = note
    return link


def _make_workspace(workspace_id: UUID | None = None) -> MagicMock:
    """Create a mock Workspace."""
    ws = MagicMock()
    ws.id = workspace_id or uuid4()
    return ws


def _make_issue(workspace_id: UUID) -> MagicMock:
    """Create a mock Issue belonging to the given workspace."""
    issue = MagicMock()
    issue.workspace_id = workspace_id
    return issue


async def _call_endpoint(
    *,
    workspace_id: str = "test-workspace",
    issue_id: UUID | None = None,
    links: list[MagicMock],
    workspace: MagicMock | None = None,
    issue_exists: bool = True,
) -> list[NoteIssueLinkBriefSchema]:
    """Call list_issue_note_links with mocked infrastructure."""
    if issue_id is None:
        issue_id = uuid4()
    if workspace is None:
        workspace = _make_workspace()

    mock_session = AsyncMock()
    mock_link_repo = AsyncMock()
    mock_workspace_repo = AsyncMock()
    mock_issue_repo = AsyncMock()

    mock_link_repo.get_by_issue.return_value = links

    if issue_exists:
        mock_issue_repo.get_by_id_with_relations.return_value = _make_issue(workspace.id)
    else:
        mock_issue_repo.get_by_id_with_relations.return_value = None

    with (
        patch(_RESOLVE_WORKSPACE, return_value=workspace) as mock_resolve,
        patch(_SET_RLS_CONTEXT, new_callable=AsyncMock) as mock_rls,
    ):
        result = await list_issue_note_links(
            session=mock_session,
            workspace_id=workspace_id,
            issue_id=issue_id,
            current_user_id=TEST_USER_ID,
            link_repo=mock_link_repo,
            workspace_repo=mock_workspace_repo,
            issue_repo=mock_issue_repo,
        )

    mock_resolve.assert_awaited_once_with(workspace_id, mock_workspace_repo)
    mock_rls.assert_awaited_once_with(mock_session, TEST_USER_ID, workspace.id)
    mock_link_repo.get_by_issue.assert_awaited_once_with(issue_id, workspace.id)

    return result


@pytest.mark.asyncio
async def test_returns_empty_list_when_no_links() -> None:
    """Should return an empty list when no links exist for the issue."""
    result = await _call_endpoint(links=[])

    assert result == []


@pytest.mark.asyncio
async def test_returns_brief_schema_for_each_link() -> None:
    """Should return one NoteIssueLinkBriefSchema per link returned by the repository."""
    link1 = _make_link(note_title="First Note")
    link2 = _make_link(note_title="Second Note")

    result = await _call_endpoint(links=[link1, link2])

    assert len(result) == 2

    ids = {item.id for item in result}
    assert link1.id in ids
    assert link2.id in ids

    for item in result:
        assert isinstance(item, NoteIssueLinkBriefSchema)
        assert item.link_type == "EXTRACTED"
        assert isinstance(item.note_id, UUID)


@pytest.mark.asyncio
async def test_trusts_repository_is_deleted_filtering() -> None:
    """Endpoint trusts get_by_issue to exclude deleted links at SQL level.

    The repository already applies `is_deleted == False` in the SQL query.
    The endpoint passes through whatever the repository returns without re-filtering.
    """
    # Simulate repository correctly returning only active links (is_deleted already filtered)
    active1 = _make_link(note_title="Active 1")
    active2 = _make_link(note_title="Active 2")

    result = await _call_endpoint(links=[active1, active2])

    assert len(result) == 2
    result_ids = {item.id for item in result}
    assert active1.id in result_ids
    assert active2.id in result_ids


@pytest.mark.asyncio
async def test_note_title_empty_string_when_note_is_none() -> None:
    """Should set note_title to empty string when link.note is None."""
    link = _make_link(note=None)

    result = await _call_endpoint(links=[link])

    assert len(result) == 1
    assert result[0].note_title == ""
    assert result[0].id == link.id


@pytest.mark.asyncio
async def test_correct_note_title_from_link_note() -> None:
    """Should populate note_title from link.note.title."""
    link = _make_link(note_title="Architecture Decision Record")

    result = await _call_endpoint(links=[link])

    assert len(result) == 1
    assert result[0].note_title == "Architecture Decision Record"


@pytest.mark.asyncio
async def test_resolves_workspace_by_slug() -> None:
    """Should call _resolve_workspace with the raw workspace_id string."""
    workspace = _make_workspace()
    mock_session = AsyncMock()
    mock_link_repo = AsyncMock()
    mock_workspace_repo = AsyncMock()
    mock_issue_repo = AsyncMock()
    mock_link_repo.get_by_issue.return_value = []
    mock_issue_repo.get_by_id_with_relations.return_value = _make_issue(workspace.id)
    issue_id = uuid4()

    with (
        patch(_RESOLVE_WORKSPACE, return_value=workspace) as mock_resolve,
        patch(_SET_RLS_CONTEXT, new_callable=AsyncMock),
    ):
        await list_issue_note_links(
            session=mock_session,
            workspace_id="my-slug",
            issue_id=issue_id,
            current_user_id=TEST_USER_ID,
            link_repo=mock_link_repo,
            workspace_repo=mock_workspace_repo,
            issue_repo=mock_issue_repo,
        )

    mock_resolve.assert_awaited_once_with("my-slug", mock_workspace_repo)


@pytest.mark.asyncio
async def test_raises_404_when_issue_not_found() -> None:
    """Should return 404 when issue_repo returns None (issue doesn't exist or is deleted)."""
    with pytest.raises(HTTPException) as exc_info:
        await _call_endpoint(links=[], issue_exists=False)

    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_raises_404_when_issue_belongs_to_different_workspace() -> None:
    """Should return 404 when the issue exists but belongs to a different workspace."""
    workspace = _make_workspace()
    other_workspace_id = uuid4()  # different from workspace.id

    mock_session = AsyncMock()
    mock_link_repo = AsyncMock()
    mock_workspace_repo = AsyncMock()
    mock_issue_repo = AsyncMock()
    mock_link_repo.get_by_issue.return_value = []
    # Issue belongs to a different workspace
    cross_ws_issue = _make_issue(other_workspace_id)
    mock_issue_repo.get_by_id_with_relations.return_value = cross_ws_issue

    with (
        patch(_RESOLVE_WORKSPACE, return_value=workspace),
        patch(_SET_RLS_CONTEXT, new_callable=AsyncMock),
        pytest.raises(HTTPException) as exc_info,
    ):
        await list_issue_note_links(
            session=mock_session,
            workspace_id="test-workspace",
            issue_id=uuid4(),
            current_user_id=TEST_USER_ID,
            link_repo=mock_link_repo,
            workspace_repo=mock_workspace_repo,
            issue_repo=mock_issue_repo,
        )

    assert exc_info.value.status_code == 404
