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

from pilot_space.api.v1.routers.ai_governance import _dispatch_rollback
from pilot_space.domain.exceptions import ValidationError as DomainValidationError


@pytest.mark.asyncio
async def test_dispatch_rollback_issue_calls_service_with_name() -> None:
    """Test 1: _dispatch_rollback('issue', ...) calls UpdateIssueService.execute()
    with the correct name field from before_state['title']."""
    issue_id = uuid.uuid4()
    mock_session = MagicMock()
    before_state = {"title": "Old Title"}

    mock_execute = AsyncMock(return_value=MagicMock())

    with (
        patch(
            "pilot_space.api.v1.routers.ai_governance.UpdateIssueService"
        ) as MockUpdateIssueService,
        patch("pilot_space.api.v1.routers.ai_governance.IssueRepository"),
        patch("pilot_space.api.v1.routers.ai_governance.ActivityRepository"),
        patch("pilot_space.api.v1.routers.ai_governance.LabelRepository"),
    ):
        mock_svc_instance = MagicMock()
        mock_svc_instance.execute = mock_execute
        MockUpdateIssueService.return_value = mock_svc_instance

        await _dispatch_rollback("issue", issue_id, before_state, mock_session)

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
        patch(
            "pilot_space.api.v1.routers.ai_governance.UpdateNoteService"
        ) as MockUpdateNoteService,
        patch("pilot_space.api.v1.routers.ai_governance.NoteRepository"),
    ):
        mock_svc_instance = MagicMock()
        mock_svc_instance.execute = mock_execute
        MockUpdateNoteService.return_value = mock_svc_instance

        await _dispatch_rollback("note", note_id, before_state, mock_session)

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
        patch(
            "pilot_space.api.v1.routers.ai_governance.UpdateIssueService"
        ) as MockUpdateIssueService,
        patch("pilot_space.api.v1.routers.ai_governance.IssueRepository"),
        patch("pilot_space.api.v1.routers.ai_governance.ActivityRepository"),
        patch("pilot_space.api.v1.routers.ai_governance.LabelRepository"),
    ):
        mock_svc_instance = MagicMock()
        mock_svc_instance.execute = mock_execute
        MockUpdateIssueService.return_value = mock_svc_instance

        await _dispatch_rollback("issue", issue_id, before_state, mock_session)

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
        patch(
            "pilot_space.api.v1.routers.ai_governance.UpdateIssueService"
        ) as MockUpdateIssueService,
        patch("pilot_space.api.v1.routers.ai_governance.IssueRepository"),
        patch("pilot_space.api.v1.routers.ai_governance.ActivityRepository"),
        patch("pilot_space.api.v1.routers.ai_governance.LabelRepository"),
    ):
        mock_svc_instance = MagicMock()
        mock_svc_instance.execute = mock_execute
        MockUpdateIssueService.return_value = mock_svc_instance

        # Should not raise
        await _dispatch_rollback("issue", issue_id, before_state, mock_session)

    mock_execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_dispatch_rollback_unknown_resource_type_raises_422() -> None:
    """Test 5: _dispatch_rollback('other', ...) raises HTTPException 422."""
    resource_id = uuid.uuid4()
    mock_session = MagicMock()
    before_state: dict = {}

    with pytest.raises(DomainValidationError) as exc_info:
        await _dispatch_rollback("other", resource_id, before_state, mock_session)

    assert exc_info.value.http_status == 422
