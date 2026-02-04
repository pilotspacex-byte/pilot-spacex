"""File-based hook executor for Claude Agent SDK.

Loads hooks from .claude/hooks.json and executes them on tool use events.
Supports pre/post tool hooks with command execution, deny patterns,
approval requirements, and logging.

Reference: docs/architect/scalable-agent-architecture.md
Design Decisions: DD-003 (Human-in-the-Loop)
"""

from __future__ import annotations

import asyncio
import fnmatch
import json
import logging
import os
import re
import shlex
import subprocess
from pathlib import Path
from typing import Any

from pilot_space.ai.sdk.hook_models import (
    HookDefinition,
    HookResponse,
    HooksConfiguration,
    HookType,
    PermissionDecision,
)

logger = logging.getLogger(__name__)


class FileBasedHookExecutor:
    """Executor for file-based hooks.

    Loads hooks from .claude/hooks.json and executes them
    on tool use events.
    """

    def __init__(self, hooks_file: Path, cwd: Path | None = None) -> None:
        """Initialize executor.

        Args:
            hooks_file: Path to hooks.json file
            cwd: Working directory for command execution
        """
        self._hooks_file = hooks_file
        self._cwd = cwd or hooks_file.parent.parent
        self._config: HooksConfiguration | None = None
        self._loaded = False

    def _ensure_loaded(self) -> None:
        """Lazily load configuration (sync fallback)."""
        if not self._loaded:
            self._config = HooksConfiguration.from_file(self._hooks_file)
            self._loaded = True

    async def _async_ensure_loaded(self) -> None:
        """Lazily load configuration (async, non-blocking I/O)."""
        if not self._loaded:
            self._config = await HooksConfiguration.async_from_file(self._hooks_file)
            self._loaded = True

    @property
    def config(self) -> HooksConfiguration:
        """Get the hooks configuration, loading if necessary."""
        self._ensure_loaded()
        assert self._config is not None
        return self._config

    def reload(self) -> None:
        """Reload configuration from file."""
        self._loaded = False
        self._config = None
        self._ensure_loaded()

    def to_sdk_hooks(self) -> dict[str, list[dict[str, Any]]]:
        """Convert file-based hooks to SDK-compatible format.

        Returns dict mapping hook event names to lists of matchers,
        each with a 'matcher' pattern and 'hooks' callback list.

        The SDK expects hooks in this format:
        {
            'PreToolUse': [
                {'matcher': 'Bash', 'hooks': [callback_fn]}
            ]
        }

        Returns:
            Dict mapping event names to HookMatcher-style dicts.
        """
        sdk_hooks: dict[str, list[dict[str, Any]]] = {}

        # Convert PreToolUse hooks
        if self.config.pre_tool_use:
            sdk_hooks["PreToolUse"] = [
                {
                    "matcher": matcher.matcher,
                    "hooks": [self._create_pre_tool_callback(matcher.hooks)],
                }
                for matcher in self.config.pre_tool_use
            ]

        # Convert PostToolUse hooks
        if self.config.post_tool_use:
            sdk_hooks["PostToolUse"] = [
                {
                    "matcher": matcher.matcher,
                    "hooks": [self._create_post_tool_callback(matcher.hooks)],
                }
                for matcher in self.config.post_tool_use
            ]

        return sdk_hooks

    def _create_pre_tool_callback(self, hooks: list[HookDefinition]):
        """Create SDK-compatible callback for PreToolUse hooks.

        Args:
            hooks: List of hook definitions to execute

        Returns:
            Async callback function compatible with SDK
        """

        async def callback(
            input_data: dict[str, Any],
            tool_use_id: str | None,
            context: Any,
        ) -> dict[str, Any]:
            """SDK hook callback for PreToolUse events."""
            tool_name = input_data.get("tool_name", "")
            tool_input = input_data.get("tool_input", {})
            hook_event_name = input_data.get("hook_event_name", "PreToolUse")

            for hook in hooks:
                # Check if hook matches this tool/input
                if not self._hook_matches_for_callback(hook, tool_name, tool_input):
                    continue

                if hook.type == HookType.DENY:
                    # Check deny patterns
                    value = self._get_check_value(tool_name, tool_input)
                    if value and self._matches_deny_patterns(value, hook.patterns):
                        return {
                            "hookSpecificOutput": {
                                "hookEventName": hook_event_name,
                                "permissionDecision": "deny",
                                "permissionDecisionReason": hook.reason or "Blocked by hook",
                            }
                        }

                if hook.type == HookType.APPROVE:
                    # Check if condition requires approval
                    value = self._get_check_value(tool_name, tool_input)
                    if value and hook.condition:
                        if not self._evaluate_condition(hook.condition, value):
                            return {
                                "hookSpecificOutput": {
                                    "hookEventName": hook_event_name,
                                    "permissionDecision": "ask",
                                    "permissionDecisionReason": hook.reason or "Requires approval",
                                }
                            }

                if hook.type == HookType.PROMPT:
                    # Add context without blocking
                    return {
                        "additionalContext": hook.prompt,
                        "hookSpecificOutput": {
                            "hookEventName": hook_event_name,
                        },
                    }

            # Allow by default
            return {}

        return callback

    def _create_post_tool_callback(self, hooks: list[HookDefinition]):
        """Create SDK-compatible callback for PostToolUse hooks.

        Args:
            hooks: List of hook definitions to execute

        Returns:
            Async callback function compatible with SDK
        """

        async def callback(
            input_data: dict[str, Any],
            tool_use_id: str | None,
            context: Any,
        ) -> dict[str, Any]:
            """SDK hook callback for PostToolUse events."""
            tool_name = input_data.get("tool_name", "")
            tool_input = input_data.get("tool_input", {})
            tool_output = input_data.get("tool_output")
            hook_event_name = input_data.get("hook_event_name", "PostToolUse")

            for hook in hooks:
                if not self._hook_matches_for_callback(hook, tool_name, tool_input):
                    continue

                if hook.type == HookType.LOG:
                    # Log the tool execution
                    log_entry = {
                        "tool": tool_name,
                        "input": tool_input,
                        "output": tool_output,
                    }
                    logger.info("Hook log: %s", json.dumps(log_entry))

            # Post hooks don't block - just observe
            return {
                "hookSpecificOutput": {
                    "hookEventName": hook_event_name,
                }
            }

        return callback

    def _hook_matches_for_callback(
        self,
        hook: HookDefinition,
        tool_name: str,
        tool_input: dict[str, Any],
    ) -> bool:
        """Check if a hook matches for callback execution.

        This is simpler than the full matcher - just checks patterns.

        Args:
            hook: Hook definition to check
            tool_name: Tool name
            tool_input: Tool input parameters

        Returns:
            True if hook should execute
        """
        # If hook has patterns, check them against the value
        if hook.patterns:
            value = self._get_check_value(tool_name, tool_input)
            if not value:
                return False
            # Hook matches if any pattern matches
            return any(fnmatch.fnmatch(value, p) for p in hook.patterns)
        # No patterns means match all
        return True

    def _matches_deny_patterns(self, value: str, patterns: list[str]) -> bool:
        """Check if value matches any deny patterns.

        Args:
            value: Value to check (path, command, etc.)
            patterns: List of glob patterns

        Returns:
            True if value matches any pattern
        """
        return any(fnmatch.fnmatch(value, p) for p in patterns)

    async def execute_pre_tool_hooks(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> HookResponse:
        """Execute pre-tool-use hooks.

        Args:
            tool_name: Name of the tool being invoked
            tool_input: Tool input parameters
            context: Additional context (session_id, user_id, etc.)

        Returns:
            Combined HookResponse from all matching hooks
        """
        await self._async_ensure_loaded()
        responses: list[HookResponse] = []

        for matcher in self.config.pre_tool_use:
            if matcher.matches(tool_name):
                for hook in matcher.hooks:
                    response = await self._execute_hook(hook, tool_name, tool_input, context)
                    responses.append(response)

                    # Stop if hook says don't continue
                    if not response.continue_execution:
                        return response

        return self._merge_responses(responses)

    async def execute_post_tool_hooks(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_output: Any,
        context: dict[str, Any] | None = None,
    ) -> HookResponse:
        """Execute post-tool-use hooks.

        Args:
            tool_name: Name of the tool that was invoked
            tool_input: Tool input parameters
            tool_output: Tool execution result
            context: Additional context

        Returns:
            Combined HookResponse from all matching hooks
        """
        await self._async_ensure_loaded()
        responses: list[HookResponse] = []

        for matcher in self.config.post_tool_use:
            if matcher.matches(tool_name):
                for hook in matcher.hooks:
                    response = await self._execute_hook(
                        hook, tool_name, tool_input, context, tool_output
                    )
                    responses.append(response)

        return self._merge_responses(responses)

    async def _execute_hook(
        self,
        hook: HookDefinition,
        tool_name: str,
        tool_input: dict[str, Any],
        context: dict[str, Any] | None = None,
        tool_output: Any = None,
    ) -> HookResponse:
        """Execute a single hook.

        Args:
            hook: Hook definition to execute
            tool_name: Name of the tool
            tool_input: Tool input parameters
            context: Additional context
            tool_output: Tool output (for post hooks)

        Returns:
            HookResponse from hook execution
        """
        try:
            if hook.type == HookType.COMMAND:
                return await self._execute_command_hook(
                    hook, tool_name, tool_input, context, tool_output
                )

            if hook.type == HookType.DENY:
                return self._execute_deny_hook(hook, tool_name, tool_input)

            if hook.type == HookType.APPROVE:
                return self._execute_approve_hook(hook, tool_name, tool_input)

            if hook.type == HookType.PROMPT:
                return HookResponse(additional_context=hook.prompt)

            if hook.type == HookType.LOG:
                await self._execute_log_hook(hook, tool_name, tool_input, tool_output)
                return HookResponse()

            logger.warning("Unknown hook type: %s", hook.type)
            return HookResponse()

        except Exception:
            logger.exception("Hook execution failed")
            # Don't block tool execution on hook failure by default
            return HookResponse()

    async def _execute_command_hook(
        self,
        hook: HookDefinition,
        tool_name: str,
        tool_input: dict[str, Any],
        context: dict[str, Any] | None = None,
        tool_output: Any = None,
    ) -> HookResponse:
        """Execute a command hook.

        The command receives tool info via environment variables and stdin.
        """
        if not hook.command:
            return HookResponse()

        # Build environment
        env = os.environ.copy()
        env.update(hook.env)
        env["HOOK_TOOL_NAME"] = tool_name
        env["HOOK_TOOL_INPUT"] = json.dumps(tool_input)
        if context:
            env["HOOK_CONTEXT"] = json.dumps(context)
        if tool_output is not None:
            env["HOOK_TOOL_OUTPUT"] = json.dumps(tool_output)

        try:
            # Parse command safely (no shell interpretation)
            try:
                args = shlex.split(hook.command)
            except ValueError:
                logger.warning("Invalid hook command syntax: %s", hook.command)
                return HookResponse()

            if not args:
                logger.warning("Empty hook command after parsing")
                return HookResponse()

            # Run command with timeout (create_subprocess_exec avoids shell injection)
            process = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    *args,
                    cwd=str(self._cwd),
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                ),
                timeout=hook.timeout,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=hook.timeout,
            )

            if process.returncode != 0:
                logger.warning(
                    "Hook command failed: %s, exit=%s, stderr=%s",
                    hook.command,
                    process.returncode,
                    stderr.decode(),
                )
                return HookResponse(
                    continue_execution=False,
                    stop_reason=f"Hook validation failed: {stderr.decode()[:200]}",
                )

            # Parse JSON response from stdout
            if stdout:
                try:
                    data = json.loads(stdout.decode())
                    return HookResponse.from_json(data)
                except json.JSONDecodeError:
                    # Command succeeded but didn't return JSON
                    return HookResponse()

            return HookResponse()

        except TimeoutError:
            logger.warning("Hook command timed out: %s", hook.command)
            return HookResponse(
                continue_execution=False,
                stop_reason=f"Hook timed out after {hook.timeout}s",
            )

    def _execute_deny_hook(
        self,
        hook: HookDefinition,
        tool_name: str,
        tool_input: dict[str, Any],
    ) -> HookResponse:
        """Execute a deny pattern hook.

        Checks if tool input matches any deny patterns.
        """
        # Get the value to check (usually path or command)
        check_value = self._get_check_value(tool_name, tool_input)
        if not check_value:
            return HookResponse()

        for pattern in hook.patterns:
            if fnmatch.fnmatch(check_value, pattern):
                return HookResponse(
                    continue_execution=False,
                    permission_decision=PermissionDecision.DENY,
                    permission_reason=hook.reason or f"Matched deny pattern: {pattern}",
                    stop_reason=hook.reason or f"Blocked by deny pattern: {pattern}",
                )

        return HookResponse()

    def _execute_approve_hook(
        self,
        hook: HookDefinition,
        tool_name: str,
        tool_input: dict[str, Any],
    ) -> HookResponse:
        """Execute an approve condition hook.

        If condition is NOT met, requires explicit approval.
        """
        check_value = self._get_check_value(tool_name, tool_input)
        if not check_value:
            return HookResponse()

        # Simple condition evaluation
        # In production, use a proper expression evaluator
        if hook.condition:
            # Example: "path.startswith('src/')"
            condition_met = self._evaluate_condition(hook.condition, check_value)

            if not condition_met:
                return HookResponse(
                    permission_decision=PermissionDecision.ASK,
                    permission_reason=hook.reason or "Requires approval",
                )

        return HookResponse()

    async def _execute_log_hook(
        self,
        _hook: HookDefinition,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_output: Any = None,
    ) -> None:
        """Execute a log hook."""
        log_entry = {
            "tool": tool_name,
            "input": tool_input,
            "output": tool_output,
        }
        logger.info("Hook log: %s", json.dumps(log_entry))

    def _get_check_value(self, tool_name: str, tool_input: dict[str, Any]) -> str | None:
        """Extract the value to check based on tool type.

        Returns path for file tools, command for Bash, URL for web tools.
        """
        if tool_name in ("Write", "Edit", "Read"):
            return tool_input.get("path") or tool_input.get("file_path")
        if tool_name == "Bash":
            return tool_input.get("command")
        if tool_name in ("WebFetch", "WebSearch"):
            return tool_input.get("url")
        # Return first string value
        for value in tool_input.values():
            if isinstance(value, str):
                return value
        return None

    def _evaluate_condition(self, condition: str, value: str) -> bool:
        """Evaluate a simple condition expression.

        Supports:
        - "path.startswith('prefix')"
        - "path.endswith('.py')"
        - "path.contains('pattern')"
        """
        # Very basic evaluation - in production use a safe expression parser
        if "startswith" in condition:
            match = re.search(r"startswith\(['\"](.+?)['\"]\)", condition)
            if match:
                return value.startswith(match.group(1))

        if "endswith" in condition:
            match = re.search(r"endswith\(['\"](.+?)['\"]\)", condition)
            if match:
                return value.endswith(match.group(1))

        if "contains" in condition:
            match = re.search(r"contains\(['\"](.+?)['\"]\)", condition)
            if match:
                return match.group(1) in value

        return False

    def _merge_responses(self, responses: list[HookResponse]) -> HookResponse:
        """Merge multiple hook responses into one.

        Takes the most restrictive permission decision.
        """
        if not responses:
            return HookResponse()

        # Start with default (allow)
        result = HookResponse()

        for response in responses:
            # Stop execution takes precedence
            if not response.continue_execution:
                return response

            # Most restrictive permission wins
            if response.permission_decision:
                if response.permission_decision == PermissionDecision.DENY:
                    result.permission_decision = PermissionDecision.DENY
                    result.permission_reason = response.permission_reason
                elif (
                    response.permission_decision == PermissionDecision.ASK
                    and result.permission_decision != PermissionDecision.DENY
                ):
                    result.permission_decision = PermissionDecision.ASK
                    result.permission_reason = response.permission_reason

            # Merge updated input
            if response.updated_input:
                if result.updated_input is None:
                    result.updated_input = {}
                result.updated_input.update(response.updated_input)

            # Append additional context
            if response.additional_context:
                if result.additional_context:
                    result.additional_context += "\n" + response.additional_context
                else:
                    result.additional_context = response.additional_context

        return result
