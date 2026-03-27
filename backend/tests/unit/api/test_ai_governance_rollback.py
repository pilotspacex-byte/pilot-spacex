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
from unittest.mock import AsyncMock, MagicMock

import pytest

from pilot_space.application.services.ai_governance import GovernanceRollbackService
from pilot_space.domain.exceptions import ValidationError as DomainValidationError


def _make_service(
    mock_session: MagicMock,
) -> tuple[GovernanceRollbackService, AsyncMock, AsyncMock]:
    """Create a GovernanceRollbackService with injected mock services.

    Returns:
        Tuple of (service, mock_issue_execute, mock_note_execute).
    """
    from pilot_space.infrastructure.database.repositories.audit_log_repository import (
        AuditLogRepository,
    )
    from pilot_space.infrastructure.database.repositories.workspace_ai_policy_repository import (
        WorkspaceAIPolicyRepository,
    )
    from pilot_space.infrastructure.database.repositories.workspace_repository import (
        WorkspaceRepository,
    )

    mock_issue_execute = AsyncMock(return_value=MagicMock())
    mock_update_issue_svc = MagicMock()
    mock_update_issue_svc.execute = mock_issue_execute

    mock_note_execute = AsyncMock(return_value=MagicMock())
    mock_update_note_svc = MagicMock()
    mock_update_note_svc.execute = mock_note_execute

    svc = GovernanceRollbackService(
        session=mock_session,
        workspace_repository=MagicMock(spec=WorkspaceRepository),
        audit_log_repository=MagicMock(spec=AuditLogRepository),
        workspace_ai_policy_repository=MagicMock(spec=WorkspaceAIPolicyRepository),
        update_issue_service=mock_update_issue_svc,
        update_note_service=mock_update_note_svc,
    )
    return svc, mock_issue_execute, mock_note_execute


@pytest.mark.asyncio
async def test_dispatch_rollback_issue_calls_service_with_name() -> None:
    """Test 1: _dispatch_rollback('issue', ...) calls UpdateIssueService.execute()
    with the correct name field from before_state['title']."""
    issue_id = uuid.uuid4()
    mock_session = MagicMock()
    before_state = {"title": "Old Title"}

    svc, mock_execute, _ = _make_service(mock_session)
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

    svc, _, mock_execute = _make_service(mock_session)
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

    svc, mock_execute, _ = _make_service(mock_session)
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

    svc, mock_execute, _ = _make_service(mock_session)
    # Should not raise
    await svc._dispatch_rollback("issue", issue_id, before_state)

    mock_execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_dispatch_rollback_unknown_resource_type_raises_422() -> None:
    """Test 5: _dispatch_rollback('other', ...) raises DomainValidationError 422."""
    resource_id = uuid.uuid4()
    mock_session = MagicMock()
    before_state: dict = {}

    svc, _, _ = _make_service(mock_session)
    with pytest.raises(DomainValidationError) as exc_info:
        await svc._dispatch_rollback("other", resource_id, before_state)

    assert exc_info.value.http_status == 422
