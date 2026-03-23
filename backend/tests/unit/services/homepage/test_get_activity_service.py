"""Unit tests for GetActivityService (H053).

Tests:
- Empty workspace returns no groups
- Groups notes by day (today/yesterday/this_week)
- Groups issues by day
- Cursor pagination with has_more
- Cursor continuation
- Mixed notes and issues sorted by updated_at desc

Note: These tests mock the repository layer since HomepageRepository
uses PostgreSQL-specific LATERAL joins not supported in SQLite.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from pilot_space.application.services.homepage.get_activity_service import (
    GetActivityPayload,
    GetActivityService,
)
from pilot_space.infrastructure.database.repositories.homepage_repository import (
    IssueActivityRow,
    NoteActivityRow,
)


@pytest.mark.asyncio
class TestGetActivityService:
    """Test suite for GetActivityService."""

    async def test_empty_workspace_returns_no_groups(self) -> None:
        """Empty workspace returns empty groups."""
        workspace_id = uuid.uuid4()

        # Mock session (not used directly but required by service)
        mock_session = AsyncMock()

        mock_repo = AsyncMock()
        mock_repo.get_recent_notes_with_annotations.return_value = []
        mock_repo.get_recent_issues_with_activity.return_value = []

        service = GetActivityService(mock_session, homepage_repository=mock_repo)
        payload = GetActivityPayload(workspace_id=workspace_id, limit=20)

        result = await service.execute(payload)

        assert result.total == 0
        assert len(result.grouped.today) == 0
        assert len(result.grouped.yesterday) == 0
        assert len(result.grouped.this_week) == 0
        assert result.cursor is None
        assert result.has_more is False

    async def test_groups_notes_by_day(self) -> None:
        """Notes are grouped into today/yesterday/this_week buckets."""
        workspace_id = uuid.uuid4()
        mock_session = AsyncMock()

        now = datetime.now(tz=UTC)
        today = now.replace(hour=12, minute=0, second=0, microsecond=0)
        yesterday = today - timedelta(days=1)
        this_week = today - timedelta(days=3)

        note_today_id = uuid.uuid4()
        note_yesterday_id = uuid.uuid4()
        note_this_week_id = uuid.uuid4()

        notes = [
            NoteActivityRow(
                id=note_today_id,
                title="Today Note",
                word_count=100,
                is_pinned=False,
                updated_at=today,
                project_id=None,
                project_name=None,
                project_identifier=None,
                annotation_type=None,
                annotation_content=None,
                annotation_confidence=None,
            ),
            NoteActivityRow(
                id=note_yesterday_id,
                title="Yesterday Note",
                word_count=100,
                is_pinned=False,
                updated_at=yesterday,
                project_id=None,
                project_name=None,
                project_identifier=None,
                annotation_type=None,
                annotation_content=None,
                annotation_confidence=None,
            ),
            NoteActivityRow(
                id=note_this_week_id,
                title="This Week Note",
                word_count=100,
                is_pinned=False,
                updated_at=this_week,
                project_id=None,
                project_name=None,
                project_identifier=None,
                annotation_type=None,
                annotation_content=None,
                annotation_confidence=None,
            ),
        ]

        mock_repo = AsyncMock()
        mock_repo.get_recent_notes_with_annotations.return_value = notes
        mock_repo.get_recent_issues_with_activity.return_value = []

        service = GetActivityService(mock_session, homepage_repository=mock_repo)
        payload = GetActivityPayload(workspace_id=workspace_id, limit=20)

        result = await service.execute(payload)

        assert result.total == 3
        assert len(result.grouped.today) == 1
        assert len(result.grouped.yesterday) == 1
        assert len(result.grouped.this_week) == 1

        assert result.grouped.today[0].id == note_today_id
        assert result.grouped.yesterday[0].id == note_yesterday_id
        assert result.grouped.this_week[0].id == note_this_week_id

    async def test_groups_issues_by_day(self) -> None:
        """Issues are grouped into today/yesterday/this_week buckets."""
        workspace_id = uuid.uuid4()
        mock_session = AsyncMock()

        now = datetime.now(tz=UTC)
        today = now.replace(hour=12, minute=0, second=0, microsecond=0)
        yesterday = today - timedelta(days=1)
        this_week = today - timedelta(days=3)

        issue_today_id = uuid.uuid4()
        issue_yesterday_id = uuid.uuid4()
        issue_this_week_id = uuid.uuid4()

        issues = [
            IssueActivityRow(
                id=issue_today_id,
                sequence_id=1,
                name="Today Issue",
                priority="none",
                updated_at=today,
                project_id=None,
                project_name=None,
                project_identifier=None,
                state_name=None,
                state_color=None,
                state_group=None,
                assignee_id=None,
                assignee_name=None,
                assignee_avatar_url=None,
                last_activity=None,
            ),
            IssueActivityRow(
                id=issue_yesterday_id,
                sequence_id=2,
                name="Yesterday Issue",
                priority="none",
                updated_at=yesterday,
                project_id=None,
                project_name=None,
                project_identifier=None,
                state_name=None,
                state_color=None,
                state_group=None,
                assignee_id=None,
                assignee_name=None,
                assignee_avatar_url=None,
                last_activity=None,
            ),
            IssueActivityRow(
                id=issue_this_week_id,
                sequence_id=3,
                name="This Week Issue",
                priority="none",
                updated_at=this_week,
                project_id=None,
                project_name=None,
                project_identifier=None,
                state_name=None,
                state_color=None,
                state_group=None,
                assignee_id=None,
                assignee_name=None,
                assignee_avatar_url=None,
                last_activity=None,
            ),
        ]

        mock_repo = AsyncMock()
        mock_repo.get_recent_notes_with_annotations.return_value = []
        mock_repo.get_recent_issues_with_activity.return_value = issues

        service = GetActivityService(mock_session, homepage_repository=mock_repo)
        payload = GetActivityPayload(workspace_id=workspace_id, limit=20)

        result = await service.execute(payload)

        assert result.total == 3
        assert len(result.grouped.today) == 1
        assert len(result.grouped.yesterday) == 1
        assert len(result.grouped.this_week) == 1

        assert result.grouped.today[0].id == issue_today_id
        assert result.grouped.yesterday[0].id == issue_yesterday_id
        assert result.grouped.this_week[0].id == issue_this_week_id

    async def test_cursor_pagination(self) -> None:
        """Pagination works with limit and returns cursor + has_more."""
        workspace_id = uuid.uuid4()
        mock_session = AsyncMock()

        now = datetime.now(tz=UTC).replace(hour=12, minute=0, second=0, microsecond=0)

        # Create 3 notes with different timestamps
        notes = [
            NoteActivityRow(
                id=uuid.uuid4(),
                title=f"Note {i}",
                word_count=100,
                is_pinned=False,
                updated_at=now - timedelta(hours=i),
                project_id=None,
                project_name=None,
                project_identifier=None,
                annotation_type=None,
                annotation_content=None,
                annotation_confidence=None,
            )
            for i in range(3)
        ]

        mock_repo = AsyncMock()
        # Return all notes (service will handle limit)
        mock_repo.get_recent_notes_with_annotations.return_value = notes
        mock_repo.get_recent_issues_with_activity.return_value = []

        service = GetActivityService(mock_session, homepage_repository=mock_repo)
        # Limit to 1 item
        payload = GetActivityPayload(workspace_id=workspace_id, limit=1)

        result = await service.execute(payload)

        # Should return only 1 item
        assert result.total == 1
        assert result.has_more is True
        assert result.cursor is not None

    async def test_cursor_continuation(self) -> None:
        """Using returned cursor fetches next page."""
        workspace_id = uuid.uuid4()
        mock_session = AsyncMock()

        now = datetime.now(tz=UTC).replace(hour=12, minute=0, second=0, microsecond=0)

        # Create 3 notes
        note_ids = [uuid.uuid4() for _ in range(3)]
        notes = [
            NoteActivityRow(
                id=note_ids[i],
                title=f"Note {i}",
                word_count=100,
                is_pinned=False,
                updated_at=now - timedelta(hours=i),
                project_id=None,
                project_name=None,
                project_identifier=None,
                annotation_type=None,
                annotation_content=None,
                annotation_confidence=None,
            )
            for i in range(3)
        ]

        mock_repo = AsyncMock()
        # First call: return all notes
        mock_repo.get_recent_notes_with_annotations.return_value = notes
        mock_repo.get_recent_issues_with_activity.return_value = []

        service = GetActivityService(mock_session, homepage_repository=mock_repo)

        # First page
        payload1 = GetActivityPayload(workspace_id=workspace_id, limit=1)
        result1 = await service.execute(payload1)

        assert result1.total == 1
        assert result1.has_more is True
        first_cursor = result1.cursor
        assert first_cursor is not None

        # Second page using cursor
        # Mock repo should filter results based on cursor
        mock_repo.get_recent_notes_with_annotations.return_value = notes[1:]

        payload2 = GetActivityPayload(
            workspace_id=workspace_id,
            limit=1,
            cursor=first_cursor,
        )
        result2 = await service.execute(payload2)

        assert result2.total == 1
        assert result2.has_more is True

        # Items should be different
        first_id = result1.grouped.today[0].id
        second_id = result2.grouped.today[0].id
        assert first_id != second_id

    async def test_mixed_notes_and_issues(self) -> None:
        """Mixed notes and issues appear sorted by updated_at desc."""
        workspace_id = uuid.uuid4()
        mock_session = AsyncMock()

        now = datetime.now(tz=UTC).replace(hour=12, minute=0, second=0, microsecond=0)
        note_id = uuid.uuid4()
        issue_id = uuid.uuid4()

        # Note is most recent
        note = NoteActivityRow(
            id=note_id,
            title="Recent Note",
            word_count=100,
            is_pinned=False,
            updated_at=now,
            project_id=None,
            project_name=None,
            project_identifier=None,
            annotation_type=None,
            annotation_content=None,
            annotation_confidence=None,
        )

        # Issue is older
        issue = IssueActivityRow(
            id=issue_id,
            sequence_id=1,
            name="Older Issue",
            priority="none",
            updated_at=now - timedelta(hours=1),
            project_id=None,
            project_name=None,
            project_identifier=None,
            state_name=None,
            state_color=None,
            state_group=None,
            assignee_id=None,
            assignee_name=None,
            assignee_avatar_url=None,
            last_activity=None,
        )

        mock_repo = AsyncMock()
        mock_repo.get_recent_notes_with_annotations.return_value = [note]
        mock_repo.get_recent_issues_with_activity.return_value = [issue]

        service = GetActivityService(mock_session, homepage_repository=mock_repo)
        payload = GetActivityPayload(workspace_id=workspace_id, limit=20)

        result = await service.execute(payload)

        assert result.total == 2
        assert len(result.grouped.today) == 2

        # First item should be the note (most recent)
        assert result.grouped.today[0].id == note_id
        assert result.grouped.today[0].type == "note"

        # Second item should be the issue
        assert result.grouped.today[1].id == issue_id
        assert result.grouped.today[1].type == "issue"
