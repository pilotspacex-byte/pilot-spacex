"""MCP Tool Discovery API endpoint.

Thin HTTP shell -- all business logic delegated to MCPToolExecutionService.

Reference: T093 (MCP Tool Discovery Endpoint)
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from pilot_space.api.v1.dependencies import MCPToolExecutionServiceDep
from pilot_space.api.v1.schemas.mcp_tools import (
    ToolExecuteRequest,
    ToolExecuteResponse,
    ToolListResponse,
    ToolSchema,
)
from pilot_space.dependencies import CurrentUserId, DbSession

router = APIRouter(prefix="/ai/mcp/tools", tags=["mcp-tools"])


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
