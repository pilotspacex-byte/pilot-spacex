"""Unit tests for _dispatch_rollback() in ai_governance router.

Tests cover:
1. Issue rollback calls UpdateIssueService.execute() with correct name field
2. Note rollback calls UpdateNoteService.execute() with correct title/content
3. Priority string 'high' maps to IssuePriority.HIGH in issue payload
4. Empty before_state does not raise (updates nothing)
5. Unknown resource_type raises HTTPException 422
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pilot_space.application.services.ai_governance import GovernanceRollbackService
from pilot_space.domain.exceptions import ValidationError as DomainValidationError

# Lazy imports inside service methods resolve from these module paths
_UPDATE_ISSUE_SVC = "pilot_space.application.services.issue.update_issue_service.UpdateIssueService"
_ISSUE_REPO = "pilot_space.infrastructure.database.repositories.IssueRepository"
_ACTIVITY_REPO = "pilot_space.infrastructure.database.repositories.ActivityRepository"
_LABEL_REPO = "pilot_space.infrastructure.database.repositories.LabelRepository"
_UPDATE_NOTE_SVC = "pilot_space.application.services.note.update_note_service.UpdateNoteService"
_NOTE_REPO = "pilot_space.infrastructure.database.repositories.NoteRepository"


def _make_service(mock_session: MagicMock) -> GovernanceRollbackService:
    """Create a GovernanceRollbackService with a mock session."""
    return GovernanceRollbackService(session=mock_session)


@pytest.mark.asyncio
async def test_dispatch_rollback_issue_calls_service_with_name() -> None:
    """Test 1: _dispatch_rollback('issue', ...) calls UpdateIssueService.execute()
    with the correct name field from before_state['title']."""
    issue_id = uuid.uuid4()
    mock_session = MagicMock()
    before_state = {"title": "Old Title"}

    mock_execute = AsyncMock(return_value=MagicMock())

    with (
        patch(_UPDATE_ISSUE_SVC) as MockUpdateIssueService,
        patch(_ISSUE_REPO),
        patch(_ACTIVITY_REPO),
        patch(_LABEL_REPO),
    ):
        mock_svc_instance = MagicMock()
        mock_svc_instance.execute = mock_execute
        MockUpdateIssueService.return_value = mock_svc_instance

        svc = _make_service(mock_session)
        await svc._dispatch_rollback("issue", issue_id, before_state)

    mock_execute.assert_awaited_once()
    call_args = mock_execute.call_args[0][0]  # positional first arg = UpdateIssuePayload
    assert call_args.name == "Old Title"
    assert call_args.issue_id == issue_id


@pytest.mark.asyncio
async def test_dispatch_rollback_note_calls_service_with_title_and_content() -> None:
    """Test 2: _dispatch_rollback('note', ...) calls UpdateNoteService.execute()
    with correct title and content fields."""
    note_id = uuid.uuid4()
    mock_session = MagicMock()
    before_state = {"title": "Old Note Title", "content": {"type": "doc", "content": []}}

    mock_execute = AsyncMock(return_value=MagicMock())

    with (
        patch(_UPDATE_NOTE_SVC) as MockUpdateNoteService,
        patch(_NOTE_REPO),
    ):
        mock_svc_instance = MagicMock()
        mock_svc_instance.execute = mock_execute
        MockUpdateNoteService.return_value = mock_svc_instance

        svc = _make_service(mock_session)
        await svc._dispatch_rollback("note", note_id, before_state)

    mock_execute.assert_awaited_once()
    call_args = mock_execute.call_args[0][0]  # positional first arg = UpdateNotePayload
    assert call_args.title == "Old Note Title"
    assert call_args.content == {"type": "doc", "content": []}
    assert call_args.note_id == note_id


@pytest.mark.asyncio
async def test_dispatch_rollback_issue_maps_priority_high() -> None:
    """Test 3: _dispatch_rollback('issue', ..., {'priority': 'high'}) maps 'high'
    to IssuePriority.HIGH in UpdateIssuePayload."""
    issue_id = uuid.uuid4()
    mock_session = MagicMock()
    before_state = {"priority": "high"}

    mock_execute = AsyncMock(return_value=MagicMock())

    with (
        patch(_UPDATE_ISSUE_SVC) as MockUpdateIssueService,
        patch(_ISSUE_REPO),
        patch(_ACTIVITY_REPO),
        patch(_LABEL_REPO),
    ):
        mock_svc_instance = MagicMock()
        mock_svc_instance.execute = mock_execute
        MockUpdateIssueService.return_value = mock_svc_instance

        svc = _make_service(mock_session)
        await svc._dispatch_rollback("issue", issue_id, before_state)

    from pilot_space.infrastructure.database.models import IssuePriority

    call_args = mock_execute.call_args[0][0]
    assert call_args.priority == IssuePriority.HIGH


@pytest.mark.asyncio
async def test_dispatch_rollback_issue_empty_before_state_does_not_raise() -> None:
    """Test 4: _dispatch_rollback with empty before_state does not raise.
    Service.execute() is still called, but all fields remain UNCHANGED."""
    issue_id = uuid.uuid4()
    mock_session = MagicMock()
    before_state: dict = {}

    mock_execute = AsyncMock(return_value=MagicMock())

    with (
        patch(_UPDATE_ISSUE_SVC) as MockUpdateIssueService,
        patch(_ISSUE_REPO),
        patch(_ACTIVITY_REPO),
        patch(_LABEL_REPO),
    ):
        mock_svc_instance = MagicMock()
        mock_svc_instance.execute = mock_execute
        MockUpdateIssueService.return_value = mock_svc_instance

        svc = _make_service(mock_session)
        # Should not raise
        await svc._dispatch_rollback("issue", issue_id, before_state)

    mock_execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_dispatch_rollback_unknown_resource_type_raises_422() -> None:
    """Test 5: _dispatch_rollback('other', ...) raises DomainValidationError 422."""
    resource_id = uuid.uuid4()
    mock_session = MagicMock()
    before_state: dict = {}

    svc = _make_service(mock_session)
    with pytest.raises(DomainValidationError) as exc_info:
        await svc._dispatch_rollback("other", resource_id, before_state)

    assert exc_info.value.http_status == 422
