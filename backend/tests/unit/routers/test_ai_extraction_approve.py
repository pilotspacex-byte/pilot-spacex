"""Tests for CreateExtractedIssuesService.execute().

Verifies project validation, exception handling, and NoteIssueLink resilience.
"""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from pilot_space.application.services.ai_extraction import (
    CreateExtractedIssuesPayload,
    CreateExtractedIssuesService,
    ExtractedIssueInput,
)
from pilot_space.domain.exceptions import (
    NotFoundError,
    ValidationError as DomainValidationError,
)

TEST_USER_ID = UUID("77a6813e-0aa3-400c-8d4e-540b6ed2187a")
TEST_WORKSPACE_ID = uuid4()
TEST_PROJECT_ID = uuid4()
TEST_NOTE_ID = uuid4()

# Patch paths — lazy imports inside CreateExtractedIssuesService.execute resolve from source modules
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


def _mock_project_repo(identifier: str | None = "PROJ") -> AsyncMock:
    """Create a mock project repository that returns the given identifier."""
    repo = AsyncMock()
    repo.get_identifier_by_id = AsyncMock(return_value=identifier)
    return repo


def _make_payload(
    issues: list[ExtractedIssueInput],
    project_id: str | None = None,
    note_id: str | None = None,
) -> CreateExtractedIssuesPayload:
    """Build a CreateExtractedIssuesPayload for tests."""
    return CreateExtractedIssuesPayload(
        workspace_id=TEST_WORKSPACE_ID,
        note_id=note_id,
        issues=issues,
        project_id=project_id,
        user_id=TEST_USER_ID,
    )


pytestmark = pytest.mark.asyncio


def _make_session() -> AsyncMock:
    """Create a mock AsyncSession with begin_nested support."""
    session = AsyncMock()
    # begin_nested() must return an async context manager (not a coroutine)
    nested_cm = MagicMock()
    nested_cm.__aenter__ = AsyncMock(return_value=None)
    nested_cm.__aexit__ = AsyncMock(return_value=False)
    session.begin_nested = MagicMock(return_value=nested_cm)
    return session


def _make_service(
    session: AsyncMock | None = None,
    project_repository: AsyncMock | MagicMock | None = None,
) -> CreateExtractedIssuesService:
    """Build a CreateExtractedIssuesService with mock dependencies."""
    return CreateExtractedIssuesService(
        session=session or _make_session(),
        project_repository=project_repository or MagicMock(),
        issue_repository=MagicMock(),
        activity_repository=MagicMock(),
        label_repository=MagicMock(),
        note_issue_link_repository=MagicMock(),
    )


async def test_empty_issues_raises_validation_error() -> None:
    """Should raise ValidationError when no issues provided."""
    payload = _make_payload(issues=[], project_id=str(TEST_PROJECT_ID))
    svc = _make_service()

    with pytest.raises(DomainValidationError) as exc_info:
        await svc.execute(payload)

    assert exc_info.value.http_status == 422
    assert "No issues" in exc_info.value.message


async def test_missing_project_id_raises_validation_error() -> None:
    """Should raise ValidationError when project_id is missing."""
    payload = _make_payload(
        issues=[ExtractedIssueInput(title="Test")],
        project_id=None,
    )
    svc = _make_service()

    with pytest.raises(DomainValidationError) as exc_info:
        await svc.execute(payload)

    assert exc_info.value.http_status == 422
    assert "project_id" in exc_info.value.message


async def test_invalid_project_id_raises_validation_error() -> None:
    """Should raise ValidationError when project_id is not a valid UUID."""
    payload = _make_payload(
        issues=[ExtractedIssueInput(title="Test")],
        project_id="not-a-uuid",
    )
    svc = _make_service()

    with pytest.raises(DomainValidationError) as exc_info:
        await svc.execute(payload)

    assert exc_info.value.http_status == 422
    assert "Invalid project_id" in exc_info.value.message


async def test_project_not_found_raises_not_found() -> None:
    """Should raise NotFoundError when project identifier is not found."""
    project_repo = _mock_project_repo(identifier=None)
    payload = _make_payload(
        issues=[ExtractedIssueInput(title="Test")],
        project_id=str(TEST_PROJECT_ID),
    )
    svc = _make_service(project_repository=project_repo)

    with pytest.raises(NotFoundError) as exc_info:
        await svc.execute(payload)

    assert exc_info.value.http_status == 404
    assert "Project not found" in exc_info.value.message


async def test_creates_issues_successfully() -> None:
    """Should create issues and return enriched response."""
    project_repo = _mock_project_repo(identifier="PILOT")
    mock_issue_obj = _mock_issue(sequence_id=42)

    payload = _make_payload(
        issues=[ExtractedIssueInput(title="Fix bug", priority=1)],
        project_id=str(TEST_PROJECT_ID),
    )
    svc = _make_service(project_repository=project_repo)

    with patch(_SVC_PATH) as MockService:
        mock_svc = MagicMock()
        mock_svc.execute = AsyncMock(return_value=MockIssueResult(issue=mock_issue_obj))
        MockService.return_value = mock_svc

        result = await svc.execute(payload)

    assert result.created_count == 1
    assert result.created_issues[0].identifier == "PILOT-42"
    assert result.source_note_id is None


async def test_note_issue_link_failure_does_not_crash() -> None:
    """NoteIssueLink DB error should be caught; issue is still created."""
    project_repo = _mock_project_repo(identifier="PILOT")
    mock_issue_obj = _mock_issue(sequence_id=1)

    # Build a mock link_repo that raises on find_existing
    mock_link_repo = AsyncMock()
    mock_link_repo.find_existing.side_effect = RuntimeError("DB connection lost")

    payload = _make_payload(
        issues=[ExtractedIssueInput(title="Fix bug", priority=1)],
        project_id=str(TEST_PROJECT_ID),
        note_id=str(TEST_NOTE_ID),
    )
    svc = _make_service(project_repository=project_repo)
    svc._note_issue_link_repo = mock_link_repo  # type: ignore[attr-defined]

    with patch(_SVC_PATH) as MockService:
        mock_svc = MagicMock()
        mock_svc.execute = AsyncMock(return_value=MockIssueResult(issue=mock_issue_obj))
        MockService.return_value = mock_svc

        result = await svc.execute(payload)

    # Issue was still created despite link failure
    assert result.created_count == 1
    assert result.created_issues[0].identifier == "PILOT-1"


async def test_issue_creation_failure_continues() -> None:
    """Single issue creation failure should not abort remaining issues."""
    project_repo = _mock_project_repo(identifier="PILOT")
    mock_issue_2 = _mock_issue(sequence_id=2)

    payload = _make_payload(
        issues=[
            ExtractedIssueInput(title="Fail issue", priority=1),
            ExtractedIssueInput(title="Success issue", priority=2),
        ],
        project_id=str(TEST_PROJECT_ID),
    )
    svc = _make_service(project_repository=project_repo)

    with patch(_SVC_PATH) as MockService:
        mock_svc = MagicMock()
        mock_svc.execute = AsyncMock(
            side_effect=[
                RuntimeError("DB error"),
                MockIssueResult(issue=mock_issue_2),
            ]
        )
        MockService.return_value = mock_svc

        result = await svc.execute(payload)

    # Only the second issue succeeded
    assert result.created_count == 1
    assert result.created_issues[0].identifier == "PILOT-2"
