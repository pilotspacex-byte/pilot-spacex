"""Tests for GET /{workspace_id}/issues/{issue_id}/relations endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from pilot_space.api.v1.routers.workspace_issues import list_issue_relations
from pilot_space.api.v1.schemas.issue import IssueLinkSchema
from pilot_space.domain.exceptions import NotFoundError
from pilot_space.infrastructure.database.models.issue_link import IssueLinkType

TEST_USER_ID = UUID("77a6813e-0aa3-400c-8d4e-540b6ed2187a")

_RESOLVE_WORKSPACE = "pilot_space.api.v1.routers.workspace_issues._resolve_workspace"
_SET_RLS_CONTEXT = "pilot_space.api.v1.routers.workspace_issues.set_rls_context"


def _make_state() -> MagicMock:
    state = MagicMock()
    state.id = uuid4()
    state.name = "Todo"
    state.color = "#60a5fa"
    state.group = "unstarted"
    return state


def _make_issue(workspace_id: UUID) -> MagicMock:
    """Create a mock Issue belonging to the given workspace."""
    issue = MagicMock()
    issue.id = uuid4()
    issue.workspace_id = workspace_id
    issue.identifier = "PS-1"
    issue.name = "Test Issue"
    issue.priority = "medium"
    issue.state = _make_state()
    issue.assignee = None
    return issue


def _make_workspace(workspace_id: UUID | None = None) -> MagicMock:
    ws = MagicMock()
    ws.id = workspace_id or uuid4()
    return ws


def _make_link(
    source_issue: MagicMock,
    target_issue: MagicMock,
    link_type: IssueLinkType = IssueLinkType.BLOCKS,
) -> MagicMock:
    """Create a mock IssueLink between two issues."""
    link = MagicMock()
    link.id = uuid4()
    link.link_type = link_type
    link.source_issue_id = source_issue.id
    link.target_issue_id = target_issue.id
    link.source_issue = source_issue
    link.target_issue = target_issue
    return link


def _make_session_for_issue(workspace_id: UUID | None) -> AsyncMock:
    """Create a mock session whose execute() returns the given workspace_id scalar."""
    mock_session = AsyncMock()
    mock_execute_result = MagicMock()
    mock_execute_result.scalar_one_or_none.return_value = workspace_id
    mock_session.execute.return_value = mock_execute_result
    return mock_session


async def _call_endpoint(
    *,
    workspace_id: str = "test-workspace",
    issue_id: UUID | None = None,
    links: list[MagicMock],
    workspace: MagicMock | None = None,
    issue_exists: bool = True,
    issue_workspace_id: UUID | None = None,
) -> list[IssueLinkSchema]:
    """Call list_issue_relations with mocked infrastructure (success path only)."""
    if issue_id is None:
        issue_id = uuid4()
    if workspace is None:
        workspace = _make_workspace()

    effective_ws_id = issue_workspace_id if issue_workspace_id is not None else workspace.id
    mock_session = _make_session_for_issue(effective_ws_id if issue_exists else None)
    mock_link_repo = AsyncMock()
    mock_workspace_repo = AsyncMock()

    mock_link_repo.find_all_for_issue.return_value = links

    with (
        patch(_RESOLVE_WORKSPACE, return_value=workspace) as mock_resolve,
        patch(_SET_RLS_CONTEXT, new_callable=AsyncMock) as mock_rls,
    ):
        result = await list_issue_relations(
            session=mock_session,
            workspace_id=workspace_id,
            issue_id=issue_id,
            current_user_id=TEST_USER_ID,
            workspace_repo=mock_workspace_repo,
            link_repo=mock_link_repo,
        )

    mock_resolve.assert_awaited_once_with(workspace_id, mock_workspace_repo)
    mock_rls.assert_awaited_once_with(mock_session, TEST_USER_ID, workspace.id)
    mock_link_repo.find_all_for_issue.assert_awaited_once_with(issue_id, workspace.id)

    return result


@pytest.mark.asyncio
async def test_returns_empty_list_when_no_relations() -> None:
    """Should return an empty list when no links exist for the issue."""
    result = await _call_endpoint(links=[])

    assert result == []


@pytest.mark.asyncio
async def test_returns_link_schema_for_each_relation() -> None:
    """Should return one IssueLinkSchema per link returned by the repository."""
    workspace = _make_workspace()
    issue_id = uuid4()
    source = _make_issue(workspace.id)
    source.id = issue_id
    target = _make_issue(workspace.id)
    link = _make_link(source, target, IssueLinkType.BLOCKS)

    result = await _call_endpoint(links=[link], workspace=workspace, issue_id=issue_id)

    assert len(result) == 1
    assert isinstance(result[0], IssueLinkSchema)
    assert result[0].id == link.id
    assert result[0].link_type == IssueLinkType.BLOCKS.value


@pytest.mark.asyncio
async def test_direction_is_outbound_when_issue_is_source() -> None:
    """Direction should be 'outbound' when the queried issue is the source."""
    workspace = _make_workspace()
    issue_id = uuid4()
    source = _make_issue(workspace.id)
    source.id = issue_id
    target = _make_issue(workspace.id)
    link = _make_link(source, target, IssueLinkType.BLOCKS)

    result = await _call_endpoint(links=[link], workspace=workspace, issue_id=issue_id)

    assert result[0].direction == "outbound"


@pytest.mark.asyncio
async def test_raises_404_when_issue_not_found() -> None:
    """Should return 404 when issue not found (deleted or nonexistent).

    Verifies that set_rls_context IS called before the 404 is raised —
    the RLS context must be established before any DB access.
    """
    workspace = _make_workspace()
    issue_id = uuid4()
    mock_session = _make_session_for_issue(None)  # scalar_one_or_none returns None
    mock_link_repo = AsyncMock()
    mock_workspace_repo = AsyncMock()

    with (
        patch(_RESOLVE_WORKSPACE, return_value=workspace),
        patch(_SET_RLS_CONTEXT, new_callable=AsyncMock) as mock_rls,
    ):
        with pytest.raises(NotFoundError) as exc_info:
            await list_issue_relations(
                session=mock_session,
                workspace_id="test-workspace",
                issue_id=issue_id,
                current_user_id=TEST_USER_ID,
                workspace_repo=mock_workspace_repo,
                link_repo=mock_link_repo,
            )
        # RLS context must be set before the 404 check
        mock_rls.assert_awaited_once_with(mock_session, TEST_USER_ID, workspace.id)

    assert exc_info.value.http_status == 404
    assert "not found" in exc_info.value.message.lower()


@pytest.mark.asyncio
async def test_raises_404_when_issue_belongs_to_different_workspace() -> None:
    """Should return 404 when the issue exists but belongs to a different workspace.

    Verifies that set_rls_context IS called before the cross-workspace check.
    """
    workspace = _make_workspace()
    other_workspace_id = uuid4()  # different from workspace.id
    issue_id = uuid4()
    mock_session = _make_session_for_issue(other_workspace_id)
    mock_link_repo = AsyncMock()
    mock_workspace_repo = AsyncMock()

    with (
        patch(_RESOLVE_WORKSPACE, return_value=workspace),
        patch(_SET_RLS_CONTEXT, new_callable=AsyncMock) as mock_rls,
    ):
        with pytest.raises(NotFoundError) as exc_info:
            await list_issue_relations(
                session=mock_session,
                workspace_id="test-workspace",
                issue_id=issue_id,
                current_user_id=TEST_USER_ID,
                workspace_repo=mock_workspace_repo,
                link_repo=mock_link_repo,
            )
        # RLS context must be set before the cross-workspace check
        mock_rls.assert_awaited_once_with(mock_session, TEST_USER_ID, workspace.id)

    assert exc_info.value.http_status == 404
