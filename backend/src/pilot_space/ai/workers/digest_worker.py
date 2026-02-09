"""Digest worker for processing workspace digest generation jobs.

Polls the AI_LOW queue for `generate_workspace_digest` tasks and
delegates to DigestJobHandler for LLM-based suggestion generation.

References:
- specs/012-homepage-note/spec.md Background Job Specification
- US-19: Homepage Hub feature
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any

from pilot_space.infrastructure.queue.models import QueueName

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from pilot_space.infrastructure.queue.supabase_queue import SupabaseQueueClient

logger = logging.getLogger(__name__)

# Task type constant for routing
DIGEST_TASK_TYPE = "generate_workspace_digest"


class DigestWorker:
    """Worker that processes workspace digest generation jobs from AI_LOW queue.

    Simpler than ConversationWorker — no streaming, no SDK clients.
    Just dequeue → create session → call DigestJobHandler → ack/nack.
    """

    def __init__(
        self,
        queue: SupabaseQueueClient,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """Initialize digest worker.

        Args:
            queue: Supabase queue client for dequeue/ack/nack.
            session_factory: Async session factory for DB access.
        """
        self.queue = queue
        self._session_factory = session_factory
        self._running = False

    async def start(self) -> None:
        """Poll loop: dequeue → process → ack/nack."""
        self._running = True
        logger.info("DigestWorker started, polling %s queue", QueueName.AI_LOW)
        while self._running:
            try:
                messages = await self.queue.dequeue(
                    QueueName.AI_LOW, batch_size=1, visibility_timeout=120
                )
                if messages:
                    await self._process(messages[0])
                else:
                    await asyncio.sleep(5.0)
            except asyncio.CancelledError:
                logger.info("DigestWorker cancelled")
                break
            except Exception:
                logger.exception("DigestWorker poll error")
                await asyncio.sleep(5.0)

    async def stop(self) -> None:
        """Signal the worker to stop polling."""
        self._running = False

    async def _process(self, message: object) -> None:
        """Process a single digest job from the queue.

        Args:
            message: Queue message with payload containing job details.
        """
        payload: dict[str, Any] = message.payload  # type: ignore[attr-defined]
        task_type = payload.get("task_type", "")

        if task_type != DIGEST_TASK_TYPE:
            logger.debug(
                "Skipping non-digest task: %s",
                task_type,
            )
            msg_id = message.id  # type: ignore[attr-defined]
            await self.queue.nack(
                QueueName.AI_LOW,
                msg_id,
                error=f"Unknown task_type: {task_type}",
            )
            return

        workspace_id = payload.get("workspace_id", "unknown")
        logger.info(
            "Processing digest job for workspace %s",
            workspace_id,
        )

        msg_id = message.id  # type: ignore[attr-defined]
        try:
            async with self._session_factory() as session:
                from pilot_space.ai.jobs.digest_job import DigestJobHandler

                handler = DigestJobHandler(session)
                result = await handler.handle(payload)

                # Ack BEFORE commit: if commit fails, the advisory lock
                # + unique partial index prevent duplicate digests on retry.
                # If ack fails, we haven't committed yet so no data loss.
                await self.queue.ack(QueueName.AI_LOW, msg_id)

                await session.commit()

            logger.info(
                "Digest job complete: %s",
                json.dumps(result),
            )

        except Exception as e:
            logger.exception("Digest job failed for workspace %s", workspace_id)
            attempts = getattr(message, "attempts", 0)
            if attempts < 2:
                await self.queue.nack(QueueName.AI_LOW, msg_id, error=str(e))
            else:
                await self.queue.move_to_dead_letter(
                    QueueName.AI_LOW,
                    msg_id,
                    error=str(e),
                    original_payload=payload,
                )


__all__ = ["DigestWorker"]
