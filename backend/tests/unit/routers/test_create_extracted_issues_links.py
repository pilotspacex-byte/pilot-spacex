"""Tests for create_extracted_issues NoteIssueLink creation.

Verifies that the create_extracted_issues endpoint creates NoteIssueLink
records with link_type=EXTRACTED for each created issue, with correct
note_id, issue_id, workspace_id, and optional block_id.
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


def _make_workspace() -> MagicMock:
    """Build a mock workspace."""
    workspace = MagicMock()
    workspace.id = WORKSPACE_ID
    return workspace


def _make_note(workspace_id=None, project_id=None) -> MagicMock:
    """Build a mock note."""
    note = MagicMock()
    note.id = NOTE_ID
    note.workspace_id = workspace_id or WORKSPACE_ID
    note.project_id = project_id or uuid4()
    return note


def _make_issue_result(issue_id=None) -> MagicMock:
    """Build a mock CreateIssueResult."""
    result = MagicMock()
    result.issue = MagicMock()
    result.issue.id = issue_id or uuid4()
    return result


async def test_create_extracted_issues_creates_note_issue_links() -> None:
    """After creating issues, NoteIssueLink(EXTRACTED) records are added to session."""
    from pilot_space.api.v1.routers.workspace_notes_ai import (
        CreateExtractedIssuesRequest,
        ExtractedIssueInput,
        create_extracted_issues,
    )
    from pilot_space.infrastructure.database.models.note_issue_link import NoteLinkType

    workspace = _make_workspace()
    note = _make_note()
    issue_result_1 = _make_issue_result(ISSUE_ID_1)
    issue_result_2 = _make_issue_result(ISSUE_ID_2)

    # Track session.add calls to verify NoteIssueLink records
    # session.add is synchronous (not a coroutine), so use MagicMock for it
    session = AsyncMock()
    added_objects: list = []
    session.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))
    session.commit = AsyncMock()

    create_issue_service = AsyncMock()
    create_issue_service.execute.side_effect = [issue_result_1, issue_result_2]

    workspace_repo = AsyncMock()
    workspace_repo.get_by_id.return_value = workspace

    note_repo = AsyncMock()
    note_repo.get_by_id.return_value = note

    body = CreateExtractedIssuesRequest(
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
        ]
    )

    response = await create_extracted_issues(
        workspace_id=str(WORKSPACE_ID),
        note_id=NOTE_ID,
        body=body,
        session=session,
        current_user_id=uuid4(),
        note_repo=note_repo,
        create_issue_service=create_issue_service,
        workspace_repo=workspace_repo,
    )

    assert response.count == 2
    assert len(response.created_issue_ids) == 2

    # Verify NoteIssueLink records were added
    from pilot_space.infrastructure.database.models.note_issue_link import NoteIssueLink

    link_objects = [obj for obj in added_objects if isinstance(obj, NoteIssueLink)]
    assert len(link_objects) == 2, (
        f"Expected 2 NoteIssueLink records to be added, got {len(link_objects)}. "
        f"All added objects: {added_objects}"
    )

    # First link has block_id from source_block_id
    link1 = next(lnk for lnk in link_objects if lnk.issue_id == ISSUE_ID_1)
    assert link1.note_id == NOTE_ID
    assert link1.issue_id == ISSUE_ID_1
    assert link1.link_type == NoteLinkType.EXTRACTED
    assert link1.workspace_id == WORKSPACE_ID
    assert link1.block_id == "block-abc"

    # Second link has block_id=None
    link2 = next(lnk for lnk in link_objects if lnk.issue_id == ISSUE_ID_2)
    assert link2.note_id == NOTE_ID
    assert link2.issue_id == ISSUE_ID_2
    assert link2.link_type == NoteLinkType.EXTRACTED
    assert link2.workspace_id == WORKSPACE_ID
    assert link2.block_id is None


async def test_create_extracted_issues_links_use_extracted_type() -> None:
    """NoteIssueLink records must use link_type=EXTRACTED, not RELATED or other."""
    from pilot_space.api.v1.routers.workspace_notes_ai import (
        CreateExtractedIssuesRequest,
        ExtractedIssueInput,
        create_extracted_issues,
    )
    from pilot_space.infrastructure.database.models.note_issue_link import (
        NoteIssueLink,
        NoteLinkType,
    )

    workspace = _make_workspace()
    note = _make_note()
    issue_result = _make_issue_result(ISSUE_ID_1)

    # session.add is synchronous (not a coroutine), so use MagicMock for it
    session = AsyncMock()
    added_objects: list = []
    session.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))
    session.commit = AsyncMock()

    create_issue_service = AsyncMock()
    create_issue_service.execute.return_value = issue_result

    workspace_repo = AsyncMock()
    workspace_repo.get_by_id.return_value = workspace

    note_repo = AsyncMock()
    note_repo.get_by_id.return_value = note

    body = CreateExtractedIssuesRequest(issues=[ExtractedIssueInput(title="Test Issue")])

    await create_extracted_issues(
        workspace_id=str(WORKSPACE_ID),
        note_id=NOTE_ID,
        body=body,
        session=session,
        current_user_id=uuid4(),
        note_repo=note_repo,
        create_issue_service=create_issue_service,
        workspace_repo=workspace_repo,
    )

    link_objects = [obj for obj in added_objects if isinstance(obj, NoteIssueLink)]
    assert len(link_objects) == 1
    assert link_objects[0].link_type == NoteLinkType.EXTRACTED
