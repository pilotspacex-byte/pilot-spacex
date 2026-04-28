"""Unified EmbeddingService — single source of truth for 768-dim text embeddings.

Consolidates 6 scattered embedding call sites into one service with a
provider cascade: LLMGateway (OpenAI via LiteLLM) → Ollama nomic-embed-text-v2-moe.

Feature 016: Knowledge Graph — Memory Engine
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from pilot_space.infrastructure.database.repositories._graph_helpers import GRAPH_EMBEDDING_DIMS
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from pilot_space.ai.proxy.llm_gateway import LLMGateway

logger = get_logger(__name__)

_OLLAMA_MODEL = "nomic-embed-text:latest"
_OLLAMA_TIMEOUT_S = 30


@dataclass(frozen=True, slots=True)
class EmbeddingConfig:
    """Configuration for EmbeddingService.

    Attributes:
        openai_api_key: Deprecated — ignored when llm_gateway is provided.
            Retained for backward compatibility with existing callers.
        ollama_base_url: Ollama API base URL.
        dimensions: Embedding vector size (authoritative constant: 768).
    """

    openai_api_key: str | None = None  # Deprecated: use llm_gateway instead
    ollama_base_url: str = "http://localhost:11434"
    dimensions: int = GRAPH_EMBEDDING_DIMS


class EmbeddingService:
    """Provider-cascading embedding service (LLMGateway → Ollama).

    Returns 768-dim float list or None when all providers fail.
    Never raises — failures are logged as warnings.

    Example:
        svc = EmbeddingService(config, llm_gateway=gateway)
        vector = await svc.embed("rate limiting design", workspace_id=ws_id, user_id=uid)
    """

    def __init__(
        self,
        config: EmbeddingConfig,
        llm_gateway: LLMGateway | None = None,
    ) -> None:
        self._config = config
        self._llm_gateway = llm_gateway

    async def embed(
        self,
        text: str,
        workspace_id: UUID | None = None,
        user_id: UUID | None = None,
    ) -> list[float] | None:
        """Embed text using LLMGateway then Ollama as fallback.

        Args:
            text: Text to embed. Returns None for empty/whitespace-only input.
            workspace_id: Workspace UUID for BYOK key lookup.
            user_id: User UUID for cost attribution.

        Returns:
            768-dim float list or None on failure.
        """
        if not text or not text.strip():
            return None

        if self._llm_gateway is not None and workspace_id is not None:
            result = await self._embed_via_gateway(text, workspace_id, user_id)
            if result is not None:
                return result

        return await self._embed_ollama(text)

    async def _embed_via_gateway(
        self,
        text: str,
        workspace_id: UUID,
        user_id: UUID | None,
    ) -> list[float] | None:
        """Embed via LLMGateway (routes to OpenAI text-embedding-3-large via LiteLLM).

        Includes BYOK key resolution, retry, and cost tracking automatically.
        """
        assert self._llm_gateway is not None
        try:
            # System sentinel for calls without user context
            _SYSTEM_USER = UUID("00000000-0000-0000-0000-000000000000")
            effective_user = user_id if user_id is not None else _SYSTEM_USER

            response = await self._llm_gateway.embed(
                workspace_id=workspace_id,
                user_id=effective_user,
                texts=[text],
                agent_name="embedding_service",
            )
            if response.embeddings:
                return list(response.embeddings[0])
            return None
        except Exception:
            logger.warning(
                "EmbeddingService: LLMGateway embedding failed — trying Ollama", exc_info=True
            )
            return None

    async def _embed_ollama(self, text: str) -> list[float] | None:
        """Embed via Ollama nomic-embed-text-v2-moe (768-dim, local).

        Runs sync urllib call in a thread to avoid blocking the event loop.
        """
        try:
            return await asyncio.to_thread(
                _ollama_embed_sync,
                text,
                self._config.ollama_base_url,
                _OLLAMA_MODEL,
                _OLLAMA_TIMEOUT_S,
            )
        except Exception:
            logger.warning("EmbeddingService: Ollama embedding failed", exc_info=True)
            return None


def _ollama_embed_sync(
    text: str,
    base_url: str,
    model: str,
    timeout: int,
) -> list[float] | None:
    """Synchronous Ollama embed — run inside asyncio.to_thread."""
    import json
    import urllib.request

    payload = json.dumps({"model": model, "input": text}).encode()
    req = urllib.request.Request(
        f"{base_url}/api/embed",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read())
    embeddings = body.get("embeddings")
    return list(embeddings[0]) if embeddings else None


__all__ = ["EmbeddingConfig", "EmbeddingService"]
