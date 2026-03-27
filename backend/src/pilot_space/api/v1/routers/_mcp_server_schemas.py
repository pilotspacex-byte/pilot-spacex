"""Backward-compatibility shim for MCP server schemas.

All schemas have been migrated to ``pilot_space.api.v1.schemas.mcp_server``.
This module re-exports everything from the new location so existing import
paths continue to work during the transition period.
"""

from __future__ import annotations

from pilot_space.api.v1.schemas.mcp_server import (
    WORKSPACE_SLUG_RE,
    ErrorServerEntry,
    ImportedServerEntry,
    ImportMcpServersRequest,
    ImportMcpServersResponse,
    McpOAuthUrlResponse,
    McpServerStatusResponse,
    McpServerTestResponse,
    SkippedServerEntry,
    WorkspaceMcpServerCreate,
    WorkspaceMcpServerListResponse,
    WorkspaceMcpServerResponse,
    WorkspaceMcpServerUpdate,
)

__all__ = [
    "WORKSPACE_SLUG_RE",
    "ErrorServerEntry",
    "ImportMcpServersRequest",
    "ImportMcpServersResponse",
    "ImportedServerEntry",
    "McpOAuthUrlResponse",
    "McpServerStatusResponse",
    "McpServerTestResponse",
    "SkippedServerEntry",
    "WorkspaceMcpServerCreate",
    "WorkspaceMcpServerListResponse",
    "WorkspaceMcpServerResponse",
    "WorkspaceMcpServerUpdate",
]
