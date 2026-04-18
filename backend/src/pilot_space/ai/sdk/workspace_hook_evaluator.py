"""WorkspaceHookEvaluator -- runtime evaluation of declarative hook rules.

Phase 83 -- evaluates workspace-scoped hook rules against tool invocations.
Loads rules from DB (Redis-cached, 5min TTL via HookRuleService), matches
tool names against glob/regex/exact patterns, and returns allow/deny/
require_approval.

DD-003 INVARIANT: Even if a rule says 'allow' for a CRITICAL tool,
the evaluator returns 'require_approval' instead. This is defense-in-depth
-- admins can *configure* allow rules, but the runtime guard is hardcoded.

Runs BEFORE PermissionCheckHook in the PreToolUse chain.
"""

from __future__ import annotations

import fnmatch
import re
import time
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pilot_space.ai.sdk.permission_handler import (
    ActionClassification,
    PermissionHandler,
)
from pilot_space.domain.hooks.hook_action import HookAction
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from pilot_space.application.services.hooks.hook_rule_service import (
        HookRuleService,
    )

logger = get_logger(__name__)


class WorkspaceHookEvaluator:
    """Evaluates workspace-scoped declarative hook rules.

    Loads rules from DB (Redis-cached, 5min TTL), matches tool names
    against glob/regex/exact patterns, and returns allow/deny/require_approval.

    DD-003 INVARIANT: Even if a rule says 'allow' for a CRITICAL tool,
    the evaluator returns 'require_approval' instead.

    Runs BEFORE PermissionCheckHook in the PreToolUse chain.

    Attributes:
        CACHE_TTL_SECONDS: Redis cache TTL for workspace rules.
        CACHE_KEY_PREFIX: Redis key prefix for cached rules.
    """

    CACHE_TTL_SECONDS = 300
    CACHE_KEY_PREFIX = "hooks:workspace:"

    def __init__(
        self,
        workspace_id: UUID,
        redis_client: Any | None = None,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        hook_rule_service: HookRuleService | None = None,
    ) -> None:
        """Initialize evaluator.

        Args:
            workspace_id: Workspace UUID for rule scoping.
            redis_client: RedisClient for direct cache access (fallback path).
            session_factory: Async sessionmaker for audit log writes.
            hook_rule_service: Service for loading cached rules (preferred path).
        """
        self._workspace_id = workspace_id
        self._redis_client = redis_client
        self._session_factory = session_factory
        self._hook_rule_service = hook_rule_service

    async def evaluate(self, tool_name: str) -> HookAction | None:
        """Evaluate workspace hook rules against a tool invocation.

        Loads rules in priority order, matches the tool name against each
        rule's pattern. On first match, applies DD-003 guard for CRITICAL
        tools and returns the effective action.

        Args:
            tool_name: Full tool name (may include MCP prefix).

        Returns:
            HookAction if a rule matches, None if no rule matches
            (downstream hooks decide).
        """
        start = time.monotonic()

        # Strip MCP prefix for matching (same as PermissionCheckHook)
        from pilot_space.ai.sdk.hooks import PermissionCheckHook

        bare_name = PermissionCheckHook.strip_mcp_prefix(tool_name)

        rules = await self._load_rules()
        if not rules:
            return None

        for rule in rules:
            pattern = rule.get("tool_pattern", "")
            if not self._matches(pattern, bare_name):
                continue

            # First match wins
            action_str = rule.get("action", "")
            rule_name = rule.get("name", "unknown")

            try:
                action = HookAction(action_str)
            except ValueError:
                logger.warning(
                    "Invalid hook action '%s' in rule '%s'; skipping",
                    action_str,
                    rule_name,
                )
                continue

            # DD-003 GUARD: CRITICAL tools cannot be auto-approved
            # even if a workspace hook says "allow". This is hardcoded
            # defense-in-depth -- the classification table is the
            # authoritative source of truth for CRITICAL status.
            if action == HookAction.ALLOW:
                classification = PermissionHandler.ACTION_CLASSIFICATIONS.get(
                    bare_name,
                )
                if classification == ActionClassification.CRITICAL_REQUIRE_APPROVAL:
                    logger.warning(
                        "DD-003 guard: hook rule '%s' tried to allow CRITICAL "
                        "tool '%s' -- overriding to require_approval",
                        rule_name,
                        bare_name,
                    )
                    action = HookAction.REQUIRE_APPROVAL

            elapsed_ms = (time.monotonic() - start) * 1000
            await self._log_evaluation(
                rule_name=rule_name,
                tool_name=tool_name,
                decision=action.value,
                latency_ms=elapsed_ms,
            )
            return action

        # No rule matched
        return None

    @staticmethod
    def _matches(pattern: str, tool_name: str) -> bool:
        """Check if tool name matches a pattern.

        Supports the same pattern types as HookMatcher.matches():
        - Regex: pattern wrapped in ``/`` delimiters.
        - OR: ``|`` separated sub-patterns (fnmatch each).
        - Glob: contains ``*`` or ``?``.
        - Exact: literal string comparison.

        Args:
            pattern: Pattern string from rule configuration.
            tool_name: Bare tool name to match against.

        Returns:
            True if the tool name matches the pattern.
        """
        # Regex: /pattern/
        if pattern.startswith("/") and pattern.endswith("/") and len(pattern) > 2:
            regex_body = pattern[1:-1]
            try:
                return bool(re.match(regex_body, tool_name))
            except re.error:
                logger.warning("Invalid regex in hook rule: %s", pattern)
                return False

        # OR pattern: A|B
        if "|" in pattern:
            parts = pattern.split("|")
            return any(fnmatch.fnmatch(tool_name, p.strip()) for p in parts)

        # Glob: * or ?
        if "*" in pattern or "?" in pattern:
            return fnmatch.fnmatch(tool_name, pattern)

        # Exact match
        return tool_name == pattern

    async def _load_rules(self) -> list[dict[str, Any]]:
        """Load enabled rules for the workspace.

        Prefers ``hook_rule_service.get_cached_rules()`` which handles
        Redis caching and DB fallback internally. If no service is
        available, returns an empty list (graceful degradation).

        Returns:
            List of rule dicts sorted by priority (ascending).
        """
        if self._hook_rule_service is not None:
            try:
                return await self._hook_rule_service.get_cached_rules(
                    self._workspace_id,
                )
            except Exception:
                logger.warning(
                    "Failed to load hook rules for workspace %s; "
                    "skipping workspace hooks",
                    self._workspace_id,
                    exc_info=True,
                )
                return []

        # No service available -- degrade gracefully
        return []

    async def _log_evaluation(
        self,
        rule_name: str,
        tool_name: str,
        decision: str,
        latency_ms: float,
    ) -> None:
        """Write an audit log entry for this hook evaluation.

        Non-fatal: follows the hooks_lifecycle.py pattern (lines 324-347).
        Audit failures are logged as warnings but never interrupt the
        tool execution pipeline.

        Args:
            rule_name: Name of the matched rule.
            tool_name: Full tool name that was evaluated.
            decision: Resulting action (allow/deny/require_approval).
            latency_ms: Time taken for evaluation in milliseconds.
        """
        if self._session_factory is None:
            return

        try:
            from pilot_space.infrastructure.database.models.audit_log import (
                ActorType,
            )
            from pilot_space.infrastructure.database.repositories.audit_log_repository import (
                AuditLogRepository,
            )

            async with self._session_factory() as session:
                repo = AuditLogRepository(session)
                await repo.create(
                    workspace_id=self._workspace_id,
                    actor_id=None,
                    actor_type=ActorType.SYSTEM,
                    action="hook.evaluation",
                    resource_type="ai_hook",
                    payload={
                        "hook_name": rule_name,
                        "tool_name": tool_name,
                        "decision": decision,
                        "latency_ms": round(latency_ms, 2),
                    },
                )
                await session.commit()
        except Exception as exc:
            logger.warning(
                "Hook evaluation audit write failed (non-fatal): %s",
                exc,
            )

    def to_sdk_hooks(self) -> dict[str, list[dict[str, Any]]]:
        """Convert to SDK-compatible hooks format.

        Returns a PreToolUse catch-all matcher that routes through
        ``evaluate()`` for every tool call.

        Returns:
            Dict mapping ``PreToolUse`` to a list with one matcher.
        """
        return {
            "PreToolUse": [
                {
                    "matcher": ".*",
                    "hooks": [self._create_callback()],
                    "timeout": 30,
                },
            ],
        }

    def _create_callback(self):
        """Create SDK-compatible async callback for hook evaluation.

        Returns:
            Async callback that bridges the evaluator to SDK format.
        """
        evaluator = self

        async def callback(
            input_data: dict[str, Any],
            tool_use_id: str | None,
            context: Any,
        ) -> dict[str, Any]:
            """SDK hook callback that evaluates workspace rules."""
            raw_tool_name = input_data.get("tool_name", "")
            hook_event_name = input_data.get(
                "hook_event_name",
                "PreToolUse",
            )

            result = await evaluator.evaluate(raw_tool_name)

            if result == HookAction.DENY:
                return {
                    "hookSpecificOutput": {
                        "hookEventName": hook_event_name,
                        "permissionDecision": "deny",
                        "permissionDecisionReason": (
                            "Blocked by workspace hook rule"
                        ),
                    },
                }

            # ALLOW, REQUIRE_APPROVAL, or None: return empty dict.
            # For REQUIRE_APPROVAL the downstream PermissionCheckHook
            # handles the approval flow. For ALLOW / None the tool
            # proceeds to the next hook in the chain.
            return {}

        return callback


__all__ = ["WorkspaceHookEvaluator"]
