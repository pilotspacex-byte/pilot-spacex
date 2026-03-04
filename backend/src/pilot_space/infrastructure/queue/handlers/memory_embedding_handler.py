"""MemoryEmbeddingJobHandler — embed memory entries, constitution rules, and graph nodes.

T-067: Handles 'memory_embedding' task_type for memory_entries and
constitution_rules tables via Gemini 768-dim embeddings.

Feature 016: Also handles 'graph_embedding' task_type for graph_nodes table
via OpenAI text-embedding-3-large (1536-dim).

Feature 015: AI Workforce Platform — Memory Engine
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import text

from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

_GEMINI_EMBEDDING_MODEL = "models/gemini-embedding-exp-03-07"
_OPENAI_EMBEDDING_MODEL = "text-embedding-3-large"
_OLLAMA_EMBEDDING_MODEL = "nomic-embed-text-v2-moe"
_OLLAMA_BASE_URL = "http://localhost:11434"
_MEMORY_TABLE = "memory_entries"
_CONSTITUTION_TABLE = "constitution_rules"
_GRAPH_NODES_TABLE = "graph_nodes"
_GRAPH_EMBEDDING_DIMS = 768


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


async def _embed_text_openai(content: str, api_key: str | None) -> list[float] | None:
    """Embed text via OpenAI text-embedding-3-large (768-dim, truncated).

    Args:
        content: Text to embed.
        api_key: OpenAI API key.

    Returns:
        768-dim float list or None on failure.
    """
    if not api_key:
        return None
    try:
        from openai import AsyncOpenAI  # type: ignore[import-untyped]

        client = AsyncOpenAI(api_key=api_key)
        response = await client.embeddings.create(
            model=_OPENAI_EMBEDDING_MODEL,
            input=content,
            dimensions=_GRAPH_EMBEDDING_DIMS,
        )
        embedding: list[float] = response.data[0].embedding
        return embedding
    except Exception:
        logger.warning(
            "OpenAI embedding failed in MemoryEmbeddingJobHandler",
            exc_info=True,
        )
        return None


def _ollama_embed_sync(content: str, base_url: str) -> list[float] | None:
    """Synchronous Ollama embed call — run inside asyncio.to_thread."""
    import json
    import urllib.request

    payload = json.dumps({"model": _OLLAMA_EMBEDDING_MODEL, "input": content}).encode()
    req = urllib.request.Request(
        f"{base_url}/api/embed",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read())
    embeddings = body.get("embeddings")
    return list(embeddings[0]) if embeddings else None


async def _embed_text_ollama(content: str, base_url: str = _OLLAMA_BASE_URL) -> list[float] | None:
    """Embed text via Ollama nomic-embed-text-v2-moe (768-dim, local).

    Args:
        content: Text to embed.
        base_url: Ollama API base URL (default: http://localhost:11434).

    Returns:
        768-dim float list or None on failure.
    """
    try:
        return await asyncio.to_thread(_ollama_embed_sync, content, base_url)
    except Exception:
        logger.warning("Ollama embedding failed in MemoryEmbeddingJobHandler", exc_info=True)
        return None


class MemoryEmbeddingJobHandler:
    """Handles memory and graph embedding jobs from the ai_normal queue.

    Routes by payload type:
    - payload['table'] in {memory_entries, constitution_rules}: embed via Gemini (768-dim)
    - handle_graph_node(payload): embed graph_nodes row (768-dim).
      Provider priority: OpenAI → Ollama local (nomic-embed-text-v2-moe).

    Args:
        session: Async DB session.
        google_api_key: Google AI API key for Gemini embeddings.
        openai_api_key: OpenAI API key for graph node embeddings (optional;
            falls back to Ollama when absent).
        ollama_base_url: Ollama API base URL for local embeddings.
    """

    def __init__(
        self,
        session: AsyncSession,
        google_api_key: str | None = None,
        openai_api_key: str | None = None,
        ollama_base_url: str = _OLLAMA_BASE_URL,
    ) -> None:
        self._session = session
        self._api_key = google_api_key
        self._openai_api_key = openai_api_key
        self._ollama_base_url = ollama_base_url

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

    async def handle_graph_node(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Embed a graph node (768-dim).

        Provider priority:
          1. OpenAI text-embedding-3-large (if openai_api_key is set)
          2. Ollama nomic-embed-text-v2-moe (local fallback)

        Args:
            payload: Queue message payload with node_id and workspace_id.

        Returns:
            Result dict with success status and node_id.
        """
        node_id_str = payload.get("node_id")
        workspace_id_str = payload.get("workspace_id")

        if not node_id_str:
            return {"success": False, "error": "missing node_id"}
        if not workspace_id_str:
            return {"success": False, "error": "missing workspace_id"}

        node_id = UUID(node_id_str)
        workspace_id = UUID(workspace_id_str)

        # Fetch node content from graph_nodes table
        content = await self._fetch_graph_node_content(node_id, workspace_id)
        if content is None:
            logger.warning(
                "MemoryEmbeddingJobHandler: graph node %s not found in workspace %s",
                node_id,
                workspace_id,
            )
            return {
                "success": False,
                "error": f"graph node {node_id} not found",
            }

        # Provider priority: OpenAI → Ollama local
        embedding: list[float] | None = None
        provider = "none"
        if self._openai_api_key:
            embedding = await _embed_text_openai(content, self._openai_api_key)
            provider = "openai"
        if embedding is None:
            embedding = await _embed_text_ollama(content, self._ollama_base_url)
            provider = "ollama"
        if embedding is None:
            return {
                "success": False,
                "error": "all embedding providers failed (OpenAI + Ollama)",
            }

        # Store embedding back to graph_nodes
        embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
        await self._store_graph_node_embedding(node_id, embedding_str)
        await self._session.commit()

        logger.info(
            "MemoryEmbeddingJobHandler: embedded graph node %s via %s (%d dims)",
            node_id,
            provider,
            len(embedding),
        )
        return {
            "success": True,
            "node_id": str(node_id),
            "workspace_id": str(workspace_id),
            "dims": len(embedding),
            "provider": provider,
        }

    async def _fetch_content(self, entry_id: UUID, table: str) -> str | None:
        """Fetch text content for memory/constitution embedding.

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

    async def _fetch_graph_node_content(self, node_id: UUID, workspace_id: UUID) -> str | None:
        """Fetch content from the graph_nodes table for embedding.

        Args:
            node_id: Graph node UUID.
            workspace_id: Owning workspace UUID (used for RLS-safe filtering).

        Returns:
            Content text or None if not found.
        """
        query = text(
            "SELECT content FROM graph_nodes "
            "WHERE id = :id AND workspace_id = :workspace_id AND is_deleted = false"
        )
        result = await self._session.execute(
            query,
            {"id": str(node_id), "workspace_id": str(workspace_id)},
        )
        row = result.first()
        return row[0] if row else None

    _ALLOWED_TABLES: frozenset[str] = frozenset({_MEMORY_TABLE, _CONSTITUTION_TABLE})

    async def _store_embedding(
        self,
        entry_id: UUID,
        table: str,
        embedding_str: str,
    ) -> None:
        """Store vector embedding in a memory/constitution table.

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

    async def _store_graph_node_embedding(
        self,
        node_id: UUID,
        embedding_str: str,
    ) -> None:
        """Store 768-dim vector embedding in graph_nodes table.

        Args:
            node_id: Graph node UUID.
            embedding_str: Embedding as '[0.1,0.2,...]' string.
        """
        update_sql = text(
            "UPDATE graph_nodes "
            f"SET embedding = CAST(:emb AS vector({_GRAPH_EMBEDDING_DIMS})) "
            "WHERE id = :id"
        )
        await self._session.execute(
            update_sql,
            {"emb": embedding_str, "id": str(node_id)},
        )
