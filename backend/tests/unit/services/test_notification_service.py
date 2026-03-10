"""Unit tests for NotificationService.

Uses in-memory SQLite via the local conftest fixture.
RLS policies are PostgreSQL-specific and are not tested here — they are
verified in integration tests with a real PostgreSQL instance.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from pilot_space.application.services.notification.notification_service import (
    NotificationListResult,
    NotificationNotFoundError,
    NotificationService,
)
from pilot_space.infrastructure.database.models.notification import (
    Notification,
    NotificationPriority,
    NotificationType,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_notification(
    *,
    workspace_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    type: NotificationType = NotificationType.GENERAL,
    title: str = "Test notification",
    body: str = "Body text",
    priority: NotificationPriority = NotificationPriority.MEDIUM,
    read_at: datetime | None = None,
) -> Notification:
    """Create a Notification ORM object without persisting."""
    n = Notification()
    n.id = uuid4()
    n.workspace_id = workspace_id or uuid4()
    n.user_id = user_id or uuid4()
    n.type = type
    n.title = title
    n.body = body
    n.entity_type = None
    n.entity_id = None
    n.priority = priority
    n.read_at = read_at
    n.created_at = datetime.now(tz=UTC)
    n.updated_at = datetime.now(tz=UTC)
    n.is_deleted = False
    n.deleted_at = None
    return n


def _make_service(
    *,
    notifications: list[Notification] | None = None,
    total: int | None = None,
    mark_read_result: Notification | None = None,
    mark_all_count: int = 0,
    unread_count: int = 0,
) -> tuple[NotificationService, MagicMock]:
    """Build a NotificationService with a fully mocked repository."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()

    repo = MagicMock()
    repo.list_for_user = AsyncMock(
        return_value=(notifications or [], total if total is not None else len(notifications or []))
    )
    repo.mark_read = AsyncMock(return_value=mark_read_result)
    repo.mark_all_read = AsyncMock(return_value=mark_all_count)
    repo.count_unread = AsyncMock(return_value=unread_count)

    service = NotificationService(session=session, notification_repository=repo)
    return service, repo


# ---------------------------------------------------------------------------
# Tests: create
# ---------------------------------------------------------------------------


class TestNotificationServiceCreate:
    """Tests for NotificationService.create."""

    @pytest.mark.asyncio
    async def test_create_persists_notification(self) -> None:
        """create() adds the notification to the session and flushes."""
        service, _ = _make_service()
        workspace_id = uuid4()
        user_id = uuid4()

        result = await service.create(
            workspace_id=workspace_id,
            user_id=user_id,
            type=NotificationType.ASSIGNMENT,
            title="Assigned to you: PS-1 Fix login",
            body="You have been assigned to issue PS-1.",
            priority=NotificationPriority.MEDIUM,
        )

        service._session.add.assert_called_once()
        service._session.flush.assert_awaited_once()
        service._session.refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_truncates_long_title(self) -> None:
        """create() truncates title to 255 characters."""
        service, _ = _make_service()
        long_title = "x" * 300

        await service.create(
            workspace_id=uuid4(),
            user_id=uuid4(),
            type=NotificationType.GENERAL,
            title=long_title,
            body="",
        )

        # The Notification passed to session.add should have a truncated title
        added_notification: Notification = service._session.add.call_args[0][0]
        assert len(added_notification.title) == 255

    @pytest.mark.asyncio
    async def test_create_sets_default_priority(self) -> None:
        """create() defaults priority to MEDIUM when not specified."""
        service, _ = _make_service()

        await service.create(
            workspace_id=uuid4(),
            user_id=uuid4(),
            type=NotificationType.GENERAL,
            title="Hello",
            body="",
        )

        added: Notification = service._session.add.call_args[0][0]
        assert added.priority == NotificationPriority.MEDIUM

    @pytest.mark.asyncio
    async def test_create_with_entity_reference(self) -> None:
        """create() stores entity_type and entity_id when provided."""
        service, _ = _make_service()
        entity_id = uuid4()

        await service.create(
            workspace_id=uuid4(),
            user_id=uuid4(),
            type=NotificationType.PR_REVIEW,
            title="PR Review Complete",
            body="Review finished with findings.",
            entity_type="issue",
            entity_id=entity_id,
            priority=NotificationPriority.HIGH,
        )

        added: Notification = service._session.add.call_args[0][0]
        assert added.entity_type == "issue"
        assert added.entity_id == entity_id


# ---------------------------------------------------------------------------
# Tests: mark_read
# ---------------------------------------------------------------------------


class TestNotificationServiceMarkRead:
    """Tests for NotificationService.mark_read."""

    @pytest.mark.asyncio
    async def test_mark_read_returns_updated_notification(self) -> None:
        """mark_read() returns the updated Notification on success."""
        notification = _make_notification()
        service, repo = _make_service(mark_read_result=notification)

        result = await service.mark_read(notification.id, notification.user_id)

        repo.mark_read.assert_awaited_once_with(notification.id, notification.user_id)
        assert result is notification

    @pytest.mark.asyncio
    async def test_mark_read_raises_not_found_when_repo_returns_none(self) -> None:
        """mark_read() raises NotificationNotFoundError when repo returns None."""
        service, _ = _make_service(mark_read_result=None)

        with pytest.raises(NotificationNotFoundError):
            await service.mark_read(uuid4(), uuid4())

    @pytest.mark.asyncio
    async def test_mark_read_passes_correct_ids_to_repo(self) -> None:
        """mark_read() forwards the exact notification_id and user_id to the repo."""
        notification = _make_notification()
        service, repo = _make_service(mark_read_result=notification)

        nid = uuid4()
        uid = uuid4()
        repo.mark_read.return_value = notification

        await service.mark_read(nid, uid)

        repo.mark_read.assert_awaited_once_with(nid, uid)


# ---------------------------------------------------------------------------
# Tests: mark_all_read
# ---------------------------------------------------------------------------


class TestNotificationServiceMarkAllRead:
    """Tests for NotificationService.mark_all_read."""

    @pytest.mark.asyncio
    async def test_mark_all_read_returns_count(self) -> None:
        """mark_all_read() returns the number of notifications updated."""
        service, repo = _make_service(mark_all_count=5)
        workspace_id = uuid4()
        user_id = uuid4()

        count = await service.mark_all_read(workspace_id, user_id)

        assert count == 5
        repo.mark_all_read.assert_awaited_once_with(workspace_id, user_id)

    @pytest.mark.asyncio
    async def test_mark_all_read_zero_when_nothing_unread(self) -> None:
        """mark_all_read() returns 0 when all notifications are already read."""
        service, _ = _make_service(mark_all_count=0)

        count = await service.mark_all_read(uuid4(), uuid4())

        assert count == 0


# ---------------------------------------------------------------------------
# Tests: list_for_user
# ---------------------------------------------------------------------------


class TestNotificationServiceListForUser:
    """Tests for NotificationService.list_for_user."""

    @pytest.mark.asyncio
    async def test_list_returns_items_and_total(self) -> None:
        """list_for_user() returns a NotificationListResult with items and total."""
        notifications = [_make_notification() for _ in range(3)]
        service, repo = _make_service(notifications=notifications, total=10)
        workspace_id = uuid4()
        user_id = uuid4()

        result = await service.list_for_user(workspace_id, user_id, page=1, page_size=3)

        assert isinstance(result, NotificationListResult)
        assert len(result.items) == 3
        assert result.total == 10
        assert result.page == 1
        assert result.page_size == 3
        assert result.total_pages == 4  # ceil(10/3)

    @pytest.mark.asyncio
    async def test_list_clamps_page_size_to_100(self) -> None:
        """list_for_user() clamps page_size to 100."""
        service, repo = _make_service(notifications=[], total=0)

        await service.list_for_user(uuid4(), uuid4(), page=1, page_size=9999)

        _, kwargs = repo.list_for_user.call_args
        assert kwargs["page_size"] == 100

    @pytest.mark.asyncio
    async def test_list_clamps_page_to_minimum_1(self) -> None:
        """list_for_user() clamps page to minimum 1."""
        service, repo = _make_service(notifications=[], total=0)

        await service.list_for_user(uuid4(), uuid4(), page=-5, page_size=10)

        _, kwargs = repo.list_for_user.call_args
        assert kwargs["page"] == 1

    @pytest.mark.asyncio
    async def test_list_passes_unread_only_flag(self) -> None:
        """list_for_user() passes unread_only=True to the repository."""
        service, repo = _make_service(notifications=[], total=0)

        await service.list_for_user(uuid4(), uuid4(), unread_only=True)

        _, kwargs = repo.list_for_user.call_args
        assert kwargs["unread_only"] is True

    @pytest.mark.asyncio
    async def test_total_pages_rounds_up(self) -> None:
        """total_pages is ceiling(total / page_size)."""
        service, _ = _make_service(notifications=[], total=21)

        result = await service.list_for_user(uuid4(), uuid4(), page=1, page_size=10)

        assert result.total_pages == 3


# ---------------------------------------------------------------------------
# Tests: count_unread
# ---------------------------------------------------------------------------


class TestNotificationServiceCountUnread:
    """Tests for NotificationService.count_unread."""

    @pytest.mark.asyncio
    async def test_count_unread_delegates_to_repo(self) -> None:
        """count_unread() returns the value from the repository."""
        service, repo = _make_service(unread_count=7)
        workspace_id = uuid4()
        user_id = uuid4()

        count = await service.count_unread(workspace_id, user_id)

        assert count == 7
        repo.count_unread.assert_awaited_once_with(workspace_id, user_id)

    @pytest.mark.asyncio
    async def test_count_unread_returns_zero_when_all_read(self) -> None:
        """count_unread() returns 0 when no unread notifications exist."""
        service, _ = _make_service(unread_count=0)

        count = await service.count_unread(uuid4(), uuid4())

        assert count == 0
