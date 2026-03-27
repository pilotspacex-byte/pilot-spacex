"""Tests for create_extracted_issues NoteIssueLink creation.

Verifies that CreateExtractedIssuesService creates NoteIssueLink records
with link_type=EXTRACTED for each created issue, with correct note_id,
issue_id, workspace_id, and optional block_id.

After CQRS migration, the NoteIssueLink creation logic moved from the
workspace_notes_ai router into CreateExtractedIssuesService. Tests now
target the service directly.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

pytestmark = pytest.mark.asyncio

WORKSPACE_ID = uuid4()
NOTE_ID = uuid4()
ISSUE_ID_1 = uuid4()
ISSUE_ID_2 = uuid4()
PROJECT_ID = uuid4()


def _make_issue_orm(issue_id=None, sequence_id: int = 1) -> MagicMock:
    """Build a mock Issue ORM object."""
    issue = MagicMock()
    issue.id = issue_id or uuid4()
    issue.sequence_id = sequence_id
    issue.name = "Test Issue"
    return issue


def _make_issue_result(issue_id=None, sequence_id: int = 1) -> MagicMock:
    """Build a mock CreateIssueResult."""
    result = MagicMock()
    result.issue = _make_issue_orm(issue_id, sequence_id)
    return result


def _make_service(
    session: AsyncMock,
    issue_results: list,
    link_repo: AsyncMock | None = None,
):
    """Build a CreateExtractedIssuesService with mocked dependencies."""
    from pilot_space.application.services.ai_extraction import CreateExtractedIssuesService

    project_repo = AsyncMock()
    project_repo.get_identifier_by_id.return_value = "PS"

    issue_repo = AsyncMock()
    activity_repo = AsyncMock()
    label_repo = AsyncMock()

    if link_repo is None:
        link_repo = AsyncMock()
        link_repo.find_existing.return_value = None

    # Patch CreateIssueService.execute to return our mock results
    service = CreateExtractedIssuesService(
        session=session,
        project_repository=project_repo,
        issue_repository=issue_repo,
        activity_repository=activity_repo,
        label_repository=label_repo,
        note_issue_link_repository=link_repo,
    )
    return service, link_repo


async def test_create_extracted_issues_creates_note_issue_links() -> None:
    """After creating issues, NoteIssueLink records are created via link_repo."""
    from contextlib import asynccontextmanager
    from unittest.mock import patch

    from pilot_space.application.services.ai_extraction import (
        CreateExtractedIssuesPayload,
        ExtractedIssueInput,
    )
    from pilot_space.infrastructure.database.models.note_issue_link import (
        NoteLinkType,
    )

    session = AsyncMock()

    @asynccontextmanager
    async def _fake_begin_nested():
        yield None

    session.begin_nested = MagicMock(side_effect=_fake_begin_nested)

    issue_result_1 = _make_issue_result(ISSUE_ID_1, sequence_id=1)
    issue_result_2 = _make_issue_result(ISSUE_ID_2, sequence_id=2)

    link_repo = AsyncMock()
    link_repo.find_existing.return_value = None
    created_links: list = []
    link_repo.create = AsyncMock(side_effect=lambda lnk: created_links.append(lnk))

    service, _ = _make_service(session, [issue_result_1, issue_result_2], link_repo)

    payload = CreateExtractedIssuesPayload(
        workspace_id=WORKSPACE_ID,
        note_id=str(NOTE_ID),
        project_id=str(PROJECT_ID),
        user_id=uuid4(),
        issues=[
            ExtractedIssueInput(
                title="Issue 1",
                description="First issue",
                source_block_id="block-abc",
            ),
            ExtractedIssueInput(
                title="Issue 2",
                description="Second issue",
                source_block_id=None,
            ),
        ],
    )

    with patch(
        "pilot_space.application.services.issue.CreateIssueService"
    ) as MockCreateIssueService:
        mock_issue_service = AsyncMock()
        mock_issue_service.execute.side_effect = [issue_result_1, issue_result_2]
        MockCreateIssueService.return_value = mock_issue_service

        result = await service.execute(payload)

    assert result.created_count == 2
    assert len(result.created_issues) == 2

    # Verify NoteIssueLink records were created via link_repo
    assert len(created_links) == 2, (
        f"Expected 2 NoteIssueLink records to be created, got {len(created_links)}."
    )

    # First link has block_id from source_block_id
    link1 = next(lnk for lnk in created_links if lnk.issue_id == ISSUE_ID_1)
    assert link1.note_id == NOTE_ID
    assert link1.issue_id == ISSUE_ID_1
    assert link1.link_type == NoteLinkType.EXTRACTED
    assert link1.workspace_id == WORKSPACE_ID
    assert link1.block_id == "block-abc"

    # Second link has block_id=None
    link2 = next(lnk for lnk in created_links if lnk.issue_id == ISSUE_ID_2)
    assert link2.note_id == NOTE_ID
    assert link2.issue_id == ISSUE_ID_2
    assert link2.link_type == NoteLinkType.EXTRACTED
    assert link2.workspace_id == WORKSPACE_ID
    assert link2.block_id is None


async def test_create_extracted_issues_links_use_extracted_type() -> None:
    """NoteIssueLink records must use link_type=EXTRACTED, not RELATED or other."""
    from contextlib import asynccontextmanager
    from unittest.mock import patch

    from pilot_space.application.services.ai_extraction import (
        CreateExtractedIssuesPayload,
        ExtractedIssueInput,
    )
    from pilot_space.infrastructure.database.models.note_issue_link import (
        NoteLinkType,
    )

    session = AsyncMock()

    @asynccontextmanager
    async def _fake_begin_nested():
        yield None

    session.begin_nested = MagicMock(side_effect=_fake_begin_nested)

    issue_result = _make_issue_result(ISSUE_ID_1, sequence_id=1)

    link_repo = AsyncMock()
    link_repo.find_existing.return_value = None
    created_links: list = []
    link_repo.create = AsyncMock(side_effect=lambda lnk: created_links.append(lnk))

    service, _ = _make_service(session, [issue_result], link_repo)

    payload = CreateExtractedIssuesPayload(
        workspace_id=WORKSPACE_ID,
        note_id=str(NOTE_ID),
        project_id=str(PROJECT_ID),
        user_id=uuid4(),
        issues=[ExtractedIssueInput(title="Test Issue")],
    )

    with patch(
        "pilot_space.application.services.issue.CreateIssueService"
    ) as MockCreateIssueService:
        mock_issue_service = AsyncMock()
        mock_issue_service.execute.return_value = issue_result
        MockCreateIssueService.return_value = mock_issue_service

        await service.execute(payload)

    assert len(created_links) == 1
    assert created_links[0].link_type == NoteLinkType.EXTRACTED
