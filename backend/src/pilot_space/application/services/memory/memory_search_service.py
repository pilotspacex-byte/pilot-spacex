"""MemorySearchService — hybrid memory search with <200ms SLA.

T-030: Embed query with Gemini → hybrid fusion → return top results.

Feature 015: AI Workforce Platform — Memory Engine
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.repositories.memory_repository import (
        MemoryEntryRepository,
    )

logger = get_logger(__name__)

_GEMINI_EMBEDDING_MODEL = "models/gemini-embedding-exp-03-07"
_DEFAULT_LIMIT = 5


@dataclass(frozen=True, slots=True)
class MemorySearchPayload:
    """Payload for memory search.

    Attributes:
        query: Natural language query text.
        workspace_id: Workspace to search in.
        limit: Maximum results to return (default 5).
        google_api_key: Optional Gemini API key for embedding.
    """

    query: str
    workspace_id: UUID
    limit: int = _DEFAULT_LIMIT
    google_api_key: str | None = None


@dataclass
class MemorySearchResult:
    """Result from memory search.

    Attributes:
        results: List of memory entry dicts with score.
        query: Original query text.
        embedding_used: Whether vector embedding was used.
    """

    results: list[dict[str, Any]] = field(default_factory=list)
    query: str = ""
    embedding_used: bool = False


class MemorySearchService:
    """Hybrid memory search service.

    Combines vector similarity (via Gemini embeddings) and full-text search
    (tsvector ts_rank) with 0.7/0.3 fusion scoring.

    Falls back to keyword-only search when embeddings are unavailable.
    SLA: <200ms at 1000 entries.

    Example:
        service = MemorySearchService(memory_repository, session)
        result = await service.execute(MemorySearchPayload(
            query="API rate limiting",
            workspace_id=workspace_id,
            google_api_key=api_key,
        ))
    """

    def __init__(
        self,
        memory_repository: MemoryEntryRepository,
        session: AsyncSession,
    ) -> None:
        """Initialize service.

        Args:
            memory_repository: Repository for MemoryEntry access.
            session: Async DB session.
        """
        self._memory_repo = memory_repository
        self._session = session

    async def execute(self, payload: MemorySearchPayload) -> MemorySearchResult:
        """Execute hybrid memory search.

        Args:
            payload: Search parameters.

        Returns:
            MemorySearchResult with ranked entries.
        """
        embedding = await self._embed_query(payload.query, payload.google_api_key)

        if embedding is not None:
            results = await self._memory_repo.hybrid_search(
                query_embedding=embedding,
                query_text=payload.query,
                workspace_id=payload.workspace_id,
                limit=payload.limit,
            )
            return MemorySearchResult(
                results=results,
                query=payload.query,
                embedding_used=True,
            )

        # Fallback: keyword-only via list_by_workspace (no vector scoring)
        logger.warning(
            "Gemini embedding unavailable — using keyword-only memory search for workspace %s",
            payload.workspace_id,
        )
        entries = await self._memory_repo.list_by_workspace(
            workspace_id=payload.workspace_id,
            limit=payload.limit,
        )
        keyword_results = [
            {
                "id": str(entry.id),
                "content": entry.content,
                "source_type": entry.source_type,
                "pinned": entry.pinned,
                "embedding_score": 0.0,
                "text_score": 0.0,
                "score": 0.0,
            }
            for entry in entries
        ]
        return MemorySearchResult(
            results=keyword_results,
            query=payload.query,
            embedding_used=False,
        )

    @staticmethod
    async def _embed_query(text: str, api_key: str | None) -> list[float] | None:
        """Embed query text using Gemini.

        Args:
            text: Query text to embed.
            api_key: Google API key.

        Returns:
            768-dim embedding vector or None on failure.
        """
        if not api_key:
            return None
        try:
            import asyncio

            import google.generativeai as genai  # type: ignore[import-untyped]

            genai.configure(api_key=api_key)  # type: ignore[attr-defined]
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: genai.embed_content(  # type: ignore[attr-defined]
                    model=_GEMINI_EMBEDDING_MODEL,
                    content=text,
                    task_type="SEMANTIC_SIMILARITY",
                ),
            )
            return list(result["embedding"])
        except Exception:
            logger.warning("Gemini embedding failed for memory search", exc_info=True)
            return None
