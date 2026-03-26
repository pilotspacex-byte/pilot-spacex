"""Pydantic schemas for MCP Tool Discovery API endpoints.

Reference: T093 (MCP Tool Discovery Endpoint)
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


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


__all__ = [
    "ToolExecuteRequest",
    "ToolExecuteResponse",
    "ToolListResponse",
    "ToolSchema",
]
