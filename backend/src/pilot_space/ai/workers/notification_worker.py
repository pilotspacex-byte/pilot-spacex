"""NotificationWorker — polls NOTIFICATIONS queue and persists notifications.

T-030: Notification Worker.

Message payload format:
    {
        "workspace_id": "<uuid>",
        "user_id": "<uuid>",
        "type": "pr_review" | "assignment" | "sprint_deadline" | "mention" | "general",
        "title": "<string>",
        "body": "<string>",
        "entity_type": "<string | null>",
        "entity_id": "<uuid | null>",
        "priority": "low" | "medium" | "high" | "urgent"
    }

Follows DigestWorker / MemoryWorker pattern:
    poll → dequeue → process → ack/nack/dead-letter
Sleeps 2s on empty queue, 5s on poll error.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pilot_space.application.services.notification.notification_service import (
    NotificationService,
)
from pilot_space.infrastructure.database.models.notification import (
    NotificationPriority,
    NotificationType,
)
from pilot_space.infrastructure.database.repositories.notification_repository import (
    NotificationRepository,
)
from pilot_space.infrastructure.logging import get_logger
from pilot_space.infrastructure.queue.models import QueueName

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from pilot_space.infrastructure.queue.supabase_queue import SupabaseQueueClient

logger = get_logger(__name__)

_BATCH_SIZE = 1
_VISIBILITY_TIMEOUT_S = 60
_SLEEP_EMPTY_S = 2.0
_SLEEP_ERROR_S = 5.0
_MAX_NACK_ATTEMPTS = 2


class NotificationWorker:
    """Worker polling NOTIFICATIONS queue and persisting notification records.

    Uses one DB session per message for clean transaction boundaries.

    Args:
        queue: Supabase queue client.
        session_factory: Async session factory for per-job sessions.
    """

    def __init__(
        self,
        queue: SupabaseQueueClient,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self.queue = queue
        self._session_factory = session_factory
        self._running = False

    async def start(self) -> None:
        """Poll loop: dequeue → process → ack/nack."""
        self._running = True
        logger.info("NotificationWorker started, polling %s queue", QueueName.NOTIFICATIONS)
        while self._running:
            try:
                messages = await self.queue.dequeue(
                    QueueName.NOTIFICATIONS,
                    batch_size=_BATCH_SIZE,
                    visibility_timeout=_VISIBILITY_TIMEOUT_S,
                )
                if messages:
                    await self._process(messages[0])
                else:
                    await asyncio.sleep(_SLEEP_EMPTY_S)
            except asyncio.CancelledError:
                logger.info("NotificationWorker cancelled")
                break
            except Exception:
                logger.exception("NotificationWorker poll error")
                await asyncio.sleep(_SLEEP_ERROR_S)

    async def stop(self) -> None:
        """Signal the worker to stop polling."""
        self._running = False

    async def _process(self, message: object) -> None:
        """Process a single queue message.

        Args:
            message: Queue message with a payload dict.
        """
        payload: dict[str, Any] = message.payload  # type: ignore[attr-defined]
        msg_id = message.id  # type: ignore[attr-defined]

        try:
            async with self._session_factory() as session:
                result = await self._persist_notification(payload, session)
                await session.commit()
                await self.queue.ack(QueueName.NOTIFICATIONS, msg_id)

            logger.info(
                "notification_persisted",
                notification_id=result.get("notification_id"),
                user_id=payload.get("user_id"),
                type=payload.get("type"),
            )

        except Exception as e:
            logger.exception(
                "NotificationWorker: job failed",
                user_id=payload.get("user_id", "unknown"),
                type=payload.get("type", "unknown"),
            )
            attempts = getattr(message, "attempts", 0)
            if attempts < _MAX_NACK_ATTEMPTS:
                await self.queue.nack(QueueName.NOTIFICATIONS, msg_id, error=str(e))
            else:
                await self.queue.move_to_dead_letter(
                    QueueName.NOTIFICATIONS,
                    msg_id,
                    error=str(e),
                    original_payload=payload,
                )

    async def _persist_notification(
        self,
        payload: dict[str, Any],
        session: AsyncSession,
    ) -> dict[str, Any]:
        """Validate payload and persist notification via NotificationService.

        Args:
            payload: Raw queue message payload.
            session: DB session for this job.

        Returns:
            Dict with notification_id on success.

        Raises:
            ValueError: If required payload fields are missing or invalid.
        """
        workspace_id = UUID(payload["workspace_id"])
        user_id = UUID(payload["user_id"])
        notification_type = NotificationType(payload["type"])
        title = str(payload["title"])
        body = str(payload.get("body", ""))
        entity_type: str | None = payload.get("entity_type")
        entity_id_raw: str | None = payload.get("entity_id")
        entity_id: UUID | None = UUID(entity_id_raw) if entity_id_raw else None
        priority = NotificationPriority(payload.get("priority", NotificationPriority.MEDIUM.value))

        repo = NotificationRepository(session)
        service = NotificationService(session=session, notification_repository=repo)

        notification = await service.create(
            workspace_id=workspace_id,
            user_id=user_id,
            type=notification_type,
            title=title,
            body=body,
            entity_type=entity_type,
            entity_id=entity_id,
            priority=priority,
        )

        return {"notification_id": str(notification.id)}


def build_notification_payload(
    workspace_id: UUID,
    user_id: UUID,
    notification_type: NotificationType,
    title: str,
    body: str = "",
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    priority: NotificationPriority = NotificationPriority.MEDIUM,
) -> dict[str, Any]:
    """Build a well-typed notification queue payload.

    Helper used by callers that enqueue notifications (e.g. PR review subagent,
    issue assignment service). Returns a JSON-serialisable dict.

    Args:
        workspace_id: Target workspace UUID.
        user_id: Recipient user UUID.
        notification_type: Notification event type.
        title: Short notification title.
        body: Full notification body.
        entity_type: Optional entity kind ("issue", "pr", "note").
        entity_id: Optional entity UUID.
        priority: Notification urgency level.

    Returns:
        JSON-serialisable payload dict for the NOTIFICATIONS queue.
    """
    payload: dict[str, Any] = {
        "workspace_id": str(workspace_id),
        "user_id": str(user_id),
        "type": notification_type.value,
        "title": title,
        "body": body,
        "entity_type": entity_type,
        "entity_id": str(entity_id) if entity_id else None,
        "priority": priority.value,
    }
    return payload


__all__ = ["NotificationWorker", "build_notification_payload"]
