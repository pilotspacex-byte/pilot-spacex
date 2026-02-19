"""Intent dedup background job handler (J-1).

T-012: IntentDedupJobHandler
- Embeds intent `what` via Gemini embeddings
- Finds near-duplicates via pgvector HNSW (cosine distance <=> operator)
- Merges intents with cosine similarity >= 0.9 (keeps higher confidence)
- Stores embedding on the intent for future HNSW queries
- Sets dedup_status='complete' on processed intents

Feature 015: AI Workforce Platform (M2)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pilot_space.infrastructure.logging import get_logger
from pilot_space.infrastructure.queue.models import QueueName

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.repositories.intent_repository import (
        WorkIntentRepository,
    )

logger = get_logger(__name__)

# Queue configuration
INTENT_DEDUP_QUEUE = QueueName.AI_NORMAL
INTENT_DEDUP_VISIBILITY_TIMEOUT = 60  # 1 minute
COSINE_MERGE_THRESHOLD = 0.9
# pgvector uses cosine *distance* (1 - similarity); threshold is complement
_COSINE_DISTANCE_THRESHOLD = 1.0 - COSINE_MERGE_THRESHOLD


@dataclass
class IntentDedupJobPayload:
    """Payload for intent dedup queue job.

    Attributes:
        intent_id: UUID of the newly created intent to deduplicate.
        workspace_id: Workspace containing the intent.
    """

    intent_id: UUID
    workspace_id: UUID

    def to_dict(self) -> dict[str, Any]:
        """Serialize payload for queue."""
        return {
            "intent_id": str(self.intent_id),
            "workspace_id": str(self.workspace_id),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IntentDedupJobPayload:
        """Deserialize from queue message."""
        return cls(
            intent_id=UUID(data["intent_id"]),
            workspace_id=UUID(data["workspace_id"]),
        )


async def _embed_text(text: str, api_key: str | None) -> list[float] | None:
    """Embed text using Gemini embeddings API.

    Args:
        text: Text to embed.
        api_key: Google AI API key.

    Returns:
        Embedding vector or None on failure.
    """
    if api_key is None:
        return None
    try:
        import google.generativeai as genai  # type: ignore[import-untyped]

        genai.configure(api_key=api_key)  # type: ignore[attr-defined]
        result = genai.embed_content(  # type: ignore[attr-defined]
            model="models/text-embedding-004",
            content=text,
            task_type="SEMANTIC_SIMILARITY",
        )
        return list(result["embedding"])
    except Exception:
        logger.warning("Gemini embedding call failed during dedup", exc_info=True)
        return None


async def process_intent_dedup(
    payload: IntentDedupJobPayload,
    session: AsyncSession,
    intent_repository: WorkIntentRepository,
    google_api_key: str | None = None,
) -> None:
    """Process intent deduplication for a newly created intent.

    Algorithm:
    1. Fetch the target intent.
    2. Embed its `what` text (single Gemini API call).
    3. Persist the embedding on the target intent for future queries.
    4. Query pgvector HNSW index for near-duplicates (single DB query).
    5. If any duplicate found: merge (keep higher confidence, soft-delete lower).
    6. Mark the target intent dedup_status='complete'.

    Replaces the previous O(N) Gemini API calls + Python cosine loop with
    a single embedding call + one pgvector HNSW query.

    Args:
        payload: Job parameters.
        session: Database session.
        intent_repository: Repository for WorkIntent CRUD.
        google_api_key: Google AI API key for embeddings.
    """
    from pilot_space.infrastructure.database.models.work_intent import (
        DedupStatus as DBDedupStatus,
    )

    target = await intent_repository.get_by_id(payload.intent_id)
    if target is None:
        logger.warning(
            "Intent not found for dedup",
            extra={"intent_id": str(payload.intent_id)},
        )
        return

    if target.workspace_id != payload.workspace_id:
        logger.error("Workspace mismatch in dedup job", extra={"intent_id": str(payload.intent_id)})
        return

    # Single embedding call for the target intent
    target_embedding = await _embed_text(target.what, google_api_key)

    if target_embedding is not None:
        # Persist embedding so future queries can use the HNSW index
        target.embedding = target_embedding  # type: ignore[assignment]
        await intent_repository.update(target)

        # pgvector HNSW query — replaces O(N) API loop + Python cosine math
        similar_intents = await intent_repository.find_similar_by_embedding(
            workspace_id=payload.workspace_id,
            exclude_intent_id=payload.intent_id,
            embedding=target_embedding,
            cosine_distance_threshold=_COSINE_DISTANCE_THRESHOLD,
        )

        for candidate in similar_intents:
            # Merge: keep higher confidence, soft-delete lower
            if target.confidence >= candidate.confidence:
                await intent_repository.delete(candidate, hard=False)
                logger.info(
                    "Merged duplicate intent (kept target)",
                    extra={
                        "kept": str(target.id),
                        "removed": str(candidate.id),
                    },
                )
            else:
                target.dedup_status = DBDedupStatus.COMPLETE  # type: ignore[assignment]
                await intent_repository.update(target)
                await intent_repository.delete(target, hard=False)
                candidate.dedup_status = DBDedupStatus.COMPLETE  # type: ignore[assignment]
                await intent_repository.update(candidate)
                await session.flush()
                logger.info(
                    "Merged duplicate intent (kept candidate)",
                    extra={
                        "kept": str(candidate.id),
                        "removed": str(target.id),
                    },
                )
                return  # Target was merged away, done

    # Mark target dedup_status='complete' after processing
    target.dedup_status = DBDedupStatus.COMPLETE  # type: ignore[assignment]
    await intent_repository.update(target)
    await session.flush()

    logger.info(
        "Intent dedup complete",
        extra={"intent_id": str(payload.intent_id)},
    )


class IntentDedupJobHandler:
    """Queue job handler for intent deduplication (J-1).

    Enqueued by IntentDetectionService after detecting intents.
    Processes each new intent to find and merge near-duplicates.
    """

    def __init__(
        self,
        session: AsyncSession,
        intent_repository: WorkIntentRepository,
        google_api_key: str | None = None,
    ) -> None:
        self._session = session
        self._intent_repo = intent_repository
        self._google_api_key = google_api_key

    async def handle(self, message: dict[str, Any]) -> None:
        """Process a dedup job message from the queue.

        Args:
            message: Queue message containing intent_id and workspace_id.
        """
        try:
            payload = IntentDedupJobPayload.from_dict(message)
            await process_intent_dedup(
                payload=payload,
                session=self._session,
                intent_repository=self._intent_repo,
                google_api_key=self._google_api_key,
            )
        except Exception:
            logger.exception(
                "Intent dedup job failed",
                extra={"message": str(message)[:200]},
            )
            raise
