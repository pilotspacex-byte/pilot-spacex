"""MCP Tool Definitions for Claude Agent SDK.

This package contains tool definitions that expose Pilot Space
data and functionality to Claude agents via the Model Context Protocol.

Tool Categories:
    database: Workspace members, cycle context, annotations
    github: PR details, diff, code search, comments
    search: Semantic search, codebase search
    note: Note CRUD + content manipulation (via MCP servers)
    issue: Issue CRUD + relationships (via MCP servers)
    project: Project CRUD + settings (via MCP servers)
    comment: Comment CRUD + threading (via MCP servers)

Usage:
    from pilot_space.ai.tools import ToolRegistry, ToolContext

    # Get all tools for an agent
    tools = ToolRegistry.get_tools()

    # Get tools by category
    db_tools = ToolRegistry.get_tools(categories=["database"])

All tools are registered automatically when imported.
"""

# Import all tools to trigger registration
from pilot_space.ai.tools.database_tools import (
    create_note_annotation,
    get_cycle_context,
    get_workspace_members,
)
from pilot_space.ai.tools.github_tools import (
    get_pr_details,
    get_pr_diff,
    post_pr_comment,
    search_code_in_repo,
)
from pilot_space.ai.tools.mcp_server import (
    ToolContext,
    ToolRegistry,
    register_tool,
)
from pilot_space.ai.tools.search_tools import (
    search_codebase,
    semantic_search,
)

__all__ = [
    "ToolContext",
    "ToolRegistry",
    "create_note_annotation",
    "get_cycle_context",
    "get_pr_details",
    "get_pr_diff",
    "get_workspace_members",
    "post_pr_comment",
    "register_tool",
    "search_code_in_repo",
    "search_codebase",
    "semantic_search",
]
