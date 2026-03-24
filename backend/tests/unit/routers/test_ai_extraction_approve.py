"""Tests for _create_extracted_issues in ai_extraction router.

Verifies project validation, exception handling, and NoteIssueLink resilience.
"""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from pilot_space.api.v1.routers.ai_extraction import (
    CreateExtractedIssuesRequest,
    ExtractedIssueInput,
    _create_extracted_issues,
)
from pilot_space.domain.exceptions import (
    NotFoundError,
    ValidationError as DomainValidationError,
)

TEST_USER_ID = UUID("77a6813e-0aa3-400c-8d4e-540b6ed2187a")
TEST_WORKSPACE_ID = uuid4()
TEST_PROJECT_ID = uuid4()
TEST_NOTE_ID = uuid4()

# Patch paths — lazy imports inside _create_extracted_issues resolve from source modules
_SVC_PATH = "pilot_space.application.services.issue.CreateIssueService"
_ISSUE_REPO = "pilot_space.infrastructure.database.repositories.issue_repository.IssueRepository"
_ACTIVITY_REPO = (
    "pilot_space.infrastructure.database.repositories.activity_repository.ActivityRepository"
)
_LABEL_REPO = "pilot_space.infrastructure.database.repositories.label_repository.LabelRepository"
_LINK_REPO = "pilot_space.infrastructure.database.repositories.note_issue_link_repository.NoteIssueLinkRepository"


@dataclass
class MockIssueResult:
    """Mock result from CreateIssueService.execute."""

    issue: MagicMock


def _mock_issue(issue_id: UUID | None = None, sequence_id: int = 1) -> MagicMock:
    """Create a mock issue."""
    issue = MagicMock()
    issue.id = issue_id or uuid4()
    issue.sequence_id = sequence_id
    issue.name = "Test Issue"
    return issue


def _mock_session(project_identifier: str | None = "PROJ") -> AsyncMock:
    """Create a mock session that returns a project identifier."""
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = project_identifier
    session.execute.return_value = mock_result
    return session


pytestmark = pytest.mark.asyncio


async def test_empty_issues_raises_validation_error() -> None:
    """Should raise ValidationError when no issues provided."""
    body = CreateExtractedIssuesRequest(issues=[], project_id=str(TEST_PROJECT_ID))

    with pytest.raises(DomainValidationError) as exc_info:
        await _create_extracted_issues(
            workspace_id=TEST_WORKSPACE_ID,
            note_id=None,
            body=body,
            current_user_id=TEST_USER_ID,
            session=AsyncMock(),
        )

    assert exc_info.value.http_status == 422
    assert "No issues" in exc_info.value.message


async def test_missing_project_id_raises_validation_error() -> None:
    """Should raise ValidationError when project_id is missing."""
    body = CreateExtractedIssuesRequest(
        issues=[ExtractedIssueInput(title="Test")],
        project_id=None,
    )

    with pytest.raises(DomainValidationError) as exc_info:
        await _create_extracted_issues(
            workspace_id=TEST_WORKSPACE_ID,
            note_id=None,
            body=body,
            current_user_id=TEST_USER_ID,
            session=AsyncMock(),
        )

    assert exc_info.value.http_status == 422
    assert "project_id" in exc_info.value.message


async def test_invalid_project_id_raises_validation_error() -> None:
    """Should raise ValidationError when project_id is not a valid UUID."""
    body = CreateExtractedIssuesRequest(
        issues=[ExtractedIssueInput(title="Test")],
        project_id="not-a-uuid",
    )

    with pytest.raises(DomainValidationError) as exc_info:
        await _create_extracted_issues(
            workspace_id=TEST_WORKSPACE_ID,
            note_id=None,
            body=body,
            current_user_id=TEST_USER_ID,
            session=AsyncMock(),
        )

    assert exc_info.value.http_status == 422
    assert "Invalid project_id" in exc_info.value.message


async def test_project_not_found_raises_not_found() -> None:
    """Should raise NotFoundError when project identifier is not found."""
    session = _mock_session(project_identifier=None)
    body = CreateExtractedIssuesRequest(
        issues=[ExtractedIssueInput(title="Test")],
        project_id=str(TEST_PROJECT_ID),
    )

    with pytest.raises(NotFoundError) as exc_info:
        await _create_extracted_issues(
            workspace_id=TEST_WORKSPACE_ID,
            note_id=None,
            body=body,
            current_user_id=TEST_USER_ID,
            session=session,
        )

    assert exc_info.value.http_status == 404
    assert "Project not found" in exc_info.value.message


async def test_creates_issues_successfully() -> None:
    """Should create issues and return enriched response."""
    session = _mock_session(project_identifier="PILOT")
    mock_issue_obj = _mock_issue(sequence_id=42)

    body = CreateExtractedIssuesRequest(
        issues=[ExtractedIssueInput(title="Fix bug", priority=1)],
        project_id=str(TEST_PROJECT_ID),
    )

    with (
        patch(_SVC_PATH) as MockService,
        patch(_ISSUE_REPO),
        patch(_ACTIVITY_REPO),
        patch(_LABEL_REPO),
    ):
        mock_svc = MagicMock()
        mock_svc.execute = AsyncMock(return_value=MockIssueResult(issue=mock_issue_obj))
        MockService.return_value = mock_svc

        result = await _create_extracted_issues(
            workspace_id=TEST_WORKSPACE_ID,
            note_id=None,
            body=body,
            current_user_id=TEST_USER_ID,
            session=session,
        )

    assert result.created_count == 1
    assert result.created_issues[0].identifier == "PILOT-42"
    assert result.source_note_id is None


async def test_note_issue_link_failure_does_not_crash() -> None:
    """NoteIssueLink DB error should be caught; issue is still created."""
    session = _mock_session(project_identifier="PILOT")
    mock_issue_obj = _mock_issue(sequence_id=1)

    body = CreateExtractedIssuesRequest(
        issues=[ExtractedIssueInput(title="Fix bug", priority=1)],
        project_id=str(TEST_PROJECT_ID),
    )

    with (
        patch(_SVC_PATH) as MockService,
        patch(_ISSUE_REPO),
        patch(_ACTIVITY_REPO),
        patch(_LABEL_REPO),
        patch(_LINK_REPO) as MockLinkRepo,
    ):
        mock_svc = MagicMock()
        mock_svc.execute = AsyncMock(return_value=MockIssueResult(issue=mock_issue_obj))
        MockService.return_value = mock_svc

        mock_link_repo = AsyncMock()
        mock_link_repo.find_existing.side_effect = RuntimeError("DB connection lost")
        MockLinkRepo.return_value = mock_link_repo

        result = await _create_extracted_issues(
            workspace_id=TEST_WORKSPACE_ID,
            note_id=str(TEST_NOTE_ID),
            body=body,
            current_user_id=TEST_USER_ID,
            session=session,
        )

    # Issue was still created despite link failure
    assert result.created_count == 1
    assert result.created_issues[0].identifier == "PILOT-1"


async def test_issue_creation_failure_continues() -> None:
    """Single issue creation failure should not abort remaining issues."""
    session = _mock_session(project_identifier="PILOT")
    mock_issue_2 = _mock_issue(sequence_id=2)

    body = CreateExtractedIssuesRequest(
        issues=[
            ExtractedIssueInput(title="Fail issue", priority=1),
            ExtractedIssueInput(title="Success issue", priority=2),
        ],
        project_id=str(TEST_PROJECT_ID),
    )

    with (
        patch(_SVC_PATH) as MockService,
        patch(_ISSUE_REPO),
        patch(_ACTIVITY_REPO),
        patch(_LABEL_REPO),
    ):
        mock_svc = MagicMock()
        mock_svc.execute = AsyncMock(
            side_effect=[
                RuntimeError("DB error"),
                MockIssueResult(issue=mock_issue_2),
            ]
        )
        MockService.return_value = mock_svc

        result = await _create_extracted_issues(
            workspace_id=TEST_WORKSPACE_ID,
            note_id=None,
            body=body,
            current_user_id=TEST_USER_ID,
            session=session,
        )

    # Only the second issue succeeded
    assert result.created_count == 1
    assert result.created_issues[0].identifier == "PILOT-2"
