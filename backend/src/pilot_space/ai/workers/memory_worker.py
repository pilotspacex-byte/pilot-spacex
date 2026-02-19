"""MemoryWorker — polls ai_normal queue for memory engine jobs.

T-068: Routes by task_type:
- 'intent_dedup'              → IntentDedupJobHandler
- 'memory_embedding'          → MemoryEmbeddingJobHandler
- 'memory_dlq_reconciliation' → MemoryDLQJobHandler

Follows DigestWorker pattern: poll → process → ack/nack/dead-letter.
Sleeps 2s on empty queue.

Feature 015: AI Workforce Platform — Memory Engine
"""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any

from pilot_space.infrastructure.logging import get_logger
from pilot_space.infrastructure.queue.models import QueueName

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from pilot_space.infrastructure.queue.supabase_queue import SupabaseQueueClient

logger = get_logger(__name__)

# Task type constants
TASK_INTENT_DEDUP = "intent_dedup"
TASK_MEMORY_EMBEDDING = "memory_embedding"
TASK_MEMORY_DLQ = "memory_dlq_reconciliation"

_BATCH_SIZE = 1
_VISIBILITY_TIMEOUT_S = 120
_SLEEP_EMPTY_S = 2.0
_SLEEP_ERROR_S = 5.0
_MAX_NACK_ATTEMPTS = 2


class MemoryWorker:
    """Worker polling ai_normal queue for memory engine jobs.

    Handles intent_dedup, memory_embedding, and memory_dlq_reconciliation
    task types. Uses session per job for clean transaction boundaries.

    Args:
        queue: Supabase queue client.
        session_factory: Async session factory for per-job sessions.
        google_api_key: Optional Google API key for Gemini embedding.
    """

    def __init__(
        self,
        queue: SupabaseQueueClient,
        session_factory: async_sessionmaker[AsyncSession],
        google_api_key: str | None = None,
    ) -> None:
        self.queue = queue
        self._session_factory = session_factory
        self._google_api_key = google_api_key
        self._running = False

    async def start(self) -> None:
        """Poll loop: dequeue → process → ack/nack."""
        self._running = True
        logger.info("MemoryWorker started, polling %s queue", QueueName.AI_NORMAL)
        while self._running:
            try:
                messages = await self.queue.dequeue(
                    QueueName.AI_NORMAL,
                    batch_size=_BATCH_SIZE,
                    visibility_timeout=_VISIBILITY_TIMEOUT_S,
                )
                if messages:
                    await self._process(messages[0])
                else:
                    await asyncio.sleep(_SLEEP_EMPTY_S)
            except asyncio.CancelledError:
                logger.info("MemoryWorker cancelled")
                break
            except Exception:
                logger.exception("MemoryWorker poll error")
                await asyncio.sleep(_SLEEP_ERROR_S)

    async def stop(self) -> None:
        """Signal the worker to stop polling."""
        self._running = False

    async def _process(self, message: object) -> None:
        """Process a single queue message by routing to the correct handler.

        Args:
            message: Queue message with payload dict.
        """
        payload: dict[str, Any] = message.payload  # type: ignore[attr-defined]
        task_type = payload.get("task_type", "")
        msg_id = message.id  # type: ignore[attr-defined]

        if task_type not in (TASK_INTENT_DEDUP, TASK_MEMORY_EMBEDDING, TASK_MEMORY_DLQ):
            logger.debug("MemoryWorker: skipping unknown task_type %s", task_type)
            await self.queue.nack(
                QueueName.AI_NORMAL,
                msg_id,
                error=f"Unknown task_type: {task_type}",
            )
            return

        workspace_id = payload.get("workspace_id", "unknown")
        logger.info(
            "MemoryWorker: processing %s for workspace %s",
            task_type,
            workspace_id,
        )

        try:
            async with self._session_factory() as session:
                result = await self._dispatch(task_type, payload, session)
                await self.queue.ack(QueueName.AI_NORMAL, msg_id)
                await session.commit()

            logger.info("MemoryWorker: completed %s: %s", task_type, json.dumps(result))

        except Exception as e:
            logger.exception(
                "MemoryWorker: job failed for task_type=%s workspace=%s",
                task_type,
                workspace_id,
            )
            attempts = getattr(message, "attempts", 0)
            if attempts < _MAX_NACK_ATTEMPTS:
                await self.queue.nack(QueueName.AI_NORMAL, msg_id, error=str(e))
            else:
                await self.queue.move_to_dead_letter(
                    QueueName.AI_NORMAL,
                    msg_id,
                    error=str(e),
                    original_payload=payload,
                )

    async def _dispatch(
        self,
        task_type: str,
        payload: dict[str, Any],
        session: AsyncSession,
    ) -> dict[str, Any]:
        """Route payload to the appropriate handler.

        Args:
            task_type: Job type string.
            payload: Queue message payload.
            session: DB session for this job.

        Returns:
            Handler result dict.
        """
        if task_type == TASK_INTENT_DEDUP:
            from pilot_space.infrastructure.database.repositories.intent_repository import (
                WorkIntentRepository,
            )
            from pilot_space.infrastructure.queue.handlers.intent_dedup_handler import (
                IntentDedupJobPayload,
                process_intent_dedup,
            )

            intent_repo = WorkIntentRepository(session)
            job_payload = IntentDedupJobPayload.from_dict(payload)
            await process_intent_dedup(
                job_payload,
                session,
                intent_repo,
                google_api_key=self._google_api_key,
            )
            return {"task_type": task_type, "intent_id": payload.get("intent_id")}

        if task_type == TASK_MEMORY_EMBEDDING:
            from pilot_space.infrastructure.queue.handlers.memory_embedding_handler import (
                MemoryEmbeddingJobHandler,
            )

            handler = MemoryEmbeddingJobHandler(session, self._google_api_key)
            return await handler.handle(payload)

        if task_type == TASK_MEMORY_DLQ:
            from pilot_space.infrastructure.queue.handlers.memory_dlq_handler import (
                MemoryDLQJobHandler,
            )

            handler = MemoryDLQJobHandler(session, self.queue)
            return await handler.handle(payload)

        return {}  # unreachable — guarded in _process


__all__ = ["MemoryWorker"]
