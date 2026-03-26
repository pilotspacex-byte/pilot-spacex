"""MCP Tool Discovery API endpoint.

Thin HTTP shell -- all business logic delegated to MCPToolExecutionService.

Reference: T093 (MCP Tool Discovery Endpoint)
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from pilot_space.api.v1.dependencies import MCPToolExecutionServiceDep
from pilot_space.dependencies import CurrentUserId, DbSession

router = APIRouter(prefix="/ai/mcp/tools", tags=["mcp-tools"])


class ToolSchema(BaseModel):
    """Tool schema for discovery."""

    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    requires_approval: bool = Field(..., description="Whether approval required")
    parameters: dict[str, Any] = Field(..., description="Parameter schema")


class ToolListResponse(BaseModel):
    """Tool list response."""

    tools: list[ToolSchema] = Field(..., description="Available tools")
    total: int = Field(..., ge=0, description="Total tool count")


class ToolExecuteRequest(BaseModel):
    """Tool execution request."""

    tool_name: str = Field(..., description="Tool name")
    workspace_id: UUID = Field(..., description="Workspace ID")
    params: dict[str, Any] = Field(default_factory=dict, description="Parameters")


class ToolExecuteResponse(BaseModel):
    """Tool execution response."""

    success: bool = Field(..., description="Execution success")
    data: dict[str, Any] | None = Field(None, description="Result data")
    error: str | None = Field(None, description="Error message")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata")


@router.get("")
async def list_tools(
    user_id: CurrentUserId,
    session: DbSession,
    service: MCPToolExecutionServiceDep,
    workspace_id: UUID | None = Query(None, description="Filter by workspace"),
) -> ToolListResponse:
    """List all available MCP tools."""
    tools = await service.list_available_tools(workspace_id=workspace_id)
    return ToolListResponse(
        tools=[
            ToolSchema(
                name=t.name,
                description=t.description,
                requires_approval=t.requires_approval,
                parameters=t.parameters,
            )
            for t in tools
        ],
        total=len(tools),
    )


@router.post("/execute")
async def execute_tool(
    request: ToolExecuteRequest,
    user_id: CurrentUserId,
    session: DbSession,
    service: MCPToolExecutionServiceDep,
) -> ToolExecuteResponse:
    """Execute an MCP tool."""
    result = await service.execute_tool(
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


__all__ = ["router"]
