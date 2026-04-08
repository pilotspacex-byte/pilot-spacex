"""MemoryRecallService — typed, cached, single-flight recall over the knowledge graph.

Phase 69 Wave 2: wraps the existing ``GraphSearchService`` with a
``MemoryType``-based filter, a Redis hot cache, and per-key single-flight
deduplication so concurrent recalls with the same parameters collapse into
a single embed + DB round-trip.

This service is intentionally *behind* the existing
``recall_graph_context()`` seam in ``pilotspace_agent.py`` — Wave 3 /
plan 05 will swap it in without touching the call site.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pilot_space.ai.telemetry.memory_metrics import (
    record_recall_hit,
    record_recall_latency_ms,
    record_recall_miss,
)
from pilot_space.application.services.memory.graph_search_service import (
    GraphSearchPayload,
    GraphSearchService,
)
from pilot_space.domain.graph_node import NodeType
from pilot_space.domain.memory.memory_type import MemoryType
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from pilot_space.ai.infrastructure.cache import AIResponseCache
    from pilot_space.application.services.embedding_service import EmbeddingService

logger = get_logger(__name__)

_CACHE_AGENT_NAME = "memory_recall"
_DEFAULT_K = 8
_DEFAULT_MIN_SCORE = 0.7
# Hard ceiling on the downstream GraphSearch call (embed + hybrid query).
# Exists to protect the agent's first-token latency when embedding providers
# stall. Chosen well above the 200ms p95 SLO so normal traffic is unaffected.
_RECALL_HARD_TIMEOUT_S = 0.5

# Module-level single-flight lock registry keyed by cache key.
# Prevents thundering-herd: concurrent identical recalls share one in-flight
# coroutine. Each acquire bumps a refcount; the last releaser pops the entry
# so the registry size is bounded by in-flight parallelism, not cardinality.
_inflight_locks: dict[str, tuple[asyncio.Lock, int]] = {}
_inflight_registry_lock = asyncio.Lock()


@dataclass(frozen=True, slots=True)
class RecallPayload:
    """Input to a memory recall call.

    Attributes:
        workspace_id: Workspace scope (required for multi-tenant isolation).
        query: Natural language query string.
        k: Max number of items to return.
        types: Restrict to these memory types (None = all 5).
        min_score: Minimum fused score threshold (items below are dropped).
        user_id: Optional user scope for surfacing personal context.
    """

    workspace_id: UUID
    query: str
    k: int = _DEFAULT_K
    types: tuple[MemoryType, ...] | None = None
    min_score: float = _DEFAULT_MIN_SCORE
    user_id: UUID | None = None


@dataclass(slots=True)
class MemoryItem:
    """A single recalled memory with provenance."""

    source_type: str
    source_id: str
    node_id: str
    score: float
    snippet: str
    created_at: str


@dataclass(slots=True)
class RecallResult:
    """Result of a recall call.

    Attributes:
        items: Recalled memories (already filtered by ``min_score``).
        cache_hit: True when the result came from the hot cache.
        elapsed_ms: Wall-clock elapsed time in milliseconds.
    """

    items: list[MemoryItem] = field(default_factory=list)
    cache_hit: bool = False
    elapsed_ms: float = 0.0


class MemoryRecallService:
    """Typed wrapper over ``GraphSearchService`` with hot cache + single-flight.

    Instances are safe to share across requests: the service itself is
    stateless, and the underlying ``GraphSearchService`` is instantiated
    per-call with the request-scoped DB session resolved by the caller.

    Because the existing ``AIResponseCache`` has a fixed TTL, this service
    relies on that TTL (configured via ``ttl_seconds`` at construction time
    — default 1 hour in ``cache.py``). For the 30s TTL requested by the
    plan, construct a dedicated cache instance with ``ttl_seconds=30``.
    """

    def __init__(
        self,
        graph_search: GraphSearchService,
        embedding: EmbeddingService,
        cache: AIResponseCache | None = None,
    ) -> None:
        self._graph_search = graph_search
        self._embedding = embedding
        self._cache = cache

    async def recall(self, payload: RecallPayload) -> RecallResult:
        """Recall memories matching ``payload``.

        Flow:
          1. Build deterministic cache key over (workspace, query, types, k, min_score).
          2. Cache get — hit returns immediately.
          3. Acquire single-flight lock keyed on cache key.
          4. Re-check cache after acquiring lock (lost-update guard).
          5. Delegate to GraphSearchService (which handles embedding + hybrid search).
          6. Filter by ``min_score``.
          7. Populate cache.
        """
        t0 = time.perf_counter()

        types_tuple: tuple[MemoryType, ...] = (
            payload.types if payload.types is not None else tuple(MemoryType)
        )
        node_types: list[NodeType] = [t.to_node_type() for t in types_tuple]

        # H3: include an embedding-model fingerprint so rotating BYOK keys or
        # switching providers mid-TTL can't serve vectors from a stale model.
        embedding_fp = (
            getattr(self._embedding, "model_name", None)
            or getattr(self._embedding, "provider", None)
            or "default"
        )
        cache_input = {
            "workspace_id": str(payload.workspace_id),
            "query": payload.query,
            "types": sorted(t.value for t in types_tuple),
            "k": payload.k,
            "min_score": payload.min_score,
            "user_id": str(payload.user_id) if payload.user_id else None,
            "embedding_fp": str(embedding_fp),
        }

        # 1. Fast-path cache check (no lock needed for read)
        cached = await self._cache_get(cache_input)
        if cached is not None:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            record_recall_hit()
            record_recall_latency_ms(elapsed_ms)
            return RecallResult(
                items=cached,
                cache_hit=True,
                elapsed_ms=elapsed_ms,
            )

        # 2. Single-flight: concurrent callers share one in-flight call.
        # The registry key is stable across callers so refcount release in
        # the finally block is guaranteed even if the delegate raises.
        registry_key = _stable_key(cache_input)
        lock = await self._acquire_inflight_lock(registry_key)
        try:
            async with lock:
                # 3. Re-check cache after acquiring the lock
                cached = await self._cache_get(cache_input)
                if cached is not None:
                    elapsed_ms = (time.perf_counter() - t0) * 1000.0
                    record_recall_hit()
                    record_recall_latency_ms(elapsed_ms)
                    return RecallResult(
                        items=cached,
                        cache_hit=True,
                        elapsed_ms=elapsed_ms,
                    )

                # 4. Delegate to GraphSearchService under a hard timeout.
                # C4: on timeout we degrade gracefully — empty recall, no
                # <memory> block, agent still produces a response.
                try:
                    result = await asyncio.wait_for(
                        self._graph_search.execute(
                            GraphSearchPayload(
                                query=payload.query,
                                workspace_id=payload.workspace_id,
                                user_id=payload.user_id,
                                node_types=node_types,
                                limit=payload.k,
                            )
                        ),
                        timeout=_RECALL_HARD_TIMEOUT_S,
                    )
                except TimeoutError:
                    elapsed_ms = (time.perf_counter() - t0) * 1000.0
                    record_recall_miss()
                    record_recall_latency_ms(elapsed_ms)
                    logger.warning(
                        "memory_recall: graph_search timed out after %.0fms "
                        "workspace=%s — degrading to empty recall",
                        _RECALL_HARD_TIMEOUT_S * 1000.0,
                        payload.workspace_id,
                    )
                    return RecallResult(items=[], cache_hit=False, elapsed_ms=elapsed_ms)

                # 5. Filter by min_score + materialize MemoryItem
                items: list[MemoryItem] = [
                    _scored_to_memory_item(sn)
                    for sn in result.nodes
                    if sn.score >= payload.min_score
                ]

                # 6. Cache the result
                await self._cache_set(cache_input, items)
        finally:
            await self._release_inflight_lock(registry_key)

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        record_recall_miss()
        record_recall_latency_ms(elapsed_ms)
        return RecallResult(
            items=items,
            cache_hit=False,
            elapsed_ms=elapsed_ms,
        )

    # ------------------------------------------------------------------
    # Cache helpers (tolerate cache=None and cache failures)
    # ------------------------------------------------------------------

    async def _cache_get(self, cache_input: Mapping[str, object]) -> list[MemoryItem] | None:
        if self._cache is None:
            return None
        try:
            raw = await self._cache.get(_CACHE_AGENT_NAME, cache_input)
        except Exception:
            logger.warning("memory_recall: cache get failed", exc_info=True)
            return None
        if raw is None:
            return None
        if not isinstance(raw, list):
            return None
        return [MemoryItem(**item) for item in raw if isinstance(item, dict)]

    async def _cache_set(
        self, cache_input: Mapping[str, object], items: list[MemoryItem]
    ) -> None:
        if self._cache is None:
            return
        try:
            await self._cache.set(
                _CACHE_AGENT_NAME,
                cache_input,
                [asdict(item) for item in items],
            )
        except Exception:
            logger.warning("memory_recall: cache set failed", exc_info=True)

    async def _acquire_inflight_lock(self, key: str) -> asyncio.Lock:
        """Return the per-key lock and bump its refcount.

        Callers MUST pair this with :meth:`_release_inflight_lock` in a
        ``finally`` block so the registry entry is popped when the last
        concurrent caller exits — otherwise the registry would leak one
        entry per unique cache key.
        """
        async with _inflight_registry_lock:
            entry = _inflight_locks.get(key)
            if entry is None:
                lock = asyncio.Lock()
                _inflight_locks[key] = (lock, 1)
                return lock
            lock, refcount = entry
            _inflight_locks[key] = (lock, refcount + 1)
            return lock

    async def _release_inflight_lock(self, key: str) -> None:
        """Decrement the per-key refcount and pop the entry at zero."""
        async with _inflight_registry_lock:
            entry = _inflight_locks.get(key)
            if entry is None:
                return
            lock, refcount = entry
            if refcount <= 1:
                _inflight_locks.pop(key, None)
            else:
                _inflight_locks[key] = (lock, refcount - 1)


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _stable_key(cache_input: Mapping[str, object]) -> str:
    """Build a stable string key from the cache_input dict."""
    import hashlib
    import json

    payload = json.dumps(cache_input, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def _scored_to_memory_item(sn: object) -> MemoryItem:
    """Convert a ScoredNode into a MemoryItem with provenance fields."""
    # Local import + duck typing to avoid a hard dependency cycle.
    node = getattr(sn, "node", None)
    score = float(getattr(sn, "score", 0.0))
    node_id = getattr(node, "id", "")
    node_type = getattr(node, "node_type", "")
    external_id = getattr(node, "external_id", None)
    content = getattr(node, "content", "") or ""
    created_at = getattr(node, "created_at", None)
    created_at_str = (
        created_at.isoformat() if isinstance(created_at, datetime) else str(created_at or "")
    )
    source_id = str(external_id) if external_id is not None else str(node_id)
    source_type = str(node_type)
    return MemoryItem(
        source_type=source_type,
        source_id=source_id,
        node_id=str(node_id),
        score=score,
        snippet=content[:240],
        created_at=created_at_str,
    )


__all__ = [
    "MemoryItem",
    "MemoryRecallService",
    "RecallPayload",
    "RecallResult",
]
