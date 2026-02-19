"""Skill concurrency manager — Redis-backed per-workspace execution slot limiter.

T-047: Limit concurrent skill executions to MAX_CONCURRENT (5) per workspace.
Slots are tracked as Redis counters with a 5-minute safety TTL to prevent leaks.

Feature 015: AI Workforce Platform — Sprint 2
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final
from uuid import UUID

from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from pilot_space.infrastructure.cache.redis import RedisClient

logger = get_logger(__name__)

MAX_CONCURRENT: Final[int] = 5
_SLOT_KEY_PREFIX: Final[str] = "skill_slots"
_SLOT_TTL_S: Final[int] = 300  # 5-minute safety TTL


class SkillConcurrencyManager:
    """Redis-backed concurrency limiter for per-workspace skill executions.

    Uses an atomic Redis counter to track in-flight executions per workspace.
    When the counter exceeds MAX_CONCURRENT the slot request is denied.

    The counter is set with a 5-minute safety TTL on first increment to
    prevent counter leaks if a process crashes without releasing.

    Args:
        redis_client: Application Redis client.

    Example:
        manager = SkillConcurrencyManager(redis_client)
        acquired = await manager.acquire_slot(workspace_id)
        if not acquired:
            raise HTTPException(429, "Too many concurrent skills")
        try:
            ...
        finally:
            await manager.release_slot(workspace_id)
    """

    def __init__(self, redis_client: RedisClient) -> None:
        self._redis = redis_client

    def _key(self, workspace_id: UUID) -> str:
        return f"{_SLOT_KEY_PREFIX}:{workspace_id}"

    async def acquire_slot(self, workspace_id: UUID) -> bool:
        """Try to acquire a concurrent skill execution slot.

        Atomically increments the workspace counter.  If the new value is 1
        the safety TTL is set.  If the value exceeds MAX_CONCURRENT the
        counter is immediately decremented and False is returned.

        Args:
            workspace_id: Target workspace.

        Returns:
            True if a slot was acquired, False if the limit is already reached.
        """
        key = self._key(workspace_id)
        current = await self._redis.incr(key)
        if current is None:
            # Redis unavailable — fail open to avoid blocking all skill work
            logger.warning(
                "[SkillConcurrencyManager] Redis unavailable, failing open workspace=%s",
                workspace_id,
            )
            return True

        if current == 1:
            # First slot — stamp a safety TTL so the key doesn't persist forever
            await self._redis.expire(key, _SLOT_TTL_S)

        if current > MAX_CONCURRENT:
            await self._redis.decr(key)
            logger.info(
                "[SkillConcurrencyManager] No slot available workspace=%s current=%d max=%d",
                workspace_id,
                current - 1,
                MAX_CONCURRENT,
            )
            return False

        logger.debug(
            "[SkillConcurrencyManager] Slot acquired workspace=%s slots_in_use=%d",
            workspace_id,
            current,
        )
        return True

    async def release_slot(self, workspace_id: UUID) -> None:
        """Release a previously acquired skill execution slot.

        Decrements the workspace counter.  Clamps to 0 to prevent negative values
        from stale releases.

        Args:
            workspace_id: Target workspace.
        """
        key = self._key(workspace_id)
        new_val = await self._redis.decr(key)
        if new_val is not None and new_val < 0:
            # Clamp to 0 — defensive: should not happen in normal operation
            await self._redis.incr(key)
            logger.warning(
                "[SkillConcurrencyManager] Counter went negative, clamped workspace=%s",
                workspace_id,
            )
        logger.debug(
            "[SkillConcurrencyManager] Slot released workspace=%s remaining=%s",
            workspace_id,
            new_val,
        )

    async def get_queue_depth(self, workspace_id: UUID) -> int:
        """Return the number of executions waiting beyond the slot limit.

        Args:
            workspace_id: Target workspace.

        Returns:
            Number of queued (over-limit) executions.  0 when within limit.
        """
        key = self._key(workspace_id)
        val = await self._redis.get(key)
        if val is None:
            return 0
        current = int(val)
        return max(0, current - MAX_CONCURRENT)


__all__ = ["SkillConcurrencyManager"]
