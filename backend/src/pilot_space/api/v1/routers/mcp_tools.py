"""MCP Tool Discovery API endpoint.

Provides tool schema discovery for AI agents and skill system.

Reference: T093 (MCP Tool Discovery Endpoint)
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from pilot_space.dependencies import CurrentUserId, DbSession
from pilot_space.domain.exceptions import AppError, NotFoundError, ValidationError

router = APIRouter(prefix="/ai/mcp/tools", tags=["mcp-tools"])


class ToolSchema(BaseModel):
    """Tool schema for discovery.

    Attributes:
        name: Tool name.
        description: Tool description.
        requires_approval: Whether tool requires approval.
        parameters: Parameter schema.
    """

    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    requires_approval: bool = Field(..., description="Whether approval required")
    parameters: dict[str, Any] = Field(..., description="Parameter schema")


class ToolListResponse(BaseModel):
    """Tool list response.

    Attributes:
        tools: List of available tools.
        total: Total count.
    """

    tools: list[ToolSchema] = Field(..., description="Available tools")
    total: int = Field(..., ge=0, description="Total tool count")


class ToolExecuteRequest(BaseModel):
    """Tool execution request.

    Attributes:
        tool_name: Tool to execute.
        workspace_id: Workspace UUID.
        params: Tool parameters.
    """

    tool_name: str = Field(..., description="Tool name")
    workspace_id: UUID = Field(..., description="Workspace ID")
    params: dict[str, Any] = Field(default_factory=dict, description="Parameters")


class ToolExecuteResponse(BaseModel):
    """Tool execution response.

    Attributes:
        success: Whether execution succeeded.
        data: Result data (if success).
        error: Error message (if failure).
        metadata: Additional metadata.
    """

    success: bool = Field(..., description="Execution success")
    data: dict[str, Any] | None = Field(None, description="Result data")
    error: str | None = Field(None, description="Error message")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata")


@router.get("")
async def list_tools(
    user_id: CurrentUserId,
    workspace_id: UUID | None = Query(None, description="Filter by workspace"),
) -> ToolListResponse:
    """List all available MCP tools.

    Args:
        user_id: Current user ID (from auth).
        workspace_id: Optional workspace filter.

    Returns:
        List of tool schemas for discovery.
    """
    from pilot_space.ai.mcp.registry import MCPToolRegistry

    # Create registry and load tools
    registry = MCPToolRegistry()

    # Register available tools
    from pilot_space.ai.mcp.tools.pr_review import PRReviewTool
    from pilot_space.integrations.github import GitHubClient

    # Initialize GitHub client (placeholder - should come from dependency)
    github_client = GitHubClient(access_token="placeholder")
    pr_review_tool = PRReviewTool(github_client)
    registry.register(pr_review_tool)

    # Get tool schemas
    tools_data = registry.list_tools(workspace_id=workspace_id)

    tools = [
        ToolSchema(
            name=tool["name"],
            description=tool["description"],
            requires_approval=tool["requires_approval"],
            parameters=tool["parameters"],
        )
        for tool in tools_data
    ]

    return ToolListResponse(
        tools=tools,
        total=len(tools),
    )


@router.post("/execute")
async def execute_tool(
    request: ToolExecuteRequest,
    user_id: CurrentUserId,
    db_session: DbSession,
) -> ToolExecuteResponse:
    """Execute an MCP tool.

    Args:
        request: Tool execution request.
        user_id: Current user ID (from auth).
        db_session: Database session for RLS.

    Returns:
        Tool execution result.

    Raises:
        HTTPException: If tool not found or execution fails.
    """
    from pilot_space.ai.mcp.registry import (
        MCPToolRegistry,
        ToolNotFoundError,
        ToolValidationError,
    )

    # Create registry and load tools
    registry = MCPToolRegistry(db_session)

    # Register available tools (should be done once at startup)
    from pilot_space.ai.mcp.tools.pr_review import PRReviewTool
    from pilot_space.integrations.github import GitHubClient

    github_client = GitHubClient(access_token="placeholder")
    pr_review_tool = PRReviewTool(github_client)
    registry.register(pr_review_tool)

    # Execute tool
    try:
        result = await registry.execute(
            tool_name=request.tool_name,
            workspace_id=request.workspace_id,
            user_id=user_id,
            params=request.params,
        )

        return ToolExecuteResponse(
            success=result.success,
            data=result.data,
            error=result.error,
            metadata=result.metadata,
        )

    except ToolNotFoundError as e:
        raise NotFoundError(str(e)) from e
    except ToolValidationError as e:
        raise ValidationError(str(e)) from e
    except Exception as e:
        raise AppError(f"Tool execution failed: {e!s}") from e


__all__ = ["router"]
