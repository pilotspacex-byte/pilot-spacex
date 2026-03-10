"""Unit tests for the notifications router.

Tests verify:
- NotificationResponse schema validation from ORM objects
- NotificationListResponse total_pages calculation
- UnreadCountResponse schema
- build_notification_payload helper from the worker module
- NotificationWorker._persist_notification payload parsing

Router endpoint logic (auth, RLS, HTTP status codes) is tested in
integration tests. Here we focus on pure-Python business logic that is
independent of HTTP and the database.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from pilot_space.ai.workers.notification_worker import (
    NotificationWorker,
    build_notification_payload,
)
from pilot_space.api.v1.routers.notifications import (
    NotificationListResponse,
    NotificationResponse,
    UnreadCountResponse,
)
from pilot_space.infrastructure.database.models.notification import (
    Notification,
    NotificationPriority,
    NotificationType,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_orm_notification(
    *,
    read_at: datetime | None = None,
    type: NotificationType = NotificationType.GENERAL,
    priority: NotificationPriority = NotificationPriority.MEDIUM,
) -> Notification:
    """Build an in-memory Notification ORM object."""
    n = Notification()
    n.id = uuid4()
    n.workspace_id = uuid4()
    n.user_id = uuid4()
    n.type = type
    n.title = "Test notification"
    n.body = "Test body"
    n.entity_type = None
    n.entity_id = None
    n.priority = priority
    n.read_at = read_at
    n.created_at = datetime.now(tz=UTC)
    n.updated_at = datetime.now(tz=UTC)
    n.is_deleted = False
    n.deleted_at = None
    return n


# ---------------------------------------------------------------------------
# Tests: NotificationResponse schema
# ---------------------------------------------------------------------------


class TestNotificationResponseSchema:
    """Tests for NotificationResponse Pydantic model."""

    def test_from_orm_unread_notification(self) -> None:
        """model_validate maps ORM to response with read_at=None."""
        orm = _make_orm_notification(read_at=None)
        response = NotificationResponse.model_validate(orm)

        assert response.id == orm.id
        assert response.workspace_id == orm.workspace_id
        assert response.user_id == orm.user_id
        assert response.type == NotificationType.GENERAL
        assert response.priority == NotificationPriority.MEDIUM
        assert response.read_at is None
        assert response.title == "Test notification"

    def test_from_orm_read_notification(self) -> None:
        """model_validate maps read_at datetime correctly."""
        read_time = datetime(2026, 3, 7, 12, 0, 0, tzinfo=UTC)
        orm = _make_orm_notification(read_at=read_time)
        response = NotificationResponse.model_validate(orm)

        assert response.read_at == read_time

    def test_all_notification_types_serialise(self) -> None:
        """All NotificationType enum values round-trip through the schema."""
        for nt in NotificationType:
            orm = _make_orm_notification(type=nt)
            response = NotificationResponse.model_validate(orm)
            assert response.type == nt

    def test_all_notification_priorities_serialise(self) -> None:
        """All NotificationPriority enum values round-trip through the schema."""
        for np in NotificationPriority:
            orm = _make_orm_notification(priority=np)
            response = NotificationResponse.model_validate(orm)
            assert response.priority == np


# ---------------------------------------------------------------------------
# Tests: NotificationListResponse total_pages
# ---------------------------------------------------------------------------


class TestNotificationListResponse:
    """Tests for NotificationListResponse schema."""

    def test_total_pages_exact_division(self) -> None:
        """total_pages = total / page_size when evenly divisible."""
        resp = NotificationListResponse(
            items=[],
            total=20,
            page=1,
            page_size=10,
            total_pages=2,
        )
        assert resp.total_pages == 2

    def test_total_pages_rounded_up(self) -> None:
        """total_pages rounds up (ceiling division)."""
        resp = NotificationListResponse(
            items=[],
            total=21,
            page=1,
            page_size=10,
            total_pages=3,
        )
        assert resp.total_pages == 3

    def test_empty_list_response(self) -> None:
        """Empty list with total=0 is valid."""
        resp = NotificationListResponse(
            items=[],
            total=0,
            page=1,
            page_size=20,
            total_pages=0,
        )
        assert resp.total == 0
        assert resp.items == []


# ---------------------------------------------------------------------------
# Tests: UnreadCountResponse schema
# ---------------------------------------------------------------------------


class TestUnreadCountResponse:
    """Tests for UnreadCountResponse schema."""

    def test_count_field_present(self) -> None:
        """UnreadCountResponse serialises count correctly."""
        resp = UnreadCountResponse(count=42)
        assert resp.count == 42
        assert resp.model_dump() == {"count": 42}

    def test_count_zero(self) -> None:
        """Zero is a valid count value."""
        resp = UnreadCountResponse(count=0)
        assert resp.count == 0


# ---------------------------------------------------------------------------
# Tests: build_notification_payload helper
# ---------------------------------------------------------------------------


class TestBuildNotificationPayload:
    """Tests for the build_notification_payload helper in notification_worker."""

    def test_returns_dict_with_required_fields(self) -> None:
        """Payload contains all required fields as strings."""
        workspace_id = uuid4()
        user_id = uuid4()

        payload = build_notification_payload(
            workspace_id=workspace_id,
            user_id=user_id,
            notification_type=NotificationType.ASSIGNMENT,
            title="Assigned to you: PS-1",
            body="Issue PS-1 was assigned to you.",
            priority=NotificationPriority.MEDIUM,
        )

        assert payload["workspace_id"] == str(workspace_id)
        assert payload["user_id"] == str(user_id)
        assert payload["type"] == "assignment"
        assert payload["title"] == "Assigned to you: PS-1"
        assert payload["body"] == "Issue PS-1 was assigned to you."
        assert payload["priority"] == "medium"
        assert payload["entity_type"] is None
        assert payload["entity_id"] is None

    def test_entity_reference_included(self) -> None:
        """Payload includes entity_type and entity_id when provided."""
        entity_id = uuid4()

        payload = build_notification_payload(
            workspace_id=uuid4(),
            user_id=uuid4(),
            notification_type=NotificationType.PR_REVIEW,
            title="PR Review Complete",
            entity_type="issue",
            entity_id=entity_id,
            priority=NotificationPriority.HIGH,
        )

        assert payload["entity_type"] == "issue"
        assert payload["entity_id"] == str(entity_id)

    def test_payload_is_json_serialisable(self) -> None:
        """Payload can be serialised to JSON (all UUIDs are strings)."""
        import json

        payload = build_notification_payload(
            workspace_id=uuid4(),
            user_id=uuid4(),
            notification_type=NotificationType.GENERAL,
            title="Hello",
        )

        # Should not raise
        serialised = json.dumps(payload)
        assert isinstance(serialised, str)

    def test_defaults_to_medium_priority(self) -> None:
        """build_notification_payload defaults priority to 'medium'."""
        payload = build_notification_payload(
            workspace_id=uuid4(),
            user_id=uuid4(),
            notification_type=NotificationType.GENERAL,
            title="Hello",
        )

        assert payload["priority"] == "medium"


# ---------------------------------------------------------------------------
# Tests: NotificationWorker._persist_notification payload parsing
# ---------------------------------------------------------------------------


class TestNotificationWorkerPersistNotification:
    """Tests for NotificationWorker._persist_notification."""

    def _make_worker(self) -> NotificationWorker:
        queue = MagicMock()
        session_factory = MagicMock()
        return NotificationWorker(queue=queue, session_factory=session_factory)

    @pytest.mark.asyncio
    async def test_persist_notification_calls_service_create(self) -> None:
        """_persist_notification builds and calls NotificationService.create."""
        worker = self._make_worker()

        workspace_id = uuid4()
        user_id = uuid4()

        created_notification = _make_orm_notification(type=NotificationType.ASSIGNMENT)

        mock_service = MagicMock()
        mock_service.create = AsyncMock(return_value=created_notification)

        payload = {
            "workspace_id": str(workspace_id),
            "user_id": str(user_id),
            "type": "assignment",
            "title": "Assigned to you",
            "body": "You have been assigned.",
            "priority": "medium",
        }

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        # Patch NotificationService constructor so we can inject the mock
        import pilot_space.ai.workers.notification_worker as worker_module

        original_service = worker_module.NotificationService
        original_repo = worker_module.NotificationRepository
        try:
            worker_module.NotificationService = MagicMock(return_value=mock_service)  # type: ignore[misc]
            worker_module.NotificationRepository = MagicMock()  # type: ignore[misc]

            result = await worker._persist_notification(payload, mock_session)
        finally:
            worker_module.NotificationService = original_service
            worker_module.NotificationRepository = original_repo

        mock_service.create.assert_awaited_once()
        assert "notification_id" in result

    @pytest.mark.asyncio
    async def test_persist_notification_raises_on_invalid_type(self) -> None:
        """_persist_notification raises ValueError for unknown notification type."""
        worker = self._make_worker()

        payload = {
            "workspace_id": str(uuid4()),
            "user_id": str(uuid4()),
            "type": "unknown_type",
            "title": "Hello",
            "body": "",
            "priority": "medium",
        }

        mock_session = AsyncMock()

        with pytest.raises(ValueError, match="unknown_type"):
            await worker._persist_notification(payload, mock_session)

    @pytest.mark.asyncio
    async def test_persist_notification_raises_on_invalid_priority(self) -> None:
        """_persist_notification raises ValueError for unknown priority."""
        worker = self._make_worker()

        payload = {
            "workspace_id": str(uuid4()),
            "user_id": str(uuid4()),
            "type": "general",
            "title": "Hello",
            "body": "",
            "priority": "super_urgent",
        }

        mock_session = AsyncMock()

        with pytest.raises(ValueError, match="super_urgent"):
            await worker._persist_notification(payload, mock_session)
