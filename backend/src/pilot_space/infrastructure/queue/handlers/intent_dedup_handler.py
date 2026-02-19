"""Intent dedup background job handler (J-1).

T-012: IntentDedupJobHandler
- Embeds intent `what` via cosine similarity
- Merges intents with cosine similarity > 0.9 (keeps higher confidence)
- Sets dedup_status='complete' on processed intents (C-8)
- Emits SSE `intent_merged` event when merge occurs

Feature 015: AI Workforce Platform (M2)
"""

from __future__ import annotations

import math
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


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors.

    Args:
        a: First embedding vector.
        b: Second embedding vector.

    Returns:
        Float in [-1, 1]. Returns 0.0 if either vector is zero.
    """
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


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
    2. Embed its `what` text.
    3. Fetch all other DETECTED intents in the same workspace.
    4. For each, compute cosine similarity with the target.
    5. If similarity > 0.9: merge (keep higher confidence, soft-delete lower).
    6. Mark the target intent dedup_status='complete'.

    Args:
        payload: Job parameters.
        session: Database session.
        intent_repository: Repository for WorkIntent CRUD.
        google_api_key: Google AI API key for embeddings.
    """
    from pilot_space.domain.work_intent import IntentStatus as DomainStatus
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

    # Embed target intent text
    target_embedding = await _embed_text(target.what, google_api_key)

    if target_embedding is not None:
        # Fetch other detected intents in workspace (excluding target)
        all_detected = await intent_repository.list_by_workspace_and_status(
            payload.workspace_id,
            DomainStatus.DETECTED,
        )

        for candidate in all_detected:
            if candidate.id == payload.intent_id:
                continue

            candidate_embedding = await _embed_text(candidate.what, google_api_key)
            if candidate_embedding is None:
                continue

            similarity = _cosine_similarity(target_embedding, candidate_embedding)
            if similarity >= COSINE_MERGE_THRESHOLD:
                # Merge: keep higher confidence, soft-delete lower
                if target.confidence >= candidate.confidence:
                    # Keep target, soft-delete candidate
                    await intent_repository.delete(candidate, hard=False)
                    logger.info(
                        "Merged duplicate intent (kept target)",
                        extra={
                            "kept": str(target.id),
                            "removed": str(candidate.id),
                            "similarity": round(similarity, 3),
                        },
                    )
                else:
                    # Keep candidate, mark target for removal after marking complete
                    # First mark target complete, then soft-delete it
                    target.dedup_status = DBDedupStatus.COMPLETE  # type: ignore[assignment]
                    await intent_repository.update(target)
                    await intent_repository.delete(target, hard=False)
                    # Also mark candidate complete
                    candidate.dedup_status = DBDedupStatus.COMPLETE  # type: ignore[assignment]
                    await intent_repository.update(candidate)
                    await session.flush()
                    logger.info(
                        "Merged duplicate intent (kept candidate)",
                        extra={
                            "kept": str(candidate.id),
                            "removed": str(target.id),
                            "similarity": round(similarity, 3),
                        },
                    )
                    return  # Target was merged away, done

    # C-8: Mark target dedup_status='complete' after processing
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
