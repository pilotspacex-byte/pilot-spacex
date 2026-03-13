"""Tests for create-extracted-issues endpoint.

Verifies that the endpoint creates issues from AI extraction results,
validates input, and handles edge cases.
"""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from pilot_space.api.v1.routers.workspace_notes_ai import (
    CreateExtractedIssuesRequest,
    ExtractedIssueInput,
    create_extracted_issues,
)

TEST_USER_ID = UUID("77a6813e-0aa3-400c-8d4e-540b6ed2187a")
TEST_WORKSPACE_ID = uuid4()
TEST_NOTE_ID = uuid4()
TEST_PROJECT_ID = uuid4()


def _make_note(
    workspace_id: UUID = TEST_WORKSPACE_ID,
    project_id: UUID | None = TEST_PROJECT_ID,
) -> MagicMock:
    """Create a mock note."""
    note = MagicMock()
    note.id = TEST_NOTE_ID
    note.workspace_id = workspace_id
    note.project_id = project_id
    return note


def _make_workspace(workspace_id: UUID = TEST_WORKSPACE_ID) -> MagicMock:
    """Create a mock workspace."""
    ws = MagicMock()
    ws.id = workspace_id
    ws.slug = "test-workspace"
    return ws


@dataclass
class MockIssueResult:
    """Mock result from CreateIssueService.execute."""

    issue: MagicMock


# Patch paths for lazy imports inside the endpoint function
_SVC_PATH = "pilot_space.application.services.issue.create_issue_service.CreateIssueService"
_ISSUE_REPO_PATH = (
    "pilot_space.infrastructure.database.repositories.issue_repository.IssueRepository"
)
_ACTIVITY_REPO_PATH = (
    "pilot_space.infrastructure.database.repositories.activity_repository.ActivityRepository"
)
_LABEL_REPO_PATH = (
    "pilot_space.infrastructure.database.repositories.label_repository.LabelRepository"
)
_PROJECT_REPO_PATH = (
    "pilot_space.infrastructure.database.repositories.project_repository.ProjectRepository"
)


@pytest.mark.asyncio
async def test_create_extracted_issues_success() -> None:
    """Should create issues and return created IDs."""
    mock_session = AsyncMock()
    mock_note_repo = AsyncMock()
    mock_workspace_repo = AsyncMock()

    workspace = _make_workspace()
    note = _make_note()
    mock_workspace_repo.get_by_id.return_value = workspace
    mock_note_repo.get_by_id.return_value = note

    issue_id_1 = uuid4()
    issue_id_2 = uuid4()

    mock_issue_1 = MagicMock()
    mock_issue_1.id = issue_id_1
    mock_issue_2 = MagicMock()
    mock_issue_2.id = issue_id_2

    body = CreateExtractedIssuesRequest(
        issues=[
            ExtractedIssueInput(title="Fix login", priority="high", type="bug"),
            ExtractedIssueInput(title="Add feature", priority="low", type="feature"),
        ]
    )

    with (
        patch(_SVC_PATH) as MockService,
        patch(_ISSUE_REPO_PATH),
        patch(_ACTIVITY_REPO_PATH),
        patch(_LABEL_REPO_PATH),
    ):
        mock_service = MagicMock()
        mock_service.execute = AsyncMock(
            side_effect=[
                MockIssueResult(issue=mock_issue_1),
                MockIssueResult(issue=mock_issue_2),
            ]
        )
        MockService.return_value = mock_service

        result = await create_extracted_issues(
            workspace_id=str(TEST_WORKSPACE_ID),
            note_id=TEST_NOTE_ID,
            body=body,
            current_user_id=TEST_USER_ID,
            session=mock_session,
            note_repo=mock_note_repo,
            create_issue_service=mock_service,
            workspace_repo=mock_workspace_repo,
        )

    assert result.count == 2
    assert len(result.created_issue_ids) == 2
    assert str(issue_id_1) in result.created_issue_ids
    assert str(issue_id_2) in result.created_issue_ids
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_extracted_issues_note_not_found() -> None:
    """Should raise 404 when note doesn't exist."""
    mock_session = AsyncMock()
    mock_note_repo = AsyncMock()
    mock_workspace_repo = AsyncMock()

    workspace = _make_workspace()
    mock_workspace_repo.get_by_id.return_value = workspace
    mock_note_repo.get_by_id.return_value = None

    body = CreateExtractedIssuesRequest(issues=[ExtractedIssueInput(title="Test issue")])

    with pytest.raises(HTTPException) as exc_info:
        await create_extracted_issues(
            workspace_id=str(TEST_WORKSPACE_ID),
            note_id=TEST_NOTE_ID,
            body=body,
            current_user_id=TEST_USER_ID,
            session=mock_session,
            note_repo=mock_note_repo,
            create_issue_service=AsyncMock(),
            workspace_repo=mock_workspace_repo,
        )

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_create_extracted_issues_wrong_workspace() -> None:
    """Should raise 404 when note belongs to different workspace."""
    mock_session = AsyncMock()
    mock_note_repo = AsyncMock()
    mock_workspace_repo = AsyncMock()

    workspace = _make_workspace()
    note = _make_note(workspace_id=uuid4())  # Different workspace
    mock_workspace_repo.get_by_id.return_value = workspace
    mock_note_repo.get_by_id.return_value = note

    body = CreateExtractedIssuesRequest(issues=[ExtractedIssueInput(title="Test issue")])

    with pytest.raises(HTTPException) as exc_info:
        await create_extracted_issues(
            workspace_id=str(TEST_WORKSPACE_ID),
            note_id=TEST_NOTE_ID,
            body=body,
            current_user_id=TEST_USER_ID,
            session=mock_session,
            note_repo=mock_note_repo,
            create_issue_service=AsyncMock(),
            workspace_repo=mock_workspace_repo,
        )

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_create_extracted_issues_fallback_project() -> None:
    """Should use first workspace project when note has no project_id."""
    mock_session = AsyncMock()
    mock_note_repo = AsyncMock()
    mock_workspace_repo = AsyncMock()

    workspace = _make_workspace()
    note = _make_note(project_id=None)  # No project on note
    mock_workspace_repo.get_by_id.return_value = workspace
    mock_note_repo.get_by_id.return_value = note

    mock_project = MagicMock()
    mock_project.id = TEST_PROJECT_ID

    issue_id = uuid4()
    mock_issue = MagicMock()
    mock_issue.id = issue_id

    body = CreateExtractedIssuesRequest(issues=[ExtractedIssueInput(title="Test issue")])

    with (
        patch(_PROJECT_REPO_PATH) as MockProjectRepo,
        patch(_SVC_PATH) as MockService,
        patch(_ISSUE_REPO_PATH),
        patch(_ACTIVITY_REPO_PATH),
        patch(_LABEL_REPO_PATH),
    ):
        mock_project_repo = AsyncMock()
        mock_project_repo.get_workspace_projects.return_value = [mock_project]
        MockProjectRepo.return_value = mock_project_repo

        mock_service = MagicMock()
        mock_service.execute = AsyncMock(return_value=MockIssueResult(issue=mock_issue))
        MockService.return_value = mock_service

        result = await create_extracted_issues(
            workspace_id=str(TEST_WORKSPACE_ID),
            note_id=TEST_NOTE_ID,
            body=body,
            current_user_id=TEST_USER_ID,
            session=mock_session,
            note_repo=mock_note_repo,
            create_issue_service=mock_service,
            workspace_repo=mock_workspace_repo,
        )

    assert result.count == 1
    MockProjectRepo.assert_called_once_with(session=mock_session)


@pytest.mark.asyncio
async def test_create_extracted_issues_no_project_available() -> None:
    """Should raise 400 when note has no project and workspace has no projects."""
    mock_session = AsyncMock()
    mock_note_repo = AsyncMock()
    mock_workspace_repo = AsyncMock()

    workspace = _make_workspace()
    note = _make_note(project_id=None)
    mock_workspace_repo.get_by_id.return_value = workspace
    mock_note_repo.get_by_id.return_value = note

    body = CreateExtractedIssuesRequest(issues=[ExtractedIssueInput(title="Test issue")])

    with patch(_PROJECT_REPO_PATH) as MockProjectRepo:
        mock_project_repo = AsyncMock()
        mock_project_repo.get_workspace_projects.return_value = []
        MockProjectRepo.return_value = mock_project_repo

        with pytest.raises(HTTPException) as exc_info:
            await create_extracted_issues(
                workspace_id=str(TEST_WORKSPACE_ID),
                note_id=TEST_NOTE_ID,
                body=body,
                current_user_id=TEST_USER_ID,
                session=mock_session,
                note_repo=mock_note_repo,
                create_issue_service=AsyncMock(),
                workspace_repo=mock_workspace_repo,
            )

    assert exc_info.value.status_code == 400
