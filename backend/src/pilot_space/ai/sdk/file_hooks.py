"""File-based hooks support for Claude Agent SDK.

Enables configuration of pre/post tool use hooks via .claude/hooks.json files.
This provides a declarative, non-code approach to adding validation, logging,
and policy enforcement to tool executions.

Reference: docs/architect/scalable-agent-architecture.md
Design Decisions: DD-003 (Human-in-the-Loop)

This module re-exports all symbols from:
- hook_models: Data models (enums, dataclasses, configuration)
- hook_executor: FileBasedHookExecutor implementation

All public symbols remain importable from this module path for
backward compatibility.
"""

from pilot_space.ai.sdk.hook_executor import FileBasedHookExecutor
from pilot_space.ai.sdk.hook_models import (
    HookDefinition,
    HookMatcher,
    HookResponse,
    HooksConfiguration,
    HookType,
    PermissionDecision,
)

__all__ = [
    "FileBasedHookExecutor",
    "HookDefinition",
    "HookMatcher",
    "HookResponse",
    "HookType",
    "HooksConfiguration",
    "PermissionDecision",
]
