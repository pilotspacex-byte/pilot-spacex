"""MemoryEmbeddingJobHandler — embed memory entries and constitution rules.

T-067: Handles both 'memory_embedding' task_type for memory_entries
and constitution_rules tables. Embeds via Gemini 768-dim.
Updates row embedding column. On constitution rules: active flag stays True.

Feature 015: AI Workforce Platform — Memory Engine
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import text

from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

_GEMINI_EMBEDDING_MODEL = "models/gemini-embedding-exp-03-07"
_MEMORY_TABLE = "memory_entries"
_CONSTITUTION_TABLE = "constitution_rules"


async def _embed_text(content: str, api_key: str | None) -> list[float] | None:
    """Embed text via Gemini gemini-embedding-exp-03-07 (768-dim).

    Args:
        content: Text to embed.
        api_key: Google AI API key.

    Returns:
        768-dim float list or None on failure.
    """
    if not api_key:
        return None
    try:
        import google.generativeai as genai  # type: ignore[import-untyped]

        genai.configure(api_key=api_key)  # type: ignore[attr-defined]
        result = genai.embed_content(  # type: ignore[attr-defined]
            model=_GEMINI_EMBEDDING_MODEL,
            content=content,
            task_type="SEMANTIC_SIMILARITY",
        )
        return list(result["embedding"])
    except Exception:
        logger.warning("Gemini embedding failed in MemoryEmbeddingJobHandler", exc_info=True)
        return None


class MemoryEmbeddingJobHandler:
    """Handles memory embedding jobs from the ai_normal queue.

    Routes by payload['table']:
    - memory_entries: embed and store vector in embedding column
    - constitution_rules: embed and store vector in embedding column

    Args:
        session: Async DB session.
        google_api_key: Google AI API key for Gemini.
    """

    def __init__(self, session: AsyncSession, google_api_key: str | None = None) -> None:
        self._session = session
        self._api_key = google_api_key

    async def handle(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Process a memory embedding job.

        Args:
            payload: Queue message payload with entry_id, workspace_id, table.

        Returns:
            Result dict with success status and entry_id.
        """
        entry_id_str = payload.get("entry_id")
        table = payload.get("table", _MEMORY_TABLE)

        if not entry_id_str:
            return {"success": False, "error": "missing entry_id"}

        entry_id = UUID(entry_id_str)

        # Fetch content from appropriate table
        content = await self._fetch_content(entry_id, table)
        if content is None:
            logger.warning(
                "MemoryEmbeddingJobHandler: entry %s not found in %s",
                entry_id,
                table,
            )
            return {"success": False, "error": f"entry {entry_id} not found in {table}"}

        # Generate embedding
        embedding = await _embed_text(content, self._api_key)
        if embedding is None:
            return {"success": False, "error": "embedding generation failed"}

        # Store embedding
        embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
        await self._store_embedding(entry_id, table, embedding_str)
        await self._session.commit()

        logger.info(
            "MemoryEmbeddingJobHandler: embedded entry %s in %s (%d dims)",
            entry_id,
            table,
            len(embedding),
        )
        return {"success": True, "entry_id": str(entry_id), "table": table}

    async def _fetch_content(self, entry_id: UUID, table: str) -> str | None:
        """Fetch text content for embedding.

        Args:
            entry_id: Record UUID.
            table: Table name (memory_entries or constitution_rules).

        Returns:
            Content text or None if not found.
        """
        if table not in (_MEMORY_TABLE, _CONSTITUTION_TABLE):
            logger.error("Unknown table for memory embedding: %s", table)
            return None

        query = text(f"SELECT content FROM {table} WHERE id = :id AND is_deleted = false")
        result = await self._session.execute(query, {"id": str(entry_id)})
        row = result.first()
        return row[0] if row else None

    _ALLOWED_TABLES: frozenset[str] = frozenset({_MEMORY_TABLE, _CONSTITUTION_TABLE})

    async def _store_embedding(
        self,
        entry_id: UUID,
        table: str,
        embedding_str: str,
    ) -> None:
        """Store vector embedding in the table.

        Args:
            entry_id: Record UUID.
            table: Table name.
            embedding_str: Embedding as '[0.1,0.2,...]' string.
        """
        if table not in self._ALLOWED_TABLES:
            raise ValueError(f"Disallowed table: {table!r}")
        update_sql = text(
            f"UPDATE {table} SET embedding = CAST(:embedding AS vector(768)) WHERE id = :id"
        )
        await self._session.execute(
            update_sql,
            {"embedding": embedding_str, "id": str(entry_id)},
        )
