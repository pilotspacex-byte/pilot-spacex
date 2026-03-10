"""Supabase Queue client using pgmq pattern.

Provides async job queue operations via Supabase RPC calls for:
- AI task processing (embeddings, context generation, PR review)
- GitHub webhook handling
- Notification delivery
- Background job orchestration

Uses pgmq (Postgres Message Queue) under the hood via Supabase Edge Functions.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast
from uuid import uuid4

import httpx
import orjson

from pilot_space.infrastructure.logging import get_logger
from pilot_space.infrastructure.queue.models import (
    MessageStatus,
    QueueMessage,
    QueueName,
)

if TYPE_CHECKING:
    from uuid import UUID

logger = get_logger(__name__)

# Re-export models for backward compatibility
__all__ = [
    "MessageStatus",
    "QueueConnectionError",
    "QueueMessage",
    "QueueName",
    "QueueOperationError",
    "SupabaseQueueClient",
    "SupabaseQueueError",
]


class SupabaseQueueError(Exception):
    """Base exception for Supabase Queue errors."""


class QueueConnectionError(SupabaseQueueError):
    """Failed to connect to Supabase."""


class QueueOperationError(SupabaseQueueError):
    """Queue operation failed."""


class SupabaseQueueClient:
    """Async Supabase Queue client using pgmq via RPC.

    Provides message queue operations through Supabase Edge Functions
    or direct RPC calls to pgmq functions.

    Example:
        client = SupabaseQueueClient(
            supabase_url="https://project.supabase.co",
            service_key="your-service-key",  # pragma: allowlist secret
        )

        # Enqueue a task
        msg_id = await client.enqueue(
            QueueName.AI_TASKS,
            {"task": "generate_embeddings", "issue_id": "123"}
        )

        # Process messages
        messages = await client.dequeue(QueueName.AI_TASKS, batch_size=10)
        for msg in messages:
            try:
                await process_message(msg)
                await client.ack(QueueName.AI_TASKS, msg.id)
            except Exception as e:
                await client.nack(QueueName.AI_TASKS, msg.id, error=str(e))
    """

    def __init__(
        self,
        supabase_url: str,
        service_key: str,
        *,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """Initialize Supabase Queue client.

        Args:
            supabase_url: Supabase project URL.
            service_key: Service role key for authenticated RPC calls.
            timeout: Request timeout in seconds.
            max_retries: Maximum retries for failed requests.
        """
        self._supabase_url = supabase_url.rstrip("/")
        self._service_key = service_key
        self._timeout = timeout
        self._max_retries = max_retries
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with proper headers."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=f"{self._supabase_url}/rest/v1",
                headers={
                    "apikey": self._service_key,
                    "Authorization": f"Bearer {self._service_key}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation",
                },
                timeout=httpx.Timeout(self._timeout),
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _rpc_call(
        self,
        function_name: str,
        params: dict[str, Any],
    ) -> Any:
        """Execute Supabase RPC call.

        Args:
            function_name: Name of the Postgres function to call.
            params: Function parameters.

        Returns:
            RPC response data.

        Raises:
            QueueConnectionError: If connection fails.
            QueueOperationError: If RPC call fails.
        """
        client = await self._get_client()

        try:
            response = await client.post(
                f"/rpc/{function_name}",
                content=orjson.dumps(params),
            )
            response.raise_for_status()
            # pgmq functions that return void send 204 No Content — guard against empty body
            if not response.content:
                return None
            return response.json()
        except httpx.ConnectError as e:
            logger.exception("Failed to connect to Supabase")
            raise QueueConnectionError(f"Connection failed: {e}") from e
        except httpx.HTTPStatusError as e:
            logger.exception("RPC call %s failed: %s", function_name, e.response.text)
            raise QueueOperationError(
                f"RPC {function_name} failed: {e.response.status_code}"
            ) from e
        except httpx.RequestError as e:
            logger.exception("Request error for %s", function_name)
            raise QueueOperationError(f"Request failed: {e}") from e

    # =========================================================================
    # Core Queue Operations
    # =========================================================================

    async def enqueue(
        self,
        queue_name: str | QueueName,
        payload: dict[str, Any],
        *,
        delay_seconds: int = 0,
        max_attempts: int = 3,
    ) -> str:
        """Add a message to the queue.

        Args:
            queue_name: Target queue name.
            payload: JSON-serializable message payload.
            delay_seconds: Seconds to delay message visibility.
            max_attempts: Maximum processing attempts.

        Returns:
            Message ID for tracking.

        Raises:
            QueueOperationError: If enqueue fails.
        """
        queue = str(queue_name)
        msg_id = str(uuid4())

        # Add metadata to payload
        enriched_payload = {
            **payload,
            "_meta": {
                "msg_id": msg_id,
                "max_attempts": max_attempts,
                "enqueued_at": datetime.now(tz=UTC).isoformat(),
            },
        }

        try:
            result = await self._rpc_call(
                "pgmq_send",
                {
                    "queue_name": queue,
                    "msg": enriched_payload,
                    "delay": delay_seconds,
                },
            )
        except SupabaseQueueError:
            raise
        except Exception as e:
            logger.exception("Failed to enqueue message to %s", queue)
            raise QueueOperationError(f"Enqueue failed: {e}") from e
        else:
            # pgmq_send returns the message ID
            returned_id = str(result) if result else msg_id
            logger.info("Enqueued message %s to %s", returned_id, queue)
            return returned_id

    async def dequeue(
        self,
        queue_name: str | QueueName,
        *,
        batch_size: int = 1,
        visibility_timeout: int = 30,
    ) -> list[QueueMessage]:
        """Retrieve messages from queue for processing.

        Messages become invisible to other consumers for the visibility
        timeout duration. Must call ack() or nack() within this window.

        Args:
            queue_name: Source queue name.
            batch_size: Maximum messages to retrieve (1-100).
            visibility_timeout: Seconds until messages become visible again.

        Returns:
            List of messages (may be empty if queue is empty).

        Raises:
            QueueOperationError: If dequeue fails.
        """
        queue = str(queue_name)
        batch_size = min(max(batch_size, 1), 100)

        try:
            result = await self._rpc_call(
                "pgmq_read",
                {
                    "queue_name": queue,
                    "vt": visibility_timeout,
                    "qty": batch_size,
                },
            )
        except SupabaseQueueError:
            raise
        except Exception as e:
            logger.exception("Failed to dequeue from %s", queue)
            raise QueueOperationError(f"Dequeue failed: {e}") from e
        else:
            if not result:
                return []

            # Cast result to list - pgmq_read returns list of message dicts
            result_list = cast("list[dict[str, Any]]", result)

            messages: list[QueueMessage] = []
            for item in result_list:
                msg = QueueMessage.from_dict(
                    {
                        **item,
                        "queue_name": queue,
                        "visibility_timeout": visibility_timeout,
                    }
                )
                messages.append(msg)

            if messages:
                logger.debug("Dequeued %d messages from %s", len(messages), queue)

            return messages

    async def ack(
        self,
        queue_name: str | QueueName,
        msg_id: str,
    ) -> bool:
        """Acknowledge successful message processing.

        Removes the message from the queue permanently.

        Args:
            queue_name: Queue name.
            msg_id: Message ID to acknowledge.

        Returns:
            True if acknowledged, False if message not found.

        Raises:
            QueueOperationError: If ack fails.
        """
        queue = str(queue_name)

        try:
            result = await self._rpc_call(
                "pgmq_delete",
                {
                    "queue_name": queue,
                    "msg_id": int(msg_id) if msg_id.isdigit() else msg_id,
                },
            )
        except SupabaseQueueError:
            raise
        except Exception as e:
            logger.exception("Failed to ack message %s from %s", msg_id, queue)
            raise QueueOperationError(f"Ack failed: {e}") from e
        else:
            acknowledged = bool(result)
            if acknowledged:
                logger.debug("Acknowledged message %s from %s", msg_id, queue)
            return acknowledged

    async def nack(
        self,
        queue_name: str | QueueName,
        msg_id: str,
        *,
        error: str | None = None,
        requeue: bool = True,
        delay_seconds: int = 0,
    ) -> bool:
        """Negative acknowledge - message processing failed.

        Either requeues the message for retry or moves to dead letter queue
        if max attempts exceeded.

        Args:
            queue_name: Queue name.
            msg_id: Message ID.
            error: Error message for logging.
            requeue: Whether to requeue (True) or discard (False).
            delay_seconds: Delay before message becomes visible again.

        Returns:
            True if processed, False if message not found.

        Raises:
            QueueOperationError: If nack fails.
        """
        queue = str(queue_name)

        if error:
            logger.warning("Message %s from %s failed: %s", msg_id, queue, error)

        try:
            if requeue:
                # Archive (nack) the message - pgmq will handle visibility
                result = await self._rpc_call(
                    "pgmq_archive",
                    {
                        "queue_name": queue,
                        "msg_id": int(msg_id) if msg_id.isdigit() else msg_id,
                    },
                )
            else:
                # Delete without requeue
                result = await self._rpc_call(
                    "pgmq_delete",
                    {
                        "queue_name": queue,
                        "msg_id": int(msg_id) if msg_id.isdigit() else msg_id,
                    },
                )

            return bool(result)
        except SupabaseQueueError:
            raise
        except Exception as e:
            logger.exception("Failed to nack message %s from %s", msg_id, queue)
            raise QueueOperationError(f"Nack failed: {e}") from e

    async def move_to_dead_letter(
        self,
        queue_name: str | QueueName,
        msg_id: str,
        *,
        error: str,
        original_payload: dict[str, Any] | None = None,
    ) -> str:
        """Move failed message to dead letter queue.

        Args:
            queue_name: Original queue name.
            msg_id: Message ID.
            error: Failure reason.
            original_payload: Original message payload.

        Returns:
            Dead letter message ID.

        Raises:
            QueueOperationError: If operation fails.
        """
        dead_letter_payload = {
            "original_queue": str(queue_name),
            "original_msg_id": msg_id,
            "error": error,
            "payload": original_payload or {},
            "dead_lettered_at": datetime.now(tz=UTC).isoformat(),
        }

        # Delete from original queue
        await self._rpc_call(
            "pgmq_delete",
            {
                "queue_name": str(queue_name),
                "msg_id": int(msg_id) if msg_id.isdigit() else msg_id,
            },
        )

        # Enqueue to dead letter
        dlq_msg_id = await self.enqueue(
            QueueName.DEAD_LETTER,
            dead_letter_payload,
            max_attempts=1,  # No retries for DLQ
        )

        logger.warning(
            "Moved message %s from %s to dead letter queue as %s",
            msg_id,
            queue_name,
            dlq_msg_id,
        )
        return dlq_msg_id

    # =========================================================================
    # Queue Management
    # =========================================================================

    async def create_queue(self, queue_name: str | QueueName) -> bool:
        """Create a new queue.

        Args:
            queue_name: Name of the queue to create.

        Returns:
            True if created, False if already exists.

        Raises:
            QueueOperationError: If creation fails.
        """
        queue = str(queue_name)

        try:
            await self._rpc_call("pgmq_create", {"queue_name": queue})
            logger.info("Created queue: %s", queue)
        except QueueOperationError as e:
            if "already exists" in str(e).lower():
                logger.debug("Queue %s already exists", queue)
                return False
            raise
        else:
            return True

    async def delete_queue(self, queue_name: str | QueueName) -> bool:
        """Delete a queue and all its messages.

        Args:
            queue_name: Name of the queue to delete.

        Returns:
            True if deleted, False if not found.

        Raises:
            QueueOperationError: If deletion fails.
        """
        queue = str(queue_name)

        try:
            await self._rpc_call("pgmq_drop", {"queue_name": queue})
            logger.info("Deleted queue: %s", queue)
        except QueueOperationError as e:
            if "does not exist" in str(e).lower():
                logger.debug("Queue %s not found", queue)
                return False
            raise
        else:
            return True

    async def purge_queue(self, queue_name: str | QueueName) -> int:
        """Remove all messages from queue without deleting it.

        Args:
            queue_name: Name of the queue to purge.

        Returns:
            Number of messages purged.

        Raises:
            QueueOperationError: If purge fails.
        """
        queue = str(queue_name)

        try:
            result = await self._rpc_call("pgmq_purge", {"queue_name": queue})
            count = int(result) if result else 0
            logger.info("Purged %d messages from %s", count, queue)
        except SupabaseQueueError:
            raise
        except Exception as e:
            logger.exception("Failed to purge queue %s", queue)
            raise QueueOperationError(f"Purge failed: {e}") from e
        else:
            return count

    async def get_queue_length(self, queue_name: str | QueueName) -> int:
        """Get number of messages in queue.

        Args:
            queue_name: Queue name.

        Returns:
            Number of messages (pending + processing).

        Raises:
            QueueOperationError: If query fails.
        """
        queue = str(queue_name)

        try:
            result = await self._rpc_call(
                "pgmq_metrics",
                {"queue_name": queue},
            )
        except SupabaseQueueError:
            raise
        except Exception as e:
            logger.exception("Failed to get queue length for %s", queue)
            raise QueueOperationError(f"Get length failed: {e}") from e
        else:
            # result is list of metrics dicts from pgmq
            if result and isinstance(result, list):
                # Cast result - pgmq_metrics returns list of metric dicts
                metrics_list = cast("list[dict[str, Any]]", result)
                if len(metrics_list) > 0:
                    first_item = metrics_list[0]
                    return int(first_item.get("queue_length", 0))
            return 0

    # =========================================================================
    # Convenience Methods for Pilot Space Queues
    # =========================================================================

    async def enqueue_ai_task(
        self,
        task_type: str,
        workspace_id: str | UUID,
        payload: dict[str, Any],
        *,
        priority: str = "normal",
    ) -> str:
        """Enqueue AI processing task with priority routing.

        Args:
            task_type: Type of AI task (e.g., "generate_embeddings").
            workspace_id: Workspace ID for context.
            payload: Task-specific payload.
            priority: Priority level ("high", "normal", "low").

        Returns:
            Message ID.
        """
        queue_map = {
            "high": QueueName.AI_HIGH,
            "normal": QueueName.AI_NORMAL,
            "low": QueueName.AI_LOW,
        }
        queue = queue_map.get(priority, QueueName.AI_NORMAL)

        return await self.enqueue(
            queue,
            {
                "task_type": task_type,
                "workspace_id": str(workspace_id),
                **payload,
            },
        )

    async def enqueue_github_webhook(
        self,
        event_type: str,
        payload: dict[str, Any],
    ) -> str:
        """Enqueue GitHub webhook for processing.

        Args:
            event_type: GitHub event type (e.g., "push", "pull_request").
            payload: Webhook payload.

        Returns:
            Message ID.
        """
        return await self.enqueue(
            QueueName.GITHUB_WEBHOOKS,
            {
                "event_type": event_type,
                "payload": payload,
            },
        )

    async def enqueue_notification(
        self,
        user_id: str | UUID,
        notification_type: str,
        data: dict[str, Any],
    ) -> str:
        """Enqueue notification for delivery.

        Args:
            user_id: Target user ID.
            notification_type: Type of notification.
            data: Notification data.

        Returns:
            Message ID.
        """
        return await self.enqueue(
            QueueName.NOTIFICATIONS,
            {
                "user_id": str(user_id),
                "notification_type": notification_type,
                "data": data,
            },
        )

    async def initialize_queues(self) -> None:
        """Create all predefined queues (idempotent).

        Call during application startup to ensure queues exist.
        """
        for queue in QueueName:
            await self.create_queue(queue)
        logger.info("Initialized all Pilot Space queues")
