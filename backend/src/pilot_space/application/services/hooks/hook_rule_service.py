"""HookRuleService -- CRUD + cache invalidation for workspace hook rules.

Phase 83 -- the service layer for declarative hook rules. Owns:

* ``create()`` -- validate pattern, enforce 50-rule limit, persist, cache bust.
* ``update()`` -- validate ownership, re-validate pattern if changed, persist.
* ``delete()`` -- validate ownership, remove, cache bust.
* ``list_rules()`` -- list all rules for a workspace (admin view).
* ``get_cached_rules()`` -- hot-path for the evaluator: Redis-backed cache.

**DD-003 defense-in-depth:** The guard for CRITICAL tools lives in the
evaluator (Plan 02), not here. Admins CAN create ``action=allow`` rules
for CRITICAL tools -- the evaluator overrides them to ``require_approval``
at runtime. This design lets admins see what they configured while
maintaining the security invariant.

The service is registered as a ``providers.Singleton``: it reads the
request-scoped ``AsyncSession`` at every call via
``get_current_session()`` (same pattern as ``PermissionService``).
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pilot_space.application.services.hooks.exceptions import (
    HookRuleLimitError,
    HookRuleNotFoundError,
    InvalidHookPatternError,
)
from pilot_space.dependencies.auth import get_current_session
from pilot_space.domain.exceptions import ForbiddenError
from pilot_space.infrastructure.database.repositories.workspace_hook_config_repository import (
    WorkspaceHookConfigRepository,
)
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.cache.redis import RedisClient
    from pilot_space.infrastructure.database.models.workspace_hook_config import (
        WorkspaceHookConfig,
    )

logger = get_logger(__name__)


# Maximum chars for tool_pattern (ReDoS mitigation, T-83-04).
_MAX_PATTERN_LENGTH = 200


class HookRuleService:
    """CRUD service for workspace hook rules with Redis cache invalidation.

    Singleton lifecycle -- reads the request-scoped ``AsyncSession`` via
    ``get_current_session()`` at each call (Pitfall 10 pattern).

    Cache strategy:
    * Key: ``hooks:workspace:{workspace_id}``
    * TTL: 300 s (5 min)
    * Invalidation: delete key + Redis pub/sub broadcast on mutation
    """

    MAX_RULES_PER_WORKSPACE = 50
    CACHE_TTL_SECONDS = 300  # 5 min
    CACHE_KEY_PREFIX = "hooks:workspace:"
    INVALIDATION_CHANNEL = "hooks:invalidate"

    def __init__(self, redis_client: RedisClient | None = None) -> None:
        """Initialize the service.

        Args:
            redis_client: Async Redis client for caching and cross-worker
                invalidation pub/sub. Optional for tests.
        """
        self._redis = redis_client

    # ------------------------------------------------------------------
    # Session / repository helpers (Singleton + ContextVar)
    # ------------------------------------------------------------------

    @property
    def _session(self) -> AsyncSession:
        return get_current_session()

    def _repo(self) -> WorkspaceHookConfigRepository:
        return WorkspaceHookConfigRepository(self._session)

    # ------------------------------------------------------------------
    # Pattern validation (T-83-01, T-83-04)
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_pattern(tool_pattern: str) -> None:
        """Validate a tool_pattern value.

        Rules:
        1. Max 200 characters (ReDoS mitigation).
        2. If wrapped in ``/`` delimiters, must compile as valid regex.
        3. Otherwise accepted as glob/exact pattern (fnmatch handles at eval).

        Raises:
            InvalidHookPatternError: On validation failure.
        """
        if len(tool_pattern) > _MAX_PATTERN_LENGTH:
            raise InvalidHookPatternError(
                f"Tool pattern exceeds {_MAX_PATTERN_LENGTH} character limit "
                f"(got {len(tool_pattern)} chars)",
            )

        if not tool_pattern.strip():
            raise InvalidHookPatternError("Tool pattern must not be empty")

        # Regex pattern: /pattern/
        if tool_pattern.startswith("/") and tool_pattern.endswith("/") and len(tool_pattern) > 2:
            regex_body = tool_pattern[1:-1]
            try:
                re.compile(regex_body)
            except re.error as exc:
                raise InvalidHookPatternError(
                    f"Invalid regex pattern: {exc}",
                ) from exc

    # ------------------------------------------------------------------
    # CRUD operations
    # ------------------------------------------------------------------

    async def create(
        self,
        *,
        workspace_id: UUID,
        name: str,
        tool_pattern: str,
        action: str,
        event_type: str = "PreToolUse",
        priority: int = 100,
        description: str | None = None,
        actor_user_id: UUID,
    ) -> WorkspaceHookConfig:
        """Create a new hook rule.

        Validates pattern, enforces 50-rule limit, persists the rule,
        and invalidates the Redis cache.

        Note on DD-003: ``action=allow`` is permitted at creation time
        even for CRITICAL tools. The evaluator (Plan 02) overrides
        allow -> require_approval at runtime for CRITICAL tools.

        Args:
            workspace_id: Owning workspace.
            name: Human-readable rule name (unique per workspace).
            tool_pattern: Glob, regex, or exact match pattern.
            action: One of ``allow`` | ``deny`` | ``require_approval``.
            event_type: Hook event type (default ``PreToolUse``).
            priority: Evaluation order (lower = higher priority).
            description: Optional description.
            actor_user_id: Admin user creating the rule.

        Returns:
            The persisted WorkspaceHookConfig.

        Raises:
            InvalidHookPatternError: If tool_pattern is invalid.
            HookRuleLimitError: If workspace has 50+ rules already.
        """
        self._validate_pattern(tool_pattern)

        repo = self._repo()
        count = await repo.count_for_workspace(workspace_id)
        if count >= self.MAX_RULES_PER_WORKSPACE:
            raise HookRuleLimitError(
                f"Workspace has reached the maximum of "
                f"{self.MAX_RULES_PER_WORKSPACE} hook rules",
            )

        hook = await repo.create(
            workspace_id=workspace_id,
            name=name,
            tool_pattern=tool_pattern,
            action=action,
            event_type=event_type,
            priority=priority,
            description=description,
            created_by=actor_user_id,
            updated_by=actor_user_id,
        )

        await self._invalidate_cache(workspace_id)
        return hook

    async def update(
        self,
        *,
        workspace_id: UUID,
        hook_id: UUID,
        actor_user_id: UUID,
        **kwargs: Any,
    ) -> WorkspaceHookConfig:
        """Update an existing hook rule.

        Validates workspace ownership, re-validates pattern if changed,
        persists updates, and invalidates the Redis cache.

        Args:
            workspace_id: Owning workspace (for ownership check).
            hook_id: The hook rule to update.
            actor_user_id: Admin user performing the update.
            **kwargs: Mutable fields to update (name, tool_pattern,
                action, event_type, priority, description, is_enabled).

        Returns:
            The updated WorkspaceHookConfig.

        Raises:
            HookRuleNotFoundError: If hook_id not found.
            ForbiddenError: If hook belongs to a different workspace.
            InvalidHookPatternError: If new tool_pattern is invalid.
        """
        repo = self._repo()
        hook = await repo.get_by_id(hook_id)
        if hook is None:
            raise HookRuleNotFoundError(f"Hook rule {hook_id} not found")
        if hook.workspace_id != workspace_id:
            raise ForbiddenError("Hook rule belongs to a different workspace")

        # Re-validate pattern if changed.
        if "tool_pattern" in kwargs:
            self._validate_pattern(kwargs["tool_pattern"])

        kwargs["updated_by"] = actor_user_id
        hook = await repo.update(hook, **kwargs)
        await self._invalidate_cache(workspace_id)
        return hook

    async def delete(
        self,
        *,
        workspace_id: UUID,
        hook_id: UUID,
        actor_user_id: UUID,
    ) -> None:
        """Delete a hook rule.

        Validates workspace ownership, removes the rule, and invalidates
        the Redis cache.

        Args:
            workspace_id: Owning workspace (for ownership check).
            hook_id: The hook rule to delete.
            actor_user_id: Admin user performing the deletion.

        Raises:
            HookRuleNotFoundError: If hook_id not found.
            ForbiddenError: If hook belongs to a different workspace.
        """
        repo = self._repo()
        hook = await repo.get_by_id(hook_id)
        if hook is None:
            raise HookRuleNotFoundError(f"Hook rule {hook_id} not found")
        if hook.workspace_id != workspace_id:
            raise ForbiddenError("Hook rule belongs to a different workspace")

        await repo.delete(hook)
        await self._invalidate_cache(workspace_id)

    async def list_rules(
        self,
        workspace_id: UUID,
        *,
        include_disabled: bool = False,
    ) -> list[WorkspaceHookConfig]:
        """List hook rules for a workspace (admin view).

        Args:
            workspace_id: Owning workspace.
            include_disabled: If True, include disabled rules.

        Returns:
            List of hook rules ordered by priority ASC.
        """
        return await self._repo().list_for_workspace(
            workspace_id,
            include_disabled=include_disabled,
        )

    # ------------------------------------------------------------------
    # Cached access (evaluator hot path)
    # ------------------------------------------------------------------

    async def get_cached_rules(self, workspace_id: UUID) -> list[dict[str, Any]]:
        """Return enabled rules for a workspace, backed by Redis cache.

        The evaluator calls this on every tool invocation. Cache hit
        avoids a DB round-trip. On miss, queries the DB, serializes to
        dicts, and stores with a 5-minute TTL.

        Args:
            workspace_id: Owning workspace.

        Returns:
            List of rule dicts (serializable format for the evaluator).
        """
        cache_key = f"{self.CACHE_KEY_PREFIX}{workspace_id}"

        # Try Redis cache first.
        if self._redis is not None and self._redis.is_connected:
            try:
                cached = await self._redis.get(cache_key)
                if cached is not None:
                    # RedisClient.get() returns deserialized JSON (via orjson).
                    if isinstance(cached, list):
                        return cached
            except Exception:
                logger.warning(
                    "Redis cache read failed for key=%s; falling back to DB",
                    cache_key,
                    exc_info=True,
                )

        # Cache miss -- query DB.
        repo = self._repo()
        rules = await repo.list_enabled_for_workspace(workspace_id)
        serialized = [
            {
                "id": str(r.id),
                "name": r.name,
                "tool_pattern": r.tool_pattern,
                "action": r.action,
                "event_type": r.event_type,
                "priority": r.priority,
            }
            for r in rules
        ]

        # Write-back to cache (best effort).
        if self._redis is not None and self._redis.is_connected:
            try:
                await self._redis.set(
                    cache_key,
                    serialized,
                    ttl=self.CACHE_TTL_SECONDS,
                )
            except Exception:
                logger.warning(
                    "Redis cache write failed for key=%s",
                    cache_key,
                    exc_info=True,
                )

        return serialized

    # ------------------------------------------------------------------
    # Cache invalidation
    # ------------------------------------------------------------------

    async def _invalidate_cache(self, workspace_id: UUID) -> None:
        """Delete Redis cache key and publish invalidation message.

        Best-effort: failures are logged but do not block the mutation.
        The cache TTL (5 min) ensures eventual consistency even if
        invalidation fails.
        """
        if self._redis is None or not self._redis.is_connected:
            return

        cache_key = f"{self.CACHE_KEY_PREFIX}{workspace_id}"
        try:
            await self._redis.delete(cache_key)
        except Exception:
            logger.exception(
                "Failed to delete Redis cache key=%s",
                cache_key,
            )

        payload = json.dumps({"workspace_id": str(workspace_id)})
        try:
            await self._redis.publish(self.INVALIDATION_CHANNEL, payload)
        except Exception:
            logger.exception(
                "Failed to publish hooks:invalidate for workspace=%s",
                workspace_id,
            )


__all__ = ["HookRuleService"]
