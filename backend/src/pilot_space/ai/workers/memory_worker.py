"""MemoryWorker — polls ai_normal queue for memory engine jobs.

T-068: Routes by task_type:
- 'intent_dedup'              → IntentDedupJobHandler
- 'memory_embedding'          → MemoryEmbeddingJobHandler
- 'graph_embedding'           → MemoryEmbeddingJobHandler.handle_graph_node
- 'memory_dlq_reconciliation' → MemoryDLQJobHandler
- 'graph_expiration'          → expire_stale_graph_nodes
- 'kg_populate'               → KgPopulateHandler
- 'document_ingestion'        → DocumentIngestionHandler
- 'artifact_cleanup'          → run_artifact_cleanup

Follows DigestWorker pattern: poll → process → ack/nack/dead-letter.
Sleeps 2s on empty queue.

Feature 015: AI Workforce Platform — Memory Engine
Feature 016: Knowledge Graph — graph_embedding dispatch added
Feature v1.1: Artifacts — artifact_cleanup dispatch added
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import TYPE_CHECKING, Any

from pilot_space.application.services.embedding_service import EmbeddingConfig, EmbeddingService
from pilot_space.infrastructure.logging import get_logger
from pilot_space.infrastructure.queue.models import QueueName

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from pilot_space.infrastructure.queue.supabase_queue import SupabaseQueueClient
    from pilot_space.infrastructure.storage.client import SupabaseStorageClient

logger = get_logger(__name__)

# Task type constants
TASK_INTENT_DEDUP = "intent_dedup"
TASK_KG_POPULATE = "kg_populate"
TASK_MEMORY_EMBEDDING = "memory_embedding"
TASK_GRAPH_EMBEDDING = "graph_embedding"
TASK_MEMORY_DLQ = "memory_dlq_reconciliation"
TASK_GRAPH_EXPIRATION = "graph_expiration"
TASK_DOCUMENT_INGESTION = "document_ingestion"
TASK_ARTIFACT_CLEANUP = "artifact_cleanup"
TASK_SEND_INVITATION_EMAIL = "send_invitation_email"

# _BATCH_SIZE MUST remain 1: _process() handles only messages[0].
# Increasing this without updating the loop would silently drop messages 1..N.
_BATCH_SIZE = 1
_VISIBILITY_TIMEOUT_S = 120
_SLEEP_EMPTY_S = 2.0
_SLEEP_ERROR_S = 5.0
_MAX_NACK_ATTEMPTS = 2
# Enqueue a graph_expiration task at most once per day per worker process.
_EXPIRATION_INTERVAL_S = 24 * 3600
# Enqueue artifact_cleanup once per hour per worker process.
_ARTIFACT_CLEANUP_INTERVAL_S = 3600


class MemoryWorker:
    """Worker polling ai_normal queue for memory engine jobs.

    Handles intent_dedup, memory_embedding, graph_embedding,
    memory_dlq_reconciliation, graph_expiration, kg_populate,
    document_ingestion, and artifact_cleanup task types.
    Uses session per job for clean transaction boundaries.

    Args:
        queue: Supabase queue client.
        session_factory: Async session factory for per-job sessions.
        google_api_key: Optional Google API key for Gemini embedding (deprecated tables).
        openai_api_key: Optional OpenAI API key for EmbeddingService.
        ollama_base_url: Ollama base URL for EmbeddingService fallback.
        anthropic_api_key: Optional Anthropic API key for contextual chunk enrichment.
        storage_client: Optional Supabase Storage client for artifact_cleanup tasks.
    """

    def __init__(
        self,
        queue: SupabaseQueueClient,
        session_factory: async_sessionmaker[AsyncSession],
        google_api_key: str | None = None,
        openai_api_key: str | None = None,
        ollama_base_url: str = "http://localhost:11434",
        anthropic_api_key: str | None = None,
        storage_client: SupabaseStorageClient | None = None,
    ) -> None:
        self.queue = queue
        self._session_factory = session_factory
        self._google_api_key = google_api_key
        self._anthropic_api_key = anthropic_api_key
        self._storage_client = storage_client
        self._embedding_service = EmbeddingService(
            EmbeddingConfig(openai_api_key=openai_api_key, ollama_base_url=ollama_base_url)
        )
        self._running = False
        # Tracks monotonic time of last graph_expiration enqueue.
        # float('-inf') guarantees the first call always enqueues regardless of system uptime.
        # Resets on worker restart, which is acceptable — daily cleanup is best-effort.
        self._last_expiration_enqueue: float = float("-inf")
        self._last_artifact_cleanup_enqueue: float = float("-inf")

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
                    await self._maybe_enqueue_expiration()
                    await self._maybe_enqueue_artifact_cleanup()
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

    async def _maybe_enqueue_expiration(self) -> None:
        """Enqueue a graph_expiration task once per day per process lifetime."""
        now = time.monotonic()
        if now - self._last_expiration_enqueue < _EXPIRATION_INTERVAL_S:
            return
        try:
            await self.queue.enqueue(
                QueueName.AI_NORMAL,
                {"task_type": TASK_GRAPH_EXPIRATION},
            )
            self._last_expiration_enqueue = now
            logger.info("MemoryWorker: enqueued graph_expiration task")
        except Exception:
            logger.exception("MemoryWorker: failed to enqueue graph_expiration")

    async def _maybe_enqueue_artifact_cleanup(self) -> None:
        """Enqueue an artifact_cleanup task once per hour per process lifetime."""
        now = time.monotonic()
        if now - self._last_artifact_cleanup_enqueue < _ARTIFACT_CLEANUP_INTERVAL_S:
            return
        try:
            await self.queue.enqueue(
                QueueName.AI_NORMAL,
                {"task_type": TASK_ARTIFACT_CLEANUP},
            )
            self._last_artifact_cleanup_enqueue = now
            logger.info("MemoryWorker: enqueued artifact_cleanup task")
        except Exception:
            logger.exception("MemoryWorker: failed to enqueue artifact_cleanup")

    async def _process(self, message: object) -> None:
        """Process a single queue message by routing to the correct handler.

        Args:
            message: Queue message with payload dict.
        """
        payload: dict[str, Any] = message.payload  # type: ignore[attr-defined]
        task_type = payload.get("task_type", "")
        msg_id = message.id  # type: ignore[attr-defined]

        if task_type not in (
            TASK_INTENT_DEDUP,
            TASK_KG_POPULATE,
            TASK_MEMORY_EMBEDDING,
            TASK_GRAPH_EMBEDDING,
            TASK_MEMORY_DLQ,
            TASK_GRAPH_EXPIRATION,
            TASK_DOCUMENT_INGESTION,
            TASK_ARTIFACT_CLEANUP,
            TASK_SEND_INVITATION_EMAIL,
        ):
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
                await session.commit()
                await self.queue.ack(QueueName.AI_NORMAL, msg_id)

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

    async def _dispatch(  # noqa: PLR0911
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
                embedding_service=self._embedding_service,
            )
            return {"task_type": task_type, "intent_id": payload.get("intent_id")}

        if task_type in (TASK_MEMORY_EMBEDDING, TASK_GRAPH_EMBEDDING):
            from pilot_space.infrastructure.queue.handlers.memory_embedding_handler import (
                MemoryEmbeddingJobHandler,
            )

            handler = MemoryEmbeddingJobHandler(
                session,
                google_api_key=self._google_api_key,
                embedding_service=self._embedding_service,
            )
            if task_type == TASK_GRAPH_EMBEDDING:
                return await handler.handle_graph_node(payload)
            return await handler.handle(payload)

        if task_type == TASK_MEMORY_DLQ:
            from pilot_space.infrastructure.queue.handlers.memory_dlq_handler import (
                MemoryDLQJobHandler,
            )

            handler = MemoryDLQJobHandler(session, self.queue)
            return await handler.handle(payload)

        if task_type == TASK_GRAPH_EXPIRATION:
            from pilot_space.infrastructure.jobs.expire_graph_nodes import expire_stale_graph_nodes

            count = await expire_stale_graph_nodes(session)
            return {"task_type": task_type, "expired_count": count}

        if task_type in (TASK_KG_POPULATE, TASK_DOCUMENT_INGESTION):
            # Both handlers share the same constructor signature — select by task_type.
            if task_type == TASK_KG_POPULATE:
                from pilot_space.infrastructure.queue.handlers.kg_populate_handler import (
                    KgPopulateHandler as _Handler,
                )
            else:
                from pilot_space.infrastructure.queue.handlers.document_ingestion_handler import (  # type: ignore[assignment]
                    DocumentIngestionHandler as _Handler,
                )
            handler = _Handler(  # type: ignore[call-arg]
                session,
                self._embedding_service,
                self.queue,
                anthropic_api_key=self._anthropic_api_key,
            )
            return await handler.handle(payload)

        if task_type == TASK_ARTIFACT_CLEANUP:
            from pilot_space.infrastructure.jobs.artifact_cleanup import run_artifact_cleanup

            if self._storage_client is None:
                logger.warning(
                    "MemoryWorker: TASK_ARTIFACT_CLEANUP skipped — storage_client not configured"
                )
                return {"task_type": task_type, "deleted_count": 0, "skipped": True}
            count = await run_artifact_cleanup(session, self._storage_client)
            return {"task_type": task_type, "deleted_count": count}

        if task_type == TASK_SEND_INVITATION_EMAIL:
            from pilot_space.infrastructure.queue.handlers.invitation_email_handler import (
                send_invitation_email,
            )

            await send_invitation_email(payload)
            return {"task_type": task_type, "invitation_id": payload.get("invitation_id")}

        raise AssertionError(f"Unreachable: _dispatch called with unknown task_type {task_type!r}")


__all__ = ["TASK_DOCUMENT_INGESTION", "MemoryWorker"]
