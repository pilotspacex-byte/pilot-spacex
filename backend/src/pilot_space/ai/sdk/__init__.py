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

from pilot_space.ai.sdk.config import (
    ClaudeAgentOptions,
    create_agent_options,
    get_model_for_task,
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
from pilot_space.ai.sdk.session_handler import (
    ConversationMessage,
    ConversationSession,
    SessionHandler,
)
from pilot_space.ai.sdk.skill_registry import SkillDefinition, SkillRegistry
from pilot_space.ai.sdk.skill_validator import (
    SkillValidator,
    ValidationError,
    ValidationResult,
    validate_skill_file,
)
from pilot_space.ai.sdk.sse_transformer import (
    SSEEvent,
    SSETransformer,
    transform_claude_event,
)

__all__ = [
    "ActionClassification",
    "ApprovalRequest",
    "ApprovalStatus",
    "ClaudeAgentOptions",
    "CompositeHook",
    "ConversationMessage",
    "ConversationSession",
    "HookResult",
    "PermissionCheckHook",
    "PermissionHandler",
    "PermissionResult",
    "PreToolUseHook",
    "SSEEvent",
    "SSETransformer",
    "SessionHandler",
    "SkillDefinition",
    "SkillRegistry",
    "SkillValidator",
    "ToolCallContext",
    "ValidationError",
    "ValidationHook",
    "ValidationResult",
    "create_agent_options",
    "get_model_for_task",
    "transform_claude_event",
    "validate_skill_file",
]
