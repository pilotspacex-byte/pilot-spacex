"""MemorySaveService — synchronous persist + async embedding enqueue.

T-031: Persists content + keywords synchronously (keyword search works immediately).
Enqueues memory_embedding job (J-3) to ai_normal queue.
On embedding failure after 3 retries → DLQ (FR-112).

Feature 015: AI Workforce Platform — Memory Engine
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pilot_space.domain.memory_entry import MemoryEntry, MemorySourceType
from pilot_space.infrastructure.logging import get_logger
from pilot_space.infrastructure.queue.models import QueueName

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.repositories.memory_repository import (
        MemoryEntryRepository,
    )
    from pilot_space.infrastructure.queue.supabase_queue import SupabaseQueueClient

logger = get_logger(__name__)

_MEMORY_EMBEDDING_TASK_TYPE = "memory_embedding"
_MEMORY_TABLE = "memory_entries"


@dataclass(frozen=True, slots=True)
class MemorySavePayload:
    """Payload for saving a memory entry.

    Attributes:
        workspace_id: Owning workspace.
        content: Memory text content.
        source_type: What generated this memory.
        source_id: Optional UUID of originating entity.
        pinned: Pin to prevent TTL expiry.
        expires_at: Optional expiry timestamp.
    """

    workspace_id: UUID
    content: str
    source_type: MemorySourceType
    actor_user_id: UUID
    source_id: UUID | None = None
    pinned: bool = False
    expires_at: datetime | None = None


@dataclass
class MemorySaveResult:
    """Result of saving a memory entry.

    Attributes:
        entry_id: UUID of the saved memory entry.
        keywords: Extracted keywords persisted synchronously.
        embedding_enqueued: Whether embedding job was enqueued.
    """

    entry_id: UUID
    keywords: list[str]
    embedding_enqueued: bool


class MemorySaveService:
    """Service to persist memory entries with async embedding.

    Synchronously saves content + keywords so keyword search works immediately.
    Asynchronously enqueues embedding generation to the ai_normal queue.
    Callers get MemorySaveResult back instantly; embedding arrives later.

    Example:
        service = MemorySaveService(memory_repository, queue_client, session)
        result = await service.execute(MemorySavePayload(
            workspace_id=workspace_id,
            content="User prefers concise code reviews",
            source_type=MemorySourceType.USER_FEEDBACK,
        ))
    """

    def __init__(
        self,
        memory_repository: MemoryEntryRepository,
        queue: SupabaseQueueClient,
        session: AsyncSession,
    ) -> None:
        """Initialize service.

        Args:
            memory_repository: Repository for MemoryEntry persistence.
            queue: Queue client for enqueuing embedding job.
            session: Async DB session.
        """
        self._memory_repo = memory_repository
        self._queue = queue
        self._session = session

    async def execute(self, payload: MemorySavePayload) -> MemorySaveResult:
        """Persist memory entry and enqueue embedding generation.

        Args:
            payload: Memory content and metadata.

        Returns:
            MemorySaveResult with entry_id and embedding_enqueued flag.
        """
        # Build domain entity for keyword extraction
        domain_entry = MemoryEntry(
            workspace_id=payload.workspace_id,
            content=payload.content,
            source_type=payload.source_type,
            source_id=payload.source_id,
            pinned=payload.pinned,
            expires_at=payload.expires_at,
        )

        # Persist synchronously using to_tsvector so full-text search works immediately
        created = await self._memory_repo.create_with_keywords(
            workspace_id=payload.workspace_id,
            content=payload.content,
            keywords=domain_entry.keywords or [],
            source_type=payload.source_type,
            source_id=payload.source_id,
            pinned=payload.pinned,
            expires_at=payload.expires_at,
        )
        await self._session.commit()

        entry_id = created.id  # type: ignore[assignment]

        # Enqueue embedding generation (J-3) — fire and forget
        enqueued = await self._enqueue_embedding(entry_id, payload.workspace_id, payload.actor_user_id)

        logger.info(
            "MemorySaveService: persisted entry %s for workspace %s (embedding_enqueued=%s)",
            entry_id,
            payload.workspace_id,
            enqueued,
        )

        return MemorySaveResult(
            entry_id=entry_id,
            keywords=domain_entry.keywords or [],
            embedding_enqueued=enqueued,
        )

    async def _enqueue_embedding(
        self, entry_id: UUID, workspace_id: UUID, actor_user_id: UUID
    ) -> bool:
        """Enqueue memory embedding job to ai_normal queue.

        Args:
            entry_id: MemoryEntry UUID to embed.
            workspace_id: Workspace for context.
            actor_user_id: Acting user id for RLS context.

        Returns:
            True if enqueued successfully, False on failure.
        """
        job_payload: dict[str, Any] = {
            "task_type": _MEMORY_EMBEDDING_TASK_TYPE,
            "entry_id": str(entry_id),
            "workspace_id": str(workspace_id),
            "actor_user_id": str(actor_user_id),
            "table": _MEMORY_TABLE,
            "enqueued_at": datetime.now(tz=UTC).isoformat(),
        }
        try:
            await self._queue.enqueue(QueueName.AI_NORMAL, job_payload)
            return True
        except Exception:
            logger.error(
                "Failed to enqueue memory embedding for entry %s",
                entry_id,
                exc_info=True,
            )
            return False
