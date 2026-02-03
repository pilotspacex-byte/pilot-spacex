"""Pre-tool-use hooks for Claude Agent SDK.

Provides hooks that intercept tool calls before execution to:
- Enforce permission/approval flow (DD-003)
- Validate tool parameters
- Log tool usage for auditing
- Implement rate limiting

Reference: docs/architect/claude-agent-sdk-architecture.md
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar
from uuid import UUID, uuid4

from pilot_space.ai.sdk.hooks_lifecycle import (
    AuditLogHook,
    BudgetStopHook,
    ContextPreservationHook,
    InputValidationHook,
)

if TYPE_CHECKING:
    from pilot_space.ai.sdk.file_hooks import FileBasedHookExecutor
    from pilot_space.ai.sdk.permission_handler import PermissionHandler

logger = logging.getLogger(__name__)


@dataclass
class ToolCallContext:
    """Context for a tool call about to be executed.

    Attributes:
        tool_name: Name of tool being called
        tool_input: Input parameters for tool
        workspace_id: Workspace UUID for RLS
        user_id: User UUID for attribution
        agent_name: Agent making the tool call
        session_id: Optional session ID for multi-turn
        metadata: Additional context metadata
    """

    tool_name: str
    tool_input: dict[str, Any]
    workspace_id: UUID
    user_id: UUID
    agent_name: str
    session_id: UUID | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class HookResult:
    """Result from pre-tool-use hook.

    Attributes:
        allow: Whether to allow tool execution
        reason: Human-readable reason for decision
        modified_input: Optional modified tool input
        requires_approval: Whether tool call requires approval
        approval_id: UUID of approval request if requires_approval=True
    """

    allow: bool
    reason: str = ""
    modified_input: dict[str, Any] | None = None
    requires_approval: bool = False
    approval_id: UUID | None = None

    @classmethod
    def allow_execution(
        cls,
        reason: str = "Tool execution allowed",
        modified_input: dict[str, Any] | None = None,
    ) -> HookResult:
        """Create result allowing execution."""
        return cls(allow=True, reason=reason, modified_input=modified_input)

    @classmethod
    def deny_execution(cls, reason: str) -> HookResult:
        """Create result denying execution."""
        return cls(allow=False, reason=reason)

    @classmethod
    def requires_approval_result(
        cls,
        approval_id: UUID,
        reason: str,
    ) -> HookResult:
        """Create result requiring approval."""
        return cls(
            allow=False,
            requires_approval=True,
            approval_id=approval_id,
            reason=reason,
        )


class PreToolUseHook(ABC):
    """Abstract base class for pre-tool-use hooks.

    Hooks are called before a tool is executed, allowing:
    - Permission checks
    - Input validation
    - Parameter modification
    - Auditing

    Subclasses must implement should_execute() method.

    Usage:
        class MyHook(PreToolUseHook):
            async def should_execute(self, context):
                if context.tool_name == "delete_issue":
                    return HookResult.deny_execution("Not allowed")
                return HookResult.allow_execution()

        hook = MyHook()
        result = await hook.should_execute(context)
    """

    @abstractmethod
    async def should_execute(self, context: ToolCallContext) -> HookResult:
        """Determine if tool execution should proceed.

        Args:
            context: Tool call context with workspace/user/tool info

        Returns:
            HookResult indicating whether to allow execution
        """


class PermissionCheckHook(PreToolUseHook):
    """Hook that enforces DD-003 permission/approval flow.

    Checks if tool call requires approval based on:
    - Tool name classification (AUTO, DEFAULT, CRITICAL)
    - Workspace-specific overrides
    - Destructive action detection

    Usage:
        hook = PermissionCheckHook(permission_handler)
        result = await hook.should_execute(context)
        if result.requires_approval:
            # Wait for human approval
            await wait_for_approval(result.approval_id)
    """

    # Tools that map to actions requiring approval
    TOOL_ACTION_MAPPING: ClassVar[dict[str, str]] = {
        # Database write tools
        "create_issue_in_db": "create_issue",
        "update_issue_in_db": "update_issue",
        "delete_issue_from_db": "delete_issue",
        "create_annotation_in_db": "create_annotation",
        # GitHub tools
        "merge_pull_request": "merge_pr",
        "close_pull_request": "close_issue",
        "link_commit_to_issue": "link_commit",
        # Task decomposition
        "create_subtasks": "decompose_tasks",
    }

    def __init__(self, permission_handler: PermissionHandler):
        """Initialize hook with permission handler.

        Args:
            permission_handler: PermissionHandler for approval flow
        """
        self._permission_handler = permission_handler

    async def should_execute(self, context: ToolCallContext) -> HookResult:
        """Check if tool execution requires approval.

        Args:
            context: Tool call context

        Returns:
            HookResult with permission decision
        """
        # Map tool name to action name
        action_name = self.TOOL_ACTION_MAPPING.get(context.tool_name)

        # If tool not mapped, allow execution (read-only tools)
        if not action_name:
            return HookResult.allow_execution(reason=f"Tool '{context.tool_name}' is read-only")

        # Check permission for mapped action
        permission_result = await self._permission_handler.check_permission(
            workspace_id=context.workspace_id,
            user_id=context.user_id,
            agent_name=context.agent_name,
            action_name=action_name,
            description=self._build_description(context),
            proposed_changes=context.tool_input,
        )

        if permission_result.requires_approval:
            return HookResult.requires_approval_result(
                approval_id=permission_result.approval_id,  # type: ignore
                reason=permission_result.reason,
            )

        return HookResult.allow_execution(reason=permission_result.reason)

    def _build_description(self, context: ToolCallContext) -> str:
        """Build human-readable description of proposed action.

        Args:
            context: Tool call context

        Returns:
            Description string for approval UI
        """
        tool_name = context.tool_name
        tool_input = context.tool_input

        if tool_name == "create_issue_in_db":
            return f"Create issue: {tool_input.get('name', 'Untitled')}"
        if tool_name == "update_issue_in_db":
            return f"Update issue: {tool_input.get('issue_id')}"
        if tool_name == "delete_issue_from_db":
            return f"Delete issue: {tool_input.get('issue_id')}"
        if tool_name == "merge_pull_request":
            return f"Merge PR: {tool_input.get('pr_number')}"
        if tool_name == "create_subtasks":
            return f"Create {len(tool_input.get('subtasks', []))} subtasks"
        return f"Execute {tool_name}"


class ValidationHook(PreToolUseHook):
    """Hook that validates tool parameters before execution.

    Ensures:
    - Required parameters are present
    - Parameter types are correct
    - Values are within valid ranges
    - UUIDs are valid format

    Usage:
        hook = ValidationHook()
        result = await hook.should_execute(context)
        if not result.allow:
            # Handle validation error
            logger.error(result.reason)
    """

    async def should_execute(self, context: ToolCallContext) -> HookResult:
        """Validate tool parameters.

        Args:
            context: Tool call context

        Returns:
            HookResult indicating if parameters are valid
        """
        tool_input = context.tool_input

        # Validate UUIDs
        uuid_fields = ["workspace_id", "user_id", "issue_id", "note_id"]
        for field in uuid_fields:
            if field in tool_input:
                try:
                    UUID(str(tool_input[field]))
                except (ValueError, TypeError):
                    return HookResult.deny_execution(
                        reason=f"Invalid UUID format for field '{field}'"
                    )

        # Validate required fields per tool
        if context.tool_name == "create_issue_in_db":
            required = ["workspace_id", "project_id", "name"]
            missing = [f for f in required if f not in tool_input]
            if missing:
                return HookResult.deny_execution(
                    reason=f"Missing required fields: {', '.join(missing)}"
                )

        # All validations passed
        return HookResult.allow_execution(reason="Parameters validated")


class CompositeHook(PreToolUseHook):
    """Composite hook that runs multiple hooks in sequence.

    Executes hooks in order, stopping at first denial.

    Usage:
        hook = CompositeHook([
            ValidationHook(),
            PermissionCheckHook(permission_handler),
        ])
        result = await hook.should_execute(context)
    """

    def __init__(self, hooks: list[PreToolUseHook]):
        """Initialize with list of hooks.

        Args:
            hooks: List of hooks to execute in order
        """
        self._hooks = hooks

    async def should_execute(self, context: ToolCallContext) -> HookResult:
        """Execute all hooks in sequence.

        Args:
            context: Tool call context

        Returns:
            First denial result, or allow if all pass
        """
        for hook in self._hooks:
            result = await hook.should_execute(context)
            if not result.allow:
                return result

        return HookResult.allow_execution(reason="All hooks passed")


class PermissionAwareHookExecutor:
    """Composes FileBasedHookExecutor with DD-003 PermissionCheckHook.

    Produces SDK-compatible hooks dict where PreToolUse includes both
    file-based hooks AND the permission check hook. The permission hook
    intercepts mapped tool calls and returns "ask"/"deny" decisions
    that the SDK handles natively (pausing execution for approval).

    Usage:
        executor = PermissionAwareHookExecutor(
            permission_handler=permission_handler,
            workspace_id=ctx.workspace_id,
            user_id=ctx.user_id,
            file_hook_executor=file_hooks,  # optional
        )
        sdk_hooks = executor.to_sdk_hooks()
    """

    def __init__(
        self,
        permission_handler: PermissionHandler,
        workspace_id: UUID,
        user_id: UUID,
        agent_name: str = "PilotSpaceAgent",
        file_hook_executor: FileBasedHookExecutor | None = None,
        event_queue: Any | None = None,
        max_budget_usd: float | None = None,
    ) -> None:
        """Initialize executor.

        Args:
            permission_handler: PermissionHandler for DD-003 approval flow
            workspace_id: Workspace UUID for RLS context
            user_id: User UUID for attribution
            agent_name: Agent name for permission tracking
            file_hook_executor: Optional file-based hooks to compose with
            event_queue: Optional asyncio.Queue for SSE approval events
            max_budget_usd: Per-request budget ceiling for BudgetStopHook
        """
        self._permission_hook = PermissionCheckHook(permission_handler)
        self._workspace_id = workspace_id
        self._user_id = user_id
        self._agent_name = agent_name
        self._file_hook_executor = file_hook_executor
        self._event_queue = event_queue
        self._max_budget_usd = max_budget_usd

    def to_sdk_hooks(self) -> dict[str, list[dict[str, Any]]]:
        """Convert to SDK-compatible hooks format.

        Merges file-based hooks with permission check hook,
        subagent progress hooks, and lifecycle hooks (G8-G11).

        Returns:
            Dict mapping hook event names to matcher lists.
        """
        # Start with file-based hooks if available
        sdk_hooks: dict[str, list[dict[str, Any]]] = {}
        if self._file_hook_executor:
            sdk_hooks = self._file_hook_executor.to_sdk_hooks()

        # Add permission check as a catch-all PreToolUse hook
        permission_matcher = {
            "matcher": ".*",
            "hooks": [self._create_permission_callback()],
        }

        pre_hooks = sdk_hooks.get("PreToolUse", [])
        pre_hooks.append(permission_matcher)
        sdk_hooks["PreToolUse"] = pre_hooks

        # Wire SubagentProgressHook for task_progress SSE events
        subagent_hook = SubagentProgressHook(event_queue=self._event_queue)

        # Build lifecycle hooks (G8-G11)
        lifecycle_hooks: list[
            AuditLogHook
            | InputValidationHook
            | BudgetStopHook
            | ContextPreservationHook
            | SubagentProgressHook
        ] = [
            subagent_hook,
            AuditLogHook(event_queue=self._event_queue),
            InputValidationHook(),
            ContextPreservationHook(),
        ]

        # Add BudgetStopHook only when budget is configured
        if self._max_budget_usd is not None and self._max_budget_usd > 0:
            lifecycle_hooks.append(
                BudgetStopHook(
                    max_budget_usd=self._max_budget_usd,
                    event_queue=self._event_queue,
                ),
            )

        # Merge all lifecycle hooks into sdk_hooks
        for hook in lifecycle_hooks:
            for event_name, matchers in hook.to_sdk_hooks().items():
                existing = sdk_hooks.get(event_name, [])
                existing.extend(matchers)
                sdk_hooks[event_name] = existing

        return sdk_hooks

    def _create_permission_callback(self):
        """Create SDK-compatible async callback for permission checks.

        Returns:
            Async callback that bridges PermissionCheckHook to SDK format.
        """
        permission_hook = self._permission_hook
        workspace_id = self._workspace_id
        user_id = self._user_id
        agent_name = self._agent_name
        event_queue = self._event_queue

        async def callback(
            input_data: dict[str, Any],
            tool_use_id: str | None,
            context: Any,
        ) -> dict[str, Any]:
            """SDK hook callback that enforces DD-003 permissions."""
            tool_name = input_data.get("tool_name", "")
            tool_input = input_data.get("tool_input", {})
            hook_event_name = input_data.get(
                "hook_event_name",
                "PreToolUse",
            )

            # Build ToolCallContext from SDK callback data
            tool_context = ToolCallContext(
                tool_name=tool_name,
                tool_input=tool_input,
                workspace_id=workspace_id,
                user_id=user_id,
                agent_name=agent_name,
            )

            try:
                result = await permission_hook.should_execute(tool_context)
            except Exception:
                logger.exception(
                    "Permission check failed for tool '%s'",
                    tool_name,
                )
                # Fail open for non-mapped tools, fail closed for mapped
                if tool_name in PermissionCheckHook.TOOL_ACTION_MAPPING:
                    return {
                        "hookSpecificOutput": {
                            "hookEventName": hook_event_name,
                            "permissionDecision": "deny",
                            "permissionDecisionReason": ("Permission check failed unexpectedly"),
                        },
                    }
                return {}

            if result.allow:
                return {}

            if result.requires_approval:
                # Emit approval_request SSE event if queue available
                if event_queue and result.approval_id:
                    approval_event = _build_approval_sse_event(
                        approval_id=result.approval_id,
                        tool_name=tool_name,
                        tool_input=tool_input,
                        reason=result.reason,
                    )
                    await event_queue.put(approval_event)

                return {
                    "hookSpecificOutput": {
                        "hookEventName": hook_event_name,
                        "permissionDecision": "ask",
                        "permissionDecisionReason": result.reason,
                    },
                }

            # Denied
            return {
                "hookSpecificOutput": {
                    "hookEventName": hook_event_name,
                    "permissionDecision": "deny",
                    "permissionDecisionReason": result.reason,
                },
            }

        return callback


class SubagentProgressHook:
    """Emits task_progress SSE events when subagents start/complete.

    Connects to SDK's SubagentStart and SubagentEnd lifecycle hooks
    to provide real-time progress visibility in the frontend TaskPanel.

    Usage:
        hook = SubagentProgressHook(event_queue)
        sdk_hooks = hook.to_sdk_hooks()
        # Merge into existing hooks dict
    """

    def __init__(self, event_queue: Any | None = None) -> None:
        """Initialize with optional event queue for SSE emission.

        Args:
            event_queue: asyncio.Queue for SSE events
        """
        self._event_queue = event_queue

    def to_sdk_hooks(self) -> dict[str, list[dict[str, Any]]]:
        """Create SDK-compatible hooks for subagent lifecycle events.

        Returns:
            Dict mapping SubagentStart/SubagentEnd to callback matchers.
        """
        return {
            "SubagentStart": [
                {
                    "matcher": ".*",
                    "hooks": [self._create_start_callback()],
                },
            ],
            "SubagentEnd": [
                {
                    "matcher": ".*",
                    "hooks": [self._create_end_callback()],
                },
            ],
        }

    def _create_start_callback(self):
        """Create callback for subagent start events."""
        event_queue = self._event_queue

        async def callback(
            input_data: dict[str, Any],
            tool_use_id: str | None,
            context: Any,
        ) -> dict[str, Any]:
            """Emit task_progress SSE when subagent starts."""
            agent_name = input_data.get("agent_name", "unknown")
            model = input_data.get("model", "")
            task_id = input_data.get("task_id", str(uuid4()))

            if event_queue:
                progress_data = {
                    "taskId": task_id,
                    "subject": f"{agent_name} analysis",
                    "status": "in_progress",
                    "progress": 0,
                    "agentName": agent_name,
                    "model": model,
                }
                event = f"event: task_progress\ndata: {json.dumps(progress_data)}\n\n"
                await event_queue.put(event)

            return {}

        return callback

    def _create_end_callback(self):
        """Create callback for subagent end events."""
        event_queue = self._event_queue

        async def callback(
            input_data: dict[str, Any],
            tool_use_id: str | None,
            context: Any,
        ) -> dict[str, Any]:
            """Emit task_progress SSE when subagent completes."""
            agent_name = input_data.get("agent_name", "unknown")
            task_id = input_data.get("task_id", str(uuid4()))
            is_error = input_data.get("is_error", False)

            if event_queue:
                progress_data = {
                    "taskId": task_id,
                    "subject": f"{agent_name} analysis",
                    "status": "failed" if is_error else "completed",
                    "progress": 100,
                    "agentName": agent_name,
                }
                event = f"event: task_progress\ndata: {json.dumps(progress_data)}\n\n"
                await event_queue.put(event)

            return {}

        return callback


def _build_approval_sse_event(
    approval_id: UUID,
    tool_name: str,
    tool_input: dict[str, Any],
    reason: str,
) -> str:
    """Build SSE event string for approval_request.

    Args:
        approval_id: UUID of the approval request
        tool_name: Tool that triggered approval
        tool_input: Tool input parameters
        reason: Reason for approval requirement

    Returns:
        SSE-formatted event string.
    """
    data = {
        "requestId": str(approval_id),
        "actionType": tool_name,
        "description": reason,
        "proposedChanges": tool_input,
    }
    return f"event: approval_request\ndata: {json.dumps(data)}\n\n"
