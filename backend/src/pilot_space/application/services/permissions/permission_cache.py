"""In-process LRU + Redis pub/sub cache for resolved tool permissions.

Phase 69 — PermissionService hot path. Target <5ms p95 on cache hit.
Two layers:

1. **In-process LRU** (``OrderedDict``) — 4096 entries, 60s TTL. Sized
   for ~40 tools across 100 workspaces = 4000 keys. Hit path is a dict
   lookup + TTL check (microseconds).

2. **Redis pub/sub channel** ``permissions:invalidate`` — when any
   worker calls ``PermissionService.set()``, it publishes a message;
   every process listening via ``subscribe_invalidations()`` evicts
   the matching local entry. This gives us cross-worker consistency
   without a Redis round-trip on every resolve.

The cache is keyed by ``(workspace_id, tool_name)``. Workspace-wide
invalidation (``invalidate_workspace``) is used when a policy template
is applied in bulk.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections import OrderedDict
from typing import TYPE_CHECKING
from uuid import UUID

from pilot_space.application.services.permissions.exceptions import (
    InvalidPolicyError,
    PermissionDeniedError,
)
from pilot_space.domain.permissions.tool_permission_mode import ToolPermissionMode
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = get_logger(__name__)

INVALIDATION_CHANNEL = "permissions:invalidate"
DEFAULT_MAX_ENTRIES = 4096
DEFAULT_TTL_SECONDS = 60.0


__all__ = [
    "DEFAULT_MAX_ENTRIES",
    "DEFAULT_TTL_SECONDS",
    "INVALIDATION_CHANNEL",
    "InvalidPolicyError",
    "PermissionCache",
    "PermissionDeniedError",
]


class PermissionCache:
    """LRU cache of resolved ``(workspace_id, tool_name) -> ToolPermissionMode``.

    Thread-safety: the cache is designed for asyncio — all callers run
    on a single event loop per process, so no lock is required.
    """

    def __init__(
        self,
        max_entries: int = DEFAULT_MAX_ENTRIES,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
    ) -> None:
        self._max_entries = max_entries
        self._ttl = ttl_seconds
        self._store: OrderedDict[tuple[UUID, str], tuple[ToolPermissionMode, float]] = (
            OrderedDict()
        )
        self._subscriber_task: asyncio.Task[None] | None = None

    def get(self, workspace_id: UUID, tool_name: str) -> ToolPermissionMode | None:
        """Return the cached mode or ``None`` on miss / expiry."""
        key = (workspace_id, tool_name)
        entry = self._store.get(key)
        if entry is None:
            return None
        mode, expires_at = entry
        if time.monotonic() >= expires_at:
            self._store.pop(key, None)
            return None
        # LRU bump
        self._store.move_to_end(key)
        return mode

    def set(self, workspace_id: UUID, tool_name: str, mode: ToolPermissionMode) -> None:
        """Insert or refresh an entry, evicting the oldest on overflow."""
        key = (workspace_id, tool_name)
        self._store[key] = (mode, time.monotonic() + self._ttl)
        self._store.move_to_end(key)
        while len(self._store) > self._max_entries:
            self._store.popitem(last=False)

    def invalidate(self, workspace_id: UUID, tool_name: str) -> None:
        """Drop a single ``(workspace_id, tool_name)`` entry."""
        self._store.pop((workspace_id, tool_name), None)

    def invalidate_workspace(self, workspace_id: UUID) -> None:
        """Drop every entry for a workspace (bulk template apply)."""
        stale_keys = [k for k in self._store if k[0] == workspace_id]
        for key in stale_keys:
            self._store.pop(key, None)

    def clear(self) -> None:
        """Drop all entries. Primarily used by tests."""
        self._store.clear()

    async def subscribe_invalidations(self, redis_client: Redis) -> None:
        """Listen on ``permissions:invalidate`` and evict matching entries.

        Spawns a background task once per process. Messages are JSON
        with ``{workspace_id, tool_name}``; an empty ``tool_name`` means
        "invalidate the entire workspace" (bulk template apply).
        """
        if self._subscriber_task is not None and not self._subscriber_task.done():
            return

        async def _run() -> None:
            pubsub = redis_client.pubsub()
            try:
                await pubsub.subscribe(INVALIDATION_CHANNEL)
                async for message in pubsub.listen():
                    if message.get("type") != "message":
                        continue
                    try:
                        payload = json.loads(message["data"])
                        workspace_id = UUID(payload["workspace_id"])
                        tool_name = payload.get("tool_name") or ""
                        if tool_name:
                            self.invalidate(workspace_id, tool_name)
                        else:
                            self.invalidate_workspace(workspace_id)
                    except (ValueError, KeyError, TypeError) as exc:
                        logger.warning(
                            "Ignoring malformed permissions:invalidate message: %s",
                            exc,
                        )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("permissions:invalidate subscriber crashed")
            finally:
                try:
                    await pubsub.unsubscribe(INVALIDATION_CHANNEL)
                    await pubsub.close()
                except Exception:
                    logger.debug("Error closing permissions pubsub", exc_info=True)

        self._subscriber_task = asyncio.create_task(
            _run(), name="permissions-invalidate-subscriber"
        )
