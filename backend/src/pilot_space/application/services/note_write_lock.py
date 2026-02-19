"""Note write lock — Redis mutex for concurrent skill write protection.

C-3: Acquire a per-note write mutex before any note mutation performed by a skill
execution.  Prevents two skills from clobbering the same note simultaneously.

Uses the Redis SET NX EX pattern for atomic acquisition.  A Lua script is used for
atomic compare-and-delete on release so that a lock can only be released by its owner.

Feature 015: AI Workforce Platform — Sprint 2
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Final
from uuid import UUID, uuid4

from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from pilot_space.infrastructure.cache.redis import RedisClient

logger = get_logger(__name__)

LOCK_TTL_S: Final[int] = 30
ACQUIRE_TIMEOUT_S: Final[float] = 5.0
_POLL_INTERVAL_S: Final[float] = 0.1
_LOCK_PREFIX: Final[str] = "note_write_lock"

# Lua script: delete key only when value matches (atomic owner check + delete)
_RELEASE_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""


class NoteLockTimeoutError(TimeoutError):
    """Raised when a note write lock could not be acquired within the timeout."""


class NoteWriteLock:
    """Redis-based per-note write mutex for concurrent skill protection.

    Protects note content from being overwritten by simultaneous skill
    executions.  The lock is owner-keyed so only the acquirer can release it.
    TTL prevents indefinite lock hold on process crash.

    Args:
        redis_client: Application Redis client.

    Example:
        lock = NoteWriteLock(redis_client)
        async with lock.lock(note_id) as lock_id:
            # safe to write to note
            ...
    """

    def __init__(self, redis_client: RedisClient) -> None:
        self._redis = redis_client

    def _key(self, note_id: UUID) -> str:
        return f"{_LOCK_PREFIX}:{note_id}"

    async def acquire(self, note_id: UUID) -> str:
        """Acquire the write lock for a note, blocking until acquired or timeout.

        Polls Redis every 100 ms until SET NX EX succeeds or ACQUIRE_TIMEOUT_S
        elapses.

        Args:
            note_id: Note UUID to lock.

        Returns:
            lock_id: Unique string identifying this lock holder.

        Raises:
            NoteLockTimeoutError: If lock cannot be acquired within timeout.
        """
        key = self._key(note_id)
        lock_id = str(uuid4())
        deadline = asyncio.get_event_loop().time() + ACQUIRE_TIMEOUT_S

        while True:
            acquired = await self._redis.set(
                key,
                lock_id,
                ttl=LOCK_TTL_S,
                if_not_exists=True,
            )
            if acquired:
                logger.debug(
                    "[NoteWriteLock] Acquired note_id=%s lock_id=%s ttl=%ds",
                    note_id,
                    lock_id,
                    LOCK_TTL_S,
                )
                return lock_id

            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                raise NoteLockTimeoutError(
                    f"Could not acquire write lock for note {note_id} within {ACQUIRE_TIMEOUT_S}s"
                )
            await asyncio.sleep(min(_POLL_INTERVAL_S, remaining))

    async def release(self, note_id: UUID, lock_id: str) -> None:
        """Release the write lock only if the caller owns it.

        Uses a Lua script for atomic compare-and-delete.  A mismatched lock_id
        (e.g. lock expired and re-acquired by another holder) is a no-op.

        Args:
            note_id: Note UUID to unlock.
            lock_id: Lock owner token returned from :meth:`acquire`.
        """
        key = self._key(note_id)
        # Fall back to simple delete when raw client is unavailable
        raw_client = getattr(self._redis, "_client", None)
        if raw_client is not None:
            try:
                result = await raw_client.eval(_RELEASE_SCRIPT, 1, key, lock_id)  # type: ignore[union-attr]
                if result == 0:
                    logger.warning(
                        "[NoteWriteLock] Release skipped — lock_id mismatch note_id=%s lock_id=%s",
                        note_id,
                        lock_id,
                    )
                else:
                    logger.debug(
                        "[NoteWriteLock] Released note_id=%s lock_id=%s",
                        note_id,
                        lock_id,
                    )
                return
            except Exception:
                logger.warning(
                    "[NoteWriteLock] Lua eval unavailable, falling back to plain delete note_id=%s",
                    note_id,
                )
        # Plain delete fallback (no owner check — less safe but still correct
        # in the common case where TTL prevents lock leak)
        await self._redis.delete(key)
        logger.debug("[NoteWriteLock] Released (plain delete) note_id=%s", note_id)

    @asynccontextmanager
    async def lock(self, note_id: UUID) -> AsyncIterator[str]:
        """Context manager: acquire lock, yield lock_id, release on exit.

        Args:
            note_id: Note UUID to protect.

        Yields:
            lock_id: The unique owner token for this acquisition.

        Raises:
            NoteLockTimeoutError: If lock cannot be acquired within timeout.
        """
        lock_id = await self.acquire(note_id)
        try:
            yield lock_id
        finally:
            await self.release(note_id, lock_id)


__all__ = ["NoteLockTimeoutError", "NoteWriteLock"]
