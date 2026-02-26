"""In-process SDK MCP server for GitHub integration tools.

Wraps the registered @register_tool("github") functions from github_tools.py
into a McpSdkServerConfig that the Claude Agent SDK can call as mcp__github__*.

Tools exposed:
- get_pr_details: PR metadata (title, author, labels, merge status)
- get_pr_diff:    Changed files with unified diff patches
- post_pr_comment: Post general or line-specific review comment
"""

from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import McpSdkServerConfig, create_sdk_mcp_server, tool

from pilot_space.ai.tools.mcp_server import ToolContext
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

SERVER_NAME = "github"

TOOL_NAMES = [
    f"mcp__{SERVER_NAME}__get_pr_details",
    f"mcp__{SERVER_NAME}__get_pr_diff",
    f"mcp__{SERVER_NAME}__post_pr_comment",
]


def _json_result(data: Any) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": json.dumps(data)}]}


def create_github_tools_server(tool_context: ToolContext) -> McpSdkServerConfig:
    """Create an in-process SDK MCP server for GitHub review tools.

    Wraps get_pr_details, get_pr_diff, and post_pr_comment with the
    tool_context already bound so the Claude SDK can call them as
    mcp__github__<tool_name>.

    Args:
        tool_context: ToolContext with db_session and workspace_id.

    Returns:
        McpSdkServerConfig ready for ClaudeAgentOptions.mcp_servers["github"].
    """
    from pilot_space.ai.tools.github_tools import (
        get_pr_details as _get_pr_details,
        get_pr_diff as _get_pr_diff,
        post_pr_comment as _post_pr_comment,
    )

    @tool(
        "get_pr_details",
        "Get pull request metadata including title, description, author, labels, and merge status.",
        {
            "type": "object",
            "properties": {
                "pr_number": {
                    "type": "integer",
                    "description": "PR number in the repository (must be positive)",
                },
                "integration_id": {
                    "type": "string",
                    "description": "Optional specific GitHub integration UUID",
                },
            },
            "required": ["pr_number"],
        },
    )
    async def get_pr_details(args: dict[str, Any]) -> dict[str, Any]:
        result = await _get_pr_details(
            pr_number=args["pr_number"],
            ctx=tool_context,
            integration_id=args.get("integration_id"),
        )
        return _json_result(result)

    @tool(
        "get_pr_diff",
        "Get changed files with unified diff patches for code review analysis.",
        {
            "type": "object",
            "properties": {
                "pr_number": {
                    "type": "integer",
                    "description": "PR number in the repository (must be positive)",
                },
                "integration_id": {
                    "type": "string",
                    "description": "Optional specific GitHub integration UUID",
                },
            },
            "required": ["pr_number"],
        },
    )
    async def get_pr_diff(args: dict[str, Any]) -> dict[str, Any]:
        result = await _get_pr_diff(
            pr_number=args["pr_number"],
            ctx=tool_context,
            integration_id=args.get("integration_id"),
        )
        return _json_result(result)

    @tool(
        "post_pr_comment",
        "Post a general or line-specific review comment on the pull request.",
        {
            "type": "object",
            "properties": {
                "pr_number": {
                    "type": "integer",
                    "description": "PR number (must be positive)",
                },
                "body": {
                    "type": "string",
                    "description": "Comment body (markdown supported)",
                },
                "integration_id": {
                    "type": "string",
                    "description": "Optional specific GitHub integration UUID",
                },
                "path": {
                    "type": "string",
                    "description": "File path for line-specific comment",
                },
                "line": {
                    "type": "integer",
                    "description": "Line number for line-specific comment (requires path)",
                },
            },
            "required": ["pr_number", "body"],
        },
    )
    async def post_pr_comment(args: dict[str, Any]) -> dict[str, Any]:
        result = await _post_pr_comment(
            pr_number=args["pr_number"],
            body=args["body"],
            ctx=tool_context,
            integration_id=args.get("integration_id"),
            path=args.get("path"),
            line=args.get("line"),
        )
        return _json_result(result)

    return create_sdk_mcp_server(
        name=SERVER_NAME,
        version="1.0.0",
        tools=[get_pr_details, get_pr_diff, post_pr_comment],
    )


__all__ = ["SERVER_NAME", "TOOL_NAMES", "create_github_tools_server"]
