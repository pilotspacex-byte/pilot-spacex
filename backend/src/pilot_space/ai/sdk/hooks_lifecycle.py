"""SDK lifecycle hooks for PostToolUse, UserPromptSubmit, Stop, PreCompact.

Extends the hook pipeline with audit logging, input validation,
budget enforcement, and context preservation during compaction.

Reference: tmp/005-sdk-gap-analysis.md (G8-G11)
"""

from __future__ import annotations

import json
import re
import time
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from pilot_space.infrastructure.database.repositories.audit_log_repository import (
        AuditLogRepository,
    )

logger = get_logger(__name__)

# Max user prompt length (50K characters)
MAX_INPUT_LENGTH = 50_000

# Patterns that indicate prompt injection attempts
INJECTION_PATTERNS: list[str] = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"you\s+are\s+now\s+a\s+different",
    r"system\s*:\s*override",
    r"<\|endoftext\|>",
    r"<\|im_start\|>",
]

_COMPILED_INJECTION_PATTERNS = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]

# Tool name → audit action string mapping
_TOOL_ACTION_MAP: dict[str, str] = {
    "mcp__github__create_pull_request_review": "ai.pr_review",
    "mcp__pilot__enhance_issue": "ai.issue_enhance",
    "mcp__pilot__extract_issues": "ai.issue_extract",
    "mcp__pilot__ghost_text": "ai.ghost_text",
}

# Max bytes for ai_input JSONB field
_MAX_AI_INPUT_BYTES = 10_000


def _truncate(text: str, max_length: int = 500) -> str:
    """Truncate text to max_length, adding ellipsis if truncated."""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def _map_tool_to_action(tool_name: str) -> str:
    """Map SDK tool name to audit action string.

    Args:
        tool_name: Raw tool name from SDK event.

    Returns:
        Dot-notation action string for audit_log.action column.
    """
    return _TOOL_ACTION_MAP.get(tool_name, "ai.tool_call")


def _safe_truncate_json(data: Any, max_bytes: int = _MAX_AI_INPUT_BYTES) -> dict[str, Any]:
    """Serialize data to dict, truncating if serialized size exceeds max_bytes.

    Args:
        data: Value to serialize (dict or any JSON-serializable object).
        max_bytes: Maximum allowed serialized size in bytes.

    Returns:
        Original dict if within limit, or {"_truncated": True, "preview": ...}.
    """
    if not isinstance(data, dict):
        data = {"value": data}

    try:
        serialized = json.dumps(data, default=str)
    except Exception:
        return {"_truncated": True, "error": "serialization_failed"}

    if len(serialized.encode()) <= max_bytes:
        return data

    preview = serialized[: max_bytes // 2]
    return {"_truncated": True, "preview": preview}


def _extract_model(result: Any) -> str | None:
    """Extract model identifier from SDK tool use result.

    Checks .model attribute first, then metadata dict.

    Args:
        result: SDK PostToolUse result object.

    Returns:
        Model string or None if not available.
    """
    model = getattr(result, "model", None)
    if model:
        return str(model)
    metadata = getattr(result, "metadata", None) or {}
    return metadata.get("model")


def _extract_tokens(result: Any) -> int | None:
    """Extract total token count from SDK tool use result.

    Args:
        result: SDK PostToolUse result object.

    Returns:
        Total token count as int, or None if not available.
    """
    # Check .token_usage.total_tokens (test mock shape)
    token_usage = getattr(result, "token_usage", None)
    if token_usage is not None:
        total = getattr(token_usage, "total_tokens", None)
        if total is not None:
            return int(total)

    # Check .usage.total_tokens (SDK native shape)
    usage = getattr(result, "usage", None)
    if usage is not None:
        total = getattr(usage, "total_tokens", None)
        if total is not None:
            return int(total)
        # Some SDK versions use input_tokens + output_tokens
        from pilot_space.ai.infrastructure.cost_tracker import extract_response_usage

        input_t, output_t = extract_response_usage(result)
        if input_t or output_t:
            return input_t + output_t

    return None


class AuditLogHook:
    """PreToolUse + PostToolUse hook for audit logging (G8, G-05, AUDIT-02).

    PreToolUse records tool start time. PostToolUse logs execution
    details (name, input/output summary, duration) for compliance
    and debugging. Fire-and-forget: never blocks or modifies tool output.

    Two operation modes:
    1. Direct audit_repo injection — for unit tests and request-scoped use.
    2. session_factory injection — for out-of-request SDK lifecycle use.

    In both modes, DB writes are non-fatal: exceptions are logged but
    never re-raised so audit failures cannot interrupt AI actions.
    """

    def __init__(
        self,
        event_queue: Any | None = None,
        audit_repo: AuditLogRepository | None = None,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        actor_id: UUID | None = None,
        workspace_id: UUID | None = None,
    ) -> None:
        """Initialize AuditLogHook.

        Args:
            event_queue: Optional asyncio.Queue for SSE audit events.
            audit_repo: Pre-constructed AuditLogRepository (request-scoped use).
            session_factory: Async sessionmaker for out-of-request DB writes.
            actor_id: UUID of the human user who triggered the AI action.
            workspace_id: Workspace UUID for tenant isolation.
        """
        self._event_queue = event_queue
        self._audit_repo = audit_repo
        self._session_factory = session_factory
        self._actor_id = actor_id
        self._workspace_id = workspace_id
        self._tool_start_times: dict[str, float] = {}

    async def on_post_tool_use(self, result: Any, context: Any) -> None:
        """Write an audit_log row after a tool use completes (AUDIT-02).

        This is the structured entry point for request-scoped callers.
        Uses either the injected audit_repo or the session_factory to
        obtain a session. Non-fatal: exceptions are logged but not raised.

        Args:
            result: Tool use result with tool_name, input, output, model,
                    token_usage, rationale attributes.
            context: Request context with workspace_id and user_id attributes.
        """
        from pilot_space.infrastructure.database.models.audit_log import ActorType
        from pilot_space.infrastructure.database.repositories.audit_log_repository import (
            AuditLogRepository as _Repo,
        )

        tool_name = getattr(result, "tool_name", "unknown")
        tool_input = getattr(result, "input", {}) or {}
        tool_output = getattr(result, "output", {}) or {}
        model = _extract_model(result)
        rationale = getattr(result, "rationale", None)
        token_count = _extract_tokens(result)

        workspace_id: UUID | None = getattr(context, "workspace_id", None) or self._workspace_id
        user_id: UUID | None = getattr(context, "user_id", None) or self._actor_id

        try:
            if self._audit_repo is not None:
                await self._audit_repo.create(
                    workspace_id=workspace_id,  # type: ignore[arg-type]
                    actor_id=user_id,
                    actor_type=ActorType.AI,
                    action=_map_tool_to_action(tool_name),
                    resource_type="ai_action",
                    ai_input=_safe_truncate_json(tool_input),
                    ai_output={"text": _truncate(str(tool_output), 500)},
                    ai_model=model,
                    ai_token_cost=token_count,
                    ai_rationale=_truncate(str(rationale), 500) if rationale else None,
                )
            elif self._session_factory is not None and workspace_id is not None:
                async with self._session_factory() as session:
                    repo = _Repo(session)
                    await repo.create(
                        workspace_id=workspace_id,
                        actor_id=user_id,
                        actor_type=ActorType.AI,
                        action=_map_tool_to_action(tool_name),
                        resource_type="ai_action",
                        ai_input=_safe_truncate_json(tool_input),
                        ai_output={"text": _truncate(str(tool_output), 500)},
                        ai_model=model,
                        ai_token_cost=token_count,
                        ai_rationale=_truncate(str(rationale), 500) if rationale else None,
                    )
                    await session.commit()
        except Exception as exc:
            logger.warning("audit_log write failed (non-fatal): %s", exc)

    def to_sdk_hooks(self) -> dict[str, list[dict[str, Any]]]:
        """Create SDK-compatible PreToolUse + PostToolUse hooks."""
        return {
            "PreToolUse": [
                {
                    "matcher": ".*",
                    "hooks": [self._create_start_time_callback()],
                },
            ],
            "PostToolUse": [
                {
                    "matcher": ".*",
                    "hooks": [self._create_audit_callback()],
                },
            ],
        }

    def record_tool_start(self, tool_use_id: str) -> None:
        """Record when a tool starts execution for duration tracking."""
        self._tool_start_times[tool_use_id] = time.monotonic()

    def _create_start_time_callback(self):
        """Create async callback for PreToolUse that records start time."""
        hook_self = self

        async def callback(
            input_data: dict[str, Any],
            tool_use_id: str | None,
            context: Any,
        ) -> dict[str, Any]:
            """Record tool start time before execution."""
            if tool_use_id:
                hook_self.record_tool_start(tool_use_id)
            return {}  # Never modify input

        return callback

    def _create_audit_callback(self):
        """Create async callback for post-tool audit logging with DB write."""
        event_queue = self._event_queue
        start_times = self._tool_start_times
        # Capture private state as local vars to avoid SLF001 in closure
        session_factory = self._session_factory
        workspace_id = self._workspace_id
        actor_id = self._actor_id

        async def callback(
            input_data: dict[str, Any],
            tool_use_id: str | None,
            context: Any,
        ) -> dict[str, Any]:
            """Log tool execution details after completion and write DB row."""
            tool_name = input_data.get("tool_name", "unknown")
            tool_input = input_data.get("tool_input", {})
            tool_output = input_data.get("tool_output", "")

            # Calculate duration if start was recorded
            duration_ms: float | None = None
            if tool_use_id and tool_use_id in start_times:
                elapsed = time.monotonic() - start_times.pop(tool_use_id)
                duration_ms = round(elapsed * 1000, 1)

            audit_entry = {
                "toolUseId": tool_use_id or "unknown",
                "toolName": tool_name,
                "inputSummary": _truncate(json.dumps(tool_input, default=str)),
                "outputSummary": _truncate(str(tool_output)),
                "durationMs": duration_ms,
            }
            logger.info("Tool audit: %s", json.dumps(audit_entry))

            # Push audit event to queue for SSE if available
            if event_queue:
                event = f"event: tool_audit\ndata: {json.dumps(audit_entry)}\n\n"
                await event_queue.put(event)

            # Write DB row if session_factory and workspace context available
            if session_factory and workspace_id:
                from pilot_space.infrastructure.database.models.audit_log import ActorType
                from pilot_space.infrastructure.database.repositories.audit_log_repository import (
                    AuditLogRepository as _Repo,
                )

                try:
                    async with session_factory() as session:
                        repo = _Repo(session)
                        await repo.create(
                            workspace_id=workspace_id,
                            actor_id=actor_id,
                            actor_type=ActorType.AI,
                            action=_map_tool_to_action(tool_name),
                            resource_type="ai_action",
                            ai_input=_safe_truncate_json(tool_input),
                            ai_output={"text": _truncate(str(tool_output), 500)},
                            ai_model=None,
                            ai_token_cost=None,
                            ai_rationale=_truncate(str(tool_output), 500),
                        )
                        await session.commit()
                except Exception as exc:
                    logger.warning("audit_log write failed in SDK callback (non-fatal): %s", exc)

            return {}  # Never modify output

        return callback


class InputValidationHook:
    """UserPromptSubmit hook for input validation (G9).

    Validates user prompt length and checks for known prompt
    injection patterns. Returns deny decision if triggered.
    """

    def __init__(self, max_length: int = MAX_INPUT_LENGTH) -> None:
        self._max_length = max_length

    def to_sdk_hooks(self) -> dict[str, list[dict[str, Any]]]:
        """Create SDK-compatible UserPromptSubmit hooks."""
        return {
            "UserPromptSubmit": [
                {
                    "matcher": ".*",
                    "hooks": [self._create_validation_callback()],
                },
            ],
        }

    def _create_validation_callback(self):
        """Create async callback for input validation."""
        max_length = self._max_length

        async def callback(
            input_data: dict[str, Any],
            tool_use_id: str | None,
            context: Any,
        ) -> dict[str, Any]:
            """Validate user prompt before submission."""
            prompt_content = input_data.get("prompt_content", "")

            # Length check
            if len(prompt_content) > max_length:
                logger.warning(
                    "Input rejected: length %d exceeds max %d",
                    len(prompt_content),
                    max_length,
                )
                return {
                    "hookSpecificOutput": {
                        "hookEventName": "UserPromptSubmit",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": (
                            f"Input exceeds maximum length "
                            f"({len(prompt_content):,} > {max_length:,} chars)"
                        ),
                    },
                }

            # Prompt injection pattern check
            for pattern in _COMPILED_INJECTION_PATTERNS:
                if pattern.search(prompt_content):
                    logger.warning(
                        "Input rejected: injection pattern detected: %s",
                        pattern.pattern,
                    )
                    return {
                        "hookSpecificOutput": {
                            "hookEventName": "UserPromptSubmit",
                            "permissionDecision": "deny",
                            "permissionDecisionReason": ("Input contains disallowed pattern"),
                        },
                    }

            return {}  # Allow

        return callback


class BudgetStopHook:
    """Stop hook for budget enforcement (G10).

    Tracks accumulated cost across conversation turns. Emits
    budget_warning SSE at 80% threshold and stops execution
    when budget is exhausted.
    """

    WARNING_THRESHOLD = 0.8

    def __init__(
        self,
        max_budget_usd: float,
        event_queue: Any | None = None,
    ) -> None:
        self._max_budget = max_budget_usd
        self._accumulated_cost = 0.0
        self._event_queue = event_queue
        self._warning_emitted = False

    @property
    def accumulated_cost(self) -> float:
        """Current accumulated cost in USD."""
        return self._accumulated_cost

    def to_sdk_hooks(self) -> dict[str, list[dict[str, Any]]]:
        """Create SDK-compatible Stop hooks."""
        return {
            "Stop": [
                {
                    "matcher": ".*",
                    "hooks": [self._create_stop_callback()],
                },
            ],
        }

    def _create_stop_callback(self):
        """Create async callback for budget stop check."""
        event_queue = self._event_queue

        async def callback(
            input_data: dict[str, Any],
            tool_use_id: str | None,
            context: Any,
        ) -> dict[str, Any]:
            """Check budget and stop if exceeded."""
            cost_usd = input_data.get("cost_usd", 0.0)
            self._accumulated_cost += cost_usd

            if self._max_budget <= 0:
                return {}

            ratio = self._accumulated_cost / self._max_budget

            # Emit warning at 80% threshold (once)
            if ratio >= self.WARNING_THRESHOLD and not self._warning_emitted:
                self._warning_emitted = True
                logger.warning(
                    "Budget warning: %.1f%% consumed ($%.4f / $%.2f)",
                    ratio * 100,
                    self._accumulated_cost,
                    self._max_budget,
                )
                if event_queue:
                    warning_data = {
                        "ratio": round(ratio, 3),
                        "accumulated_usd": round(self._accumulated_cost, 4),
                        "max_budget_usd": self._max_budget,
                    }
                    event = f"event: budget_warning\ndata: {json.dumps(warning_data)}\n\n"
                    await event_queue.put(event)

            # Stop if budget exceeded
            if self._accumulated_cost >= self._max_budget:
                logger.info(
                    "Budget exhausted: $%.4f >= $%.2f, stopping",
                    self._accumulated_cost,
                    self._max_budget,
                )
                return {
                    "hookSpecificOutput": {
                        "stop": True,
                        "reason": (
                            f"Budget limit reached "
                            f"(${self._accumulated_cost:.2f} / "
                            f"${self._max_budget:.2f})"
                        ),
                    },
                }

            return {}

        return callback


class ContextPreservationHook:
    """PreCompact hook for context preservation (G11).

    Extracts key context before SDK compacts the conversation,
    ensuring critical information (task description, decisions,
    pending approvals) survives context window reduction.
    """

    def __init__(self, preserve_keys: list[str] | None = None) -> None:
        self._preserve_keys = preserve_keys or [
            "current_task",
            "key_decisions",
            "pending_approvals",
            "tool_results_summary",
        ]

    def to_sdk_hooks(self) -> dict[str, list[dict[str, Any]]]:
        """Create SDK-compatible PreCompact hooks."""
        return {
            "PreCompact": [
                {
                    "matcher": ".*",
                    "hooks": [self._create_preservation_callback()],
                },
            ],
        }

    def _create_preservation_callback(self):
        """Create async callback for context preservation."""
        preserve_keys = self._preserve_keys

        async def callback(
            input_data: dict[str, Any],
            tool_use_id: str | None,
            context: Any,
        ) -> dict[str, Any]:
            """Extract and preserve key context before compaction."""
            messages = input_data.get("messages", [])

            preserved: dict[str, str] = {}

            # Extract last assistant tool results summary
            tool_results: list[str] = []
            for msg in reversed(messages):
                if msg.get("role") == "tool" and len(tool_results) < 5:
                    name = msg.get("name", "unknown")
                    content = _truncate(str(msg.get("content", "")), 200)
                    tool_results.append(f"- {name}: {content}")

            if tool_results and "tool_results_summary" in preserve_keys:
                preserved["tool_results_summary"] = "\n".join(tool_results)

            # Extract pending decisions from last user/assistant messages
            for msg in reversed(messages[-10:]):
                content = str(msg.get("content", ""))
                role = msg.get("role", "")

                if role == "user" and "current_task" in preserve_keys:
                    if "current_task" not in preserved:
                        preserved["current_task"] = _truncate(content, 300)

                if role == "assistant" and "key_decisions" in preserve_keys:
                    if "key_decisions" not in preserved:
                        preserved["key_decisions"] = _truncate(content, 300)

            if preserved:
                logger.info(
                    "PreCompact: preserving %d context keys",
                    len(preserved),
                )
                return {
                    "hookSpecificOutput": {
                        "preserved_context": json.dumps(preserved),
                    },
                }

            return {}

        return callback
