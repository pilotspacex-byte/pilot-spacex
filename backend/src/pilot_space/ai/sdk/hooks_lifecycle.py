"""SDK lifecycle hooks for PostToolUse, UserPromptSubmit, Stop, PreCompact.

Extends the hook pipeline with audit logging, input validation,
budget enforcement, and context preservation during compaction.

Reference: tmp/005-sdk-gap-analysis.md (G8-G11)
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

logger = logging.getLogger(__name__)

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


def _truncate(text: str, max_length: int = 500) -> str:
    """Truncate text to max_length, adding ellipsis if truncated."""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


class AuditLogHook:
    """PostToolUse hook for audit logging (G8).

    Logs tool execution details (name, input/output summary,
    duration) for compliance and debugging. Fire-and-forget:
    never blocks or modifies tool output.
    """

    def __init__(self, event_queue: Any | None = None) -> None:
        self._event_queue = event_queue
        self._tool_start_times: dict[str, float] = {}

    def to_sdk_hooks(self) -> dict[str, list[dict[str, Any]]]:
        """Create SDK-compatible PostToolUse hooks."""
        return {
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

    def _create_audit_callback(self):
        """Create async callback for post-tool audit logging."""
        event_queue = self._event_queue
        start_times = self._tool_start_times

        async def callback(
            input_data: dict[str, Any],
            tool_use_id: str | None,
            context: Any,
        ) -> dict[str, Any]:
            """Log tool execution details after completion."""
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
