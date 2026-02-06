"""MCP Tool Registry for Claude Agent SDK.

Provides tool registration, selection, approval levels, and tool result types
for agent orchestration. Tools are registered via decorators and selected
per agent needs.

Reference: Claude Agent SDK patterns, spec 010-enhanced-mcp-tools AD-002
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any, TypeVar

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


# Type for tool functions
ToolFunc = TypeVar("ToolFunc", bound=Callable[..., Any])

# Global tool registry
_TOOL_REGISTRY: dict[str, Callable[..., Any]] = {}
_TOOL_CATEGORIES: dict[str, list[str]] = {
    "database": [],
    "github": [],
    "search": [],
    "note": [],
    "issue": [],
    "project": [],
    "comment": [],
}


class ToolApprovalLevel(StrEnum):
    """Approval level for MCP tools (DD-003, spec 010 AD-002).

    Determines the approval flow for each tool invocation:
    - AUTO_EXECUTE: Execute immediately, notify user.
    - REQUIRE_APPROVAL: Request approval, configurable by user.
    - ALWAYS_REQUIRE: Always require explicit approval, cannot be disabled.
    """

    AUTO_EXECUTE = "auto_execute"
    REQUIRE_APPROVAL = "require_approval"
    ALWAYS_REQUIRE = "always_require"


@dataclass
class ToolResult:
    """Structured result from an MCP tool invocation.

    All mutation tools return ToolResult with appropriate status and payload.
    Read-only tools return data directly.
    """

    tool: str
    operation: str
    status: str  # "pending_apply" | "approval_required" | "executed"
    approval_level: ToolApprovalLevel
    payload: dict[str, Any]
    preview: dict[str, Any] | None = None


# Maps tool names to their approval levels (spec 010, 27 tools)
TOOL_APPROVAL_MAP: dict[str, ToolApprovalLevel] = {
    # Note tools - AUTO_EXECUTE (read-only)
    "search_notes": ToolApprovalLevel.AUTO_EXECUTE,
    "search_note_content": ToolApprovalLevel.AUTO_EXECUTE,
    # Note tools - REQUIRE_APPROVAL (mutations)
    "create_note": ToolApprovalLevel.REQUIRE_APPROVAL,
    "update_note": ToolApprovalLevel.REQUIRE_APPROVAL,
    "insert_block": ToolApprovalLevel.REQUIRE_APPROVAL,
    "remove_block": ToolApprovalLevel.REQUIRE_APPROVAL,
    "remove_content": ToolApprovalLevel.REQUIRE_APPROVAL,
    "replace_content": ToolApprovalLevel.REQUIRE_APPROVAL,
    # Issue tools - AUTO_EXECUTE (read-only)
    "get_issue": ToolApprovalLevel.AUTO_EXECUTE,
    "search_issues": ToolApprovalLevel.AUTO_EXECUTE,
    # Issue tools - REQUIRE_APPROVAL (mutations)
    "create_issue": ToolApprovalLevel.REQUIRE_APPROVAL,
    "update_issue": ToolApprovalLevel.REQUIRE_APPROVAL,
    "link_issue_to_note": ToolApprovalLevel.REQUIRE_APPROVAL,
    "link_issues": ToolApprovalLevel.REQUIRE_APPROVAL,
    "add_sub_issue": ToolApprovalLevel.REQUIRE_APPROVAL,
    "transition_issue_state": ToolApprovalLevel.REQUIRE_APPROVAL,
    # Issue tools - ALWAYS_REQUIRE (destructive)
    "unlink_issue_from_note": ToolApprovalLevel.ALWAYS_REQUIRE,
    "unlink_issues": ToolApprovalLevel.ALWAYS_REQUIRE,
    # Project tools - AUTO_EXECUTE (read-only)
    "get_project": ToolApprovalLevel.AUTO_EXECUTE,
    "search_projects": ToolApprovalLevel.AUTO_EXECUTE,
    # Project tools - REQUIRE_APPROVAL (mutations)
    "create_project": ToolApprovalLevel.REQUIRE_APPROVAL,
    "update_project": ToolApprovalLevel.REQUIRE_APPROVAL,
    "update_project_settings": ToolApprovalLevel.REQUIRE_APPROVAL,
    # Retained tools (6 from note_tools.py, registered in MCP servers)
    "update_note_block": ToolApprovalLevel.REQUIRE_APPROVAL,
    "enhance_text": ToolApprovalLevel.AUTO_EXECUTE,
    "extract_issues": ToolApprovalLevel.REQUIRE_APPROVAL,
    "create_issue_from_note": ToolApprovalLevel.REQUIRE_APPROVAL,
    "link_existing_issues": ToolApprovalLevel.REQUIRE_APPROVAL,
    "write_to_note": ToolApprovalLevel.REQUIRE_APPROVAL,
    # Comment tools - reads are AUTO_EXECUTE, creation auto (CM-001: non-destructive)
    "create_comment": ToolApprovalLevel.AUTO_EXECUTE,
    "search_comments": ToolApprovalLevel.AUTO_EXECUTE,
    "get_comments": ToolApprovalLevel.AUTO_EXECUTE,
    # Comment tools - REQUIRE_APPROVAL (content modification)
    "update_comment": ToolApprovalLevel.REQUIRE_APPROVAL,
}


def get_tool_approval_level(tool_name: str) -> ToolApprovalLevel:
    """Get the approval level for a tool.

    Args:
        tool_name: The tool function name.

    Returns:
        The approval level, defaults to REQUIRE_APPROVAL for unknown tools.
    """
    level = TOOL_APPROVAL_MAP.get(tool_name)
    if level is None:
        logger.warning("Unknown tool '%s', defaulting to REQUIRE_APPROVAL", tool_name)
        return ToolApprovalLevel.REQUIRE_APPROVAL
    return level


def register_tool(category: str) -> Callable[[ToolFunc], ToolFunc]:
    """Decorator to register an MCP tool.

    Usage:
        @register_tool("database")
        async def get_issue_context(...):
            ...

    Args:
        category: Tool category (database, github, search)

    Returns:
        Decorator function
    """

    def decorator(func: ToolFunc) -> ToolFunc:
        _TOOL_REGISTRY[func.__name__] = func
        if category in _TOOL_CATEGORIES:
            _TOOL_CATEGORIES[category].append(func.__name__)
        return func

    return decorator


@dataclass
class ToolContext:
    """Context passed to tools during execution.

    Contains database session and user context for RLS.
    """

    db_session: AsyncSession
    workspace_id: str
    user_id: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class ToolRegistry:
    """Registry for MCP tools used by Claude Agent SDK.

    Provides tool selection and filtering for agents.
    Each agent requests specific tools or categories.

    Usage:
        registry = ToolRegistry()
        tools = registry.get_tools(categories=["database"])
        # Pass tools to ClaudeSDKClient
    """

    @classmethod
    def get_tool(cls, name: str) -> Callable[..., Any] | None:
        """Get a specific tool by name.

        Args:
            name: Tool function name

        Returns:
            Tool function or None if not found
        """
        return _TOOL_REGISTRY.get(name)

    @classmethod
    def get_tools(
        cls,
        names: list[str] | None = None,
        categories: list[str] | None = None,
    ) -> list[Callable[..., Any]]:
        """Get tools by name or category.

        Args:
            names: Specific tool names to include
            categories: Tool categories to include

        Returns:
            List of tool functions
        """
        selected: list[Callable[..., Any]] = []

        if names:
            for name in names:
                if name in _TOOL_REGISTRY:
                    selected.append(_TOOL_REGISTRY[name])

        if categories:
            for category in categories:
                if category in _TOOL_CATEGORIES:
                    for name in _TOOL_CATEGORIES[category]:
                        tool = _TOOL_REGISTRY.get(name)
                        if tool and tool not in selected:
                            selected.append(tool)

        # If nothing specified, return all
        if not names and not categories:
            selected = list(_TOOL_REGISTRY.values())

        return selected

    @classmethod
    def get_all_tool_names(cls) -> list[str]:
        """Get all registered tool names.

        Returns:
            List of tool function names
        """
        return list(_TOOL_REGISTRY.keys())

    @classmethod
    def get_tools_by_category(cls, category: str) -> list[str]:
        """Get tool names for a specific category.

        Args:
            category: Category name (database, github, search)

        Returns:
            List of tool names in the category
        """
        return _TOOL_CATEGORIES.get(category, []).copy()

    @classmethod
    def get_categories(cls) -> list[str]:
        """Get all available categories.

        Returns:
            List of category names
        """
        return list(_TOOL_CATEGORIES.keys())
