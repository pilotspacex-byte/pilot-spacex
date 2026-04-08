"""PermissionService — 5-tier resolver, DD-003 guard, audit log writer.

Phase 69 — the service layer for granular AI tool permissions. Owns:

* ``resolve(workspace_id, tool_name)`` — 5-tier fallback chain.
* ``set(workspace_id, tool_name, mode, actor_user_id, reason=None)``
  — admin mutation with DD-003 invariant guard, audit log, and cache
  invalidation (local + Redis pub/sub).
* ``bulk_apply_template(workspace_id, template_name, actor_user_id)``
  — apply one of the pre-baked policy templates.
* ``list(workspace_id)`` — merged view of every known tool with its
  resolved mode, source attribution, and ``can_set_auto`` flag.

**DD-003 invariant (mirrors ``permission_handler.py:273-284``):** tools
classified as ``CRITICAL_REQUIRE_APPROVAL`` cannot be set to
``AUTO``. Attempts raise :class:`InvalidPolicyError`. This
enforcement is duplicated here (not delegated) so admin API calls
fail-fast with a structured RFC 7807 response instead of silently
falling through at tool-invocation time.

The service is registered as a ``providers.Singleton``: it reads the
request-scoped ``AsyncSession`` at every call via
``get_current_session()`` (see Pitfall 10 in 69-RESEARCH.md).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from pilot_space.ai.agents.pilotspace_agent_helpers import ALL_TOOL_NAMES
from pilot_space.ai.sdk.permission_handler import (
    ActionClassification,
    PermissionHandler,
)
from pilot_space.application.services.permissions.exceptions import (
    InvalidPolicyError,
)
from pilot_space.application.services.permissions.permission_cache import (
    INVALIDATION_CHANNEL,
    PermissionCache,
)
from pilot_space.application.services.permissions.policy_templates import (
    POLICY_TEMPLATES,
    TEMPLATE_NAMES,
    is_critical,
)
from pilot_space.dependencies.auth import get_current_session
from pilot_space.domain.permissions.tool_permission_mode import ToolPermissionMode
from pilot_space.infrastructure.database.models.tool_permission_audit_log import (
    ToolPermissionAuditLog,
)
from pilot_space.infrastructure.database.repositories.workspace_tool_permission_repository import (
    WorkspaceToolPermissionRepository,
)
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from redis.asyncio import Redis
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

ACTION_CLASSIFICATIONS: dict[str, ActionClassification] = (
    PermissionHandler.ACTION_CLASSIFICATIONS
)


def _short_tool_name(tool_name: str) -> str:
    """Strip the ``mcp__<server>__`` prefix from a fully qualified MCP tool.

    ``ACTION_CLASSIFICATIONS`` is keyed by short names (e.g. ``update_issue``),
    but ``ALL_TOOL_NAMES`` contains fully qualified MCP names
    (e.g. ``mcp__pilot-issues__update_issue``). This helper bridges the two.
    """
    if tool_name.startswith("mcp__"):
        _, _, rest = tool_name.partition("__")
        if "__" in rest:
            return rest.split("__", 1)[1]
    return tool_name


def _classify(tool_name: str) -> ActionClassification | None:
    """Return the DD-003 classification for a tool, or ``None`` if unknown."""
    if tool_name in ACTION_CLASSIFICATIONS:
        return ACTION_CLASSIFICATIONS[tool_name]
    short = _short_tool_name(tool_name)
    return ACTION_CLASSIFICATIONS.get(short)


@dataclass(frozen=True, slots=True)
class ResolvedToolPermission:
    """Merged per-tool view returned from ``list(workspace_id)``."""

    tool_name: str
    mode: ToolPermissionMode
    source: str  # 'db' | 'override' | 'default'
    can_set_auto: bool


@dataclass(frozen=True, slots=True)
class BulkApplyResult:
    """Summary returned by ``bulk_apply_template``."""

    template: str
    applied: int
    skipped: list[str]


def _default_mode_for(tool_name: str) -> ToolPermissionMode:
    """Translate DD-003 default classification to a ``ToolPermissionMode``."""
    c = _classify(tool_name) or ActionClassification.DEFAULT_REQUIRE_APPROVAL
    if c is ActionClassification.AUTO_EXECUTE:
        return ToolPermissionMode.AUTO
    return ToolPermissionMode.ASK


class PermissionService:
    """5-tier granular tool permission resolver + admin mutator.

    Fallback chain (first hit wins):

    1. Local LRU cache (``PermissionCache``) — microseconds.
    2. Workspace DB row (``workspace_tool_permissions``).
    3. Workspace-level ``approval_overrides`` (pluggable provider).
    4. DD-003 default classification from ``ACTION_CLASSIFICATIONS``.
    5. Fallback default: ``ASK`` for unknown tools.

    Redis is layer 1.5 only used for cross-worker invalidation
    notifications, not for lookup (the local LRU is the hot path).
    """

    def __init__(
        self,
        cache: PermissionCache,
        redis_client: Redis | None = None,
        approval_overrides_provider: (
            Callable[[UUID], dict[str, str] | None] | None
        ) = None,
    ) -> None:
        """Initialize the service.

        Args:
            cache: Shared in-process LRU cache.
            redis_client: Async Redis client for cross-worker
                invalidation pub/sub. Optional for tests.
            approval_overrides_provider: Optional callable that returns
                workspace-scoped ``{tool_name: mode}`` overrides from
                workspace settings (tier 3 of the resolver). Defaults
                to a no-op returning ``None``.
        """
        self._cache = cache
        self._redis = redis_client
        self._overrides_provider = approval_overrides_provider or (lambda _w: None)

    # ------------------------------------------------------------------
    # Session / repository helpers (Pitfall 10 — Singleton + ContextVar)
    # ------------------------------------------------------------------

    @property
    def _session(self) -> AsyncSession:
        return get_current_session()

    def _repo(self) -> WorkspaceToolPermissionRepository:
        return WorkspaceToolPermissionRepository(self._session)

    # ------------------------------------------------------------------
    # Resolver
    # ------------------------------------------------------------------

    async def resolve(
        self,
        workspace_id: UUID,
        tool_name: str,
    ) -> ToolPermissionMode:
        """Return the effective mode for ``(workspace_id, tool_name)``.

        5-tier fallback — see class docstring.
        """
        # Tier 1: in-process LRU (hot path — microseconds).
        cached = self._cache.get(workspace_id, tool_name)
        if cached is not None:
            return cached

        mode = await self._resolve_uncached(workspace_id, tool_name)
        self._cache.set(workspace_id, tool_name, mode)
        return mode

    async def _resolve_uncached(
        self,
        workspace_id: UUID,
        tool_name: str,
    ) -> ToolPermissionMode:
        """Slow-path resolver: DB -> overrides -> default."""
        # Tier 2: DB row.
        row = await self._repo().get(workspace_id, tool_name)
        if row is not None:
            try:
                return ToolPermissionMode(row.mode)
            except ValueError:
                logger.warning(
                    "Invalid mode %r stored for workspace=%s tool=%s; "
                    "falling back to default",
                    row.mode,
                    workspace_id,
                    tool_name,
                )

        # Tier 3: workspace-level approval_overrides (pluggable).
        overrides = self._overrides_provider(workspace_id)
        if overrides and tool_name in overrides:
            try:
                return ToolPermissionMode(overrides[tool_name])
            except ValueError:
                logger.warning(
                    "Invalid override %r for workspace=%s tool=%s; "
                    "falling back to default",
                    overrides[tool_name],
                    workspace_id,
                    tool_name,
                )

        # Tier 4: DD-003 default classification.
        if _classify(tool_name) is not None:
            return _default_mode_for(tool_name)

        # Tier 5: unknown tool — safe default.
        return ToolPermissionMode.ASK

    # ------------------------------------------------------------------
    # Mutator
    # ------------------------------------------------------------------

    async def set(
        self,
        workspace_id: UUID,
        tool_name: str,
        mode: ToolPermissionMode,
        actor_user_id: UUID,
        reason: str | None = None,
    ) -> None:
        """Set the mode for ``(workspace_id, tool_name)``.

        Enforces DD-003: CRITICAL tools cannot be set to AUTO.
        Writes the permission row and an audit log row atomically,
        then invalidates the local LRU entry and publishes a Redis
        message so other workers evict their copies.
        """
        # DD-003 invariant — mirrors permission_handler.py:273-284.
        if (
            _classify(tool_name) is ActionClassification.CRITICAL_REQUIRE_APPROVAL
            and mode is ToolPermissionMode.AUTO
        ):
            raise InvalidPolicyError(
                f"DD-003: tool {tool_name!r} is CRITICAL and cannot be set to 'auto'",
            )

        repo = self._repo()
        row, previous_mode = await repo.upsert(
            workspace_id=workspace_id,
            tool_name=tool_name,
            mode=mode.value,
            actor_user_id=actor_user_id,
        )
        await repo.insert_audit_log(
            workspace_id=workspace_id,
            tool_name=tool_name,
            old_mode=previous_mode,
            new_mode=row.mode,
            actor_user_id=actor_user_id,
            reason=reason,
        )

        # Invalidate local cache immediately so this process sees the
        # new value without waiting for the Redis round-trip.
        self._cache.invalidate(workspace_id, tool_name)
        await self._publish_invalidation(workspace_id, tool_name)

    async def _publish_invalidation(
        self,
        workspace_id: UUID,
        tool_name: str,
    ) -> None:
        """Publish a Redis invalidation message (best effort)."""
        if self._redis is None:
            return
        payload = json.dumps(
            {"workspace_id": str(workspace_id), "tool_name": tool_name}
        )
        try:
            await self._redis.publish(INVALIDATION_CHANNEL, payload)
        except Exception:
            logger.exception(
                "Failed to publish permissions:invalidate for workspace=%s tool=%s",
                workspace_id,
                tool_name,
            )

    # ------------------------------------------------------------------
    # Bulk template apply
    # ------------------------------------------------------------------

    async def bulk_apply_template(
        self,
        workspace_id: UUID,
        template_name: str,
        actor_user_id: UUID,
    ) -> BulkApplyResult:
        """Apply a named template's ``tool -> mode`` map.

        Skipped tools (CRITICAL + AUTO combinations that would violate
        DD-003) are collected and returned, not raised — callers can
        surface a warning without blocking the whole operation.
        """
        if template_name not in POLICY_TEMPLATES:
            raise InvalidPolicyError(
                f"Unknown permission template {template_name!r}; "
                f"valid options: {', '.join(TEMPLATE_NAMES)}",
            )

        template = POLICY_TEMPLATES[template_name]
        applied = 0
        skipped: list[str] = []
        for tool_name, mode in template.items():
            try:
                await self.set(
                    workspace_id=workspace_id,
                    tool_name=tool_name,
                    mode=mode,
                    actor_user_id=actor_user_id,
                    reason=f"Bulk apply: {template_name} template",
                )
                applied += 1
            except InvalidPolicyError:
                logger.info(
                    "Skipped %s during %s template apply (DD-003 critical guard)",
                    tool_name,
                    template_name,
                )
                skipped.append(tool_name)

        # A bulk apply touches ~40 tools; drop the whole workspace
        # cache in one shot instead of relying on per-tool invalidations.
        self._cache.invalidate_workspace(workspace_id)
        await self._publish_workspace_invalidation(workspace_id)

        return BulkApplyResult(
            template=template_name,
            applied=applied,
            skipped=skipped,
        )

    async def _publish_workspace_invalidation(self, workspace_id: UUID) -> None:
        """Publish a workspace-wide invalidation (empty ``tool_name``)."""
        if self._redis is None:
            return
        payload = json.dumps(
            {"workspace_id": str(workspace_id), "tool_name": ""}
        )
        try:
            await self._redis.publish(INVALIDATION_CHANNEL, payload)
        except Exception:
            logger.exception(
                "Failed to publish workspace invalidation for workspace=%s",
                workspace_id,
            )

    # ------------------------------------------------------------------
    # Merged list view
    # ------------------------------------------------------------------

    async def list_all(
        self,
        workspace_id: UUID,
    ) -> list[ResolvedToolPermission]:
        """Return every known tool with its resolved mode + source.

        The ``source`` field distinguishes:

        * ``db`` — explicit row in ``workspace_tool_permissions``.
        * ``override`` — workspace-level ``approval_overrides`` hit.
        * ``default`` — DD-003 classification fallback.

        ``can_set_auto`` is ``False`` for CRITICAL tools (the admin UI
        renders them disabled to prevent DD-003 violations client-side).
        """
        repo = self._repo()
        db_rows = {r.tool_name: r.mode for r in await repo.list_for_workspace(workspace_id)}
        overrides = self._overrides_provider(workspace_id) or {}

        merged: list[ResolvedToolPermission] = []
        for tool_name in ALL_TOOL_NAMES:
            can_set_auto = not is_critical(tool_name)
            if tool_name in db_rows:
                try:
                    mode = ToolPermissionMode(db_rows[tool_name])
                except ValueError:
                    mode = _default_mode_for(tool_name)
                    source = "default"
                else:
                    source = "db"
            elif tool_name in overrides:
                try:
                    mode = ToolPermissionMode(overrides[tool_name])
                    source = "override"
                except ValueError:
                    mode = _default_mode_for(tool_name)
                    source = "default"
            else:
                mode = _default_mode_for(tool_name)
                source = "default"
            merged.append(
                ResolvedToolPermission(
                    tool_name=tool_name,
                    mode=mode,
                    source=source,
                    can_set_auto=can_set_auto,
                )
            )
        return merged


    # ------------------------------------------------------------------
    # Audit log view
    # ------------------------------------------------------------------

    async def list_audit_log(
        self,
        workspace_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ToolPermissionAuditLog]:
        """Return audit-log rows for a workspace, most-recent first."""
        return await self._repo().list_audit_log(workspace_id, limit, offset)


__all__ = [
    "BulkApplyResult",
    "PermissionService",
    "ResolvedToolPermission",
]
