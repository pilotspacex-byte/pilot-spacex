"""Data models for file-based hooks support.

Contains enums, dataclasses, and configuration models used by the
file-based hook system for Claude Agent SDK.

Reference: docs/architect/scalable-agent-architecture.md
Design Decisions: DD-003 (Human-in-the-Loop)
"""

from __future__ import annotations

import asyncio
import fnmatch
import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class HookType(Enum):
    """Types of hooks that can be configured."""

    COMMAND = "command"  # Execute external command
    DENY = "deny"  # Deny based on patterns
    APPROVE = "approve"  # Require explicit approval
    PROMPT = "prompt"  # Add prompt to Claude
    LOG = "log"  # Log to file/service


class PermissionDecision(Enum):
    """Hook permission decisions."""

    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


@dataclass
class HookResponse:
    """Response from a hook execution.

    Attributes:
        continue_execution: Whether to continue with tool execution
        stop_reason: Reason if execution should stop
        suppress_output: Whether to hide hook output from user
        permission_decision: Permission decision (allow/deny/ask)
        permission_reason: Reason for permission decision
        updated_input: Modified tool input parameters
        additional_context: Extra context for Claude
    """

    continue_execution: bool = True
    stop_reason: str | None = None
    suppress_output: bool = False
    permission_decision: PermissionDecision | None = None
    permission_reason: str | None = None
    updated_input: dict[str, Any] | None = None
    additional_context: str | None = None

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> HookResponse:
        """Parse hook response from JSON output."""
        specific = data.get("hookSpecificOutput", {})

        decision = None
        if specific.get("permissionDecision"):
            decision = PermissionDecision(specific["permissionDecision"])

        return cls(
            continue_execution=data.get("continue", True),
            stop_reason=data.get("stopReason"),
            suppress_output=data.get("suppressOutput", False),
            permission_decision=decision,
            permission_reason=specific.get("permissionDecisionReason"),
            updated_input=specific.get("updatedInput"),
            additional_context=specific.get("additionalContext"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result: dict[str, Any] = {
            "continue": self.continue_execution,
            "suppressOutput": self.suppress_output,
        }

        if self.stop_reason:
            result["stopReason"] = self.stop_reason

        specific: dict[str, Any] = {}
        if self.permission_decision:
            specific["permissionDecision"] = self.permission_decision.value
        if self.permission_reason:
            specific["permissionDecisionReason"] = self.permission_reason
        if self.updated_input:
            specific["updatedInput"] = self.updated_input
        if self.additional_context:
            specific["additionalContext"] = self.additional_context

        if specific:
            result["hookSpecificOutput"] = specific

        return result


@dataclass
class HookDefinition:
    """Single hook definition.

    Attributes:
        type: Type of hook (command, deny, approve, etc.)
        command: Command to execute (for command type)
        patterns: Patterns to match (for deny type)
        condition: Condition expression (for approve type)
        prompt: Prompt text (for prompt type)
        timeout: Execution timeout in seconds
        env: Additional environment variables
        reason: Reason for hook action
    """

    type: HookType
    command: str | None = None
    patterns: list[str] = field(default_factory=list)
    condition: str | None = None
    prompt: str | None = None
    timeout: int = 30
    env: dict[str, str] = field(default_factory=dict)
    reason: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HookDefinition:
        """Parse hook definition from dictionary."""
        return cls(
            type=HookType(data["type"]),
            command=data.get("command"),
            patterns=data.get("patterns", []),
            condition=data.get("condition"),
            prompt=data.get("prompt"),
            timeout=data.get("timeout", 30),
            env=data.get("env", {}),
            reason=data.get("reason"),
        )


@dataclass
class HookMatcher:
    """Hook matcher with pattern and hook definitions.

    Attributes:
        matcher: Pattern to match tool names (glob syntax or regex)
        description: Human-readable description
        hooks: List of hooks to execute when matched
    """

    matcher: str
    description: str = ""
    hooks: list[HookDefinition] = field(default_factory=list)

    def matches(self, tool_name: str) -> bool:
        """Check if tool name matches this matcher's pattern.

        Supports:
        - Regex patterns: /^Bash.*/
        - OR patterns: "Write|Edit"
        - Glob patterns: "Web*", "*"
        - Exact match: "Bash"
        """
        pattern = self.matcher

        # Handle regex patterns first (to avoid conflicts with glob * check)
        if pattern.startswith("/") and pattern.endswith("/"):
            regex = pattern[1:-1]
            return bool(re.match(regex, tool_name))

        # Handle OR patterns (must check before glob since | is not a glob char)
        if "|" in pattern:
            patterns = pattern.split("|")
            return any(fnmatch.fnmatch(tool_name, p.strip()) for p in patterns)

        # Handle glob patterns
        if "*" in pattern or "?" in pattern:
            return fnmatch.fnmatch(tool_name, pattern)

        # Exact match
        return tool_name == pattern

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HookMatcher:
        """Parse hook matcher from dictionary."""
        hooks = [HookDefinition.from_dict(h) for h in data.get("hooks", [])]
        return cls(
            matcher=data["matcher"],
            description=data.get("description", ""),
            hooks=hooks,
        )


@dataclass
class HooksConfiguration:
    """Complete hooks configuration from hooks.json.

    Attributes:
        version: Configuration format version
        pre_tool_use: Hooks to run before tool execution
        post_tool_use: Hooks to run after tool execution
        stop: Hooks to run on session stop
        subagent_start: Hooks to run on subagent start
        subagent_stop: Hooks to run on subagent stop
    """

    version: str = "1.0"
    pre_tool_use: list[HookMatcher] = field(default_factory=list)
    post_tool_use: list[HookMatcher] = field(default_factory=list)
    stop: list[HookMatcher] = field(default_factory=list)
    subagent_start: list[HookMatcher] = field(default_factory=list)
    subagent_stop: list[HookMatcher] = field(default_factory=list)

    @classmethod
    def from_file(cls, path: Path) -> HooksConfiguration:
        """Load hooks configuration from JSON file (sync)."""
        if not path.exists():
            return cls()

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls.from_dict(data)
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to parse hooks.json: %s", e)
            return cls()

    @classmethod
    async def async_from_file(cls, path: Path) -> HooksConfiguration:
        """Load hooks configuration from JSON file (async, non-blocking)."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, cls.from_file, path)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HooksConfiguration:
        """Parse hooks configuration from dictionary."""
        hooks = data.get("hooks", {})

        return cls(
            version=data.get("version", "1.0"),
            pre_tool_use=[HookMatcher.from_dict(m) for m in hooks.get("PreToolUse", [])],
            post_tool_use=[HookMatcher.from_dict(m) for m in hooks.get("PostToolUse", [])],
            stop=[HookMatcher.from_dict(m) for m in hooks.get("Stop", [])],
            subagent_start=[HookMatcher.from_dict(m) for m in hooks.get("SubagentStart", [])],
            subagent_stop=[HookMatcher.from_dict(m) for m in hooks.get("SubagentStop", [])],
        )
