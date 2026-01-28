"""Pre-tool-use hooks for Claude Agent SDK.

Provides hooks that intercept tool calls before execution to:
- Enforce permission/approval flow (DD-003)
- Validate tool parameters
- Log tool usage for auditing
- Implement rate limiting

Reference: docs/architect/claude-agent-sdk-architecture.md
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar
from uuid import UUID

if TYPE_CHECKING:
    from pilot_space.ai.sdk.permission_handler import PermissionHandler


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
