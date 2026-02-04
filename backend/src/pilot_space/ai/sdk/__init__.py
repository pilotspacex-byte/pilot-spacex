"""Claude Agent SDK integration layer for PilotSpace.

This module provides the integration layer for Claude Agent SDK,
including:
- Configuration management (ClaudeAgentOptions)
- Session handling for multi-turn conversations
- Permission/approval flow enforcement (DD-003)
- Pre-tool-use hooks for validation and security

Reference: docs/architect/claude-agent-sdk-architecture.md
Design Decisions: DD-002 (BYOK), DD-003 (Approval Flow), DD-058 (SDK modes)

Usage:
    # Create agent options with API key
    options = await create_agent_options(
        workspace_id=workspace_id,
        user_id=user_id,
        key_storage=key_storage,
        model="claude-sonnet-4-20250514",
    )

    # Create session handler for multi-turn
    session_handler = SessionHandler(session_manager)
    session = await session_handler.create_session(
        workspace_id, user_id, "ai_context"
    )

    # Create permission handler
    permission_handler = PermissionHandler(approval_service)
    result = await permission_handler.check_permission(
        workspace_id, user_id, "pr_review", "create_issue", "...", {...}
    )

    # Create pre-tool-use hooks
    hook = PermissionCheckHook(permission_handler)
    hook_result = await hook.should_execute(tool_context)
"""

from pilot_space.ai.sdk.command_registry import (
    CommandDefinition,
    CommandParameter,
    CommandRegistry,
)
from pilot_space.ai.sdk.config import (
    ClaudeAgentOptions,
    create_agent_options,
    get_model_for_task,
)
from pilot_space.ai.sdk.file_hooks import (
    FileBasedHookExecutor,
    HookDefinition,
    HookMatcher,
    HookResponse,
    HooksConfiguration,
    HookType,
    PermissionDecision,
)
from pilot_space.ai.sdk.hooks import (
    CompositeHook,
    HookResult,
    PermissionCheckHook,
    PreToolUseHook,
    ToolCallContext,
    ValidationHook,
)
from pilot_space.ai.sdk.permission_handler import (
    ActionClassification,
    ApprovalRequest,
    ApprovalStatus,
    PermissionHandler,
    PermissionResult,
)
from pilot_space.ai.sdk.sandbox_config import (
    DANGEROUS_BASH_PATTERNS,
    PROTECTED_FILE_PATTERNS,
    SAFE_BASH_PATTERNS,
    SandboxSettings,
    SDKConfiguration,
    configure_sdk_for_space,
    is_bash_command_safe,
    is_file_protected,
)
from pilot_space.ai.sdk.session_handler import (
    ConversationMessage,
    ConversationSession,
    SessionHandler,
)
from pilot_space.ai.sdk.sse_transformer import (
    SSEEvent,
)

__all__ = [
    # Sandbox
    "DANGEROUS_BASH_PATTERNS",
    "PROTECTED_FILE_PATTERNS",
    "SAFE_BASH_PATTERNS",
    # Permissions
    "ActionClassification",
    "ApprovalRequest",
    "ApprovalStatus",
    # Config
    "ClaudeAgentOptions",
    # Command registry
    "CommandDefinition",
    "CommandParameter",
    "CommandRegistry",
    # Hooks
    "CompositeHook",
    # Session
    "ConversationMessage",
    "ConversationSession",
    # File-based hooks
    "FileBasedHookExecutor",
    "HookDefinition",
    "HookMatcher",
    "HookResponse",
    "HookResult",
    "HookType",
    "HooksConfiguration",
    "PermissionCheckHook",
    "PermissionDecision",
    "PermissionHandler",
    "PermissionResult",
    "PreToolUseHook",
    "SDKConfiguration",
    # SSE
    "SSEEvent",
    "SandboxSettings",
    "SessionHandler",
    "ToolCallContext",
    "ValidationHook",
    "configure_sdk_for_space",
    "create_agent_options",
    "get_model_for_task",
    "is_bash_command_safe",
    "is_file_protected",
]
