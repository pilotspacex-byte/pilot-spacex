"""Domain schema for McpServerService return types.

The full API-level response schema (``WorkspaceMcpServerResponse``) already
lives in ``api/v1/routers/_mcp_server_schemas.py`` and is feature-complete.
This thin domain schema captures the minimal identity result that the service
layer uses when it needs to communicate a server ID without coupling to the
API schema layer.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class McpServerResult(BaseModel):
    """Minimal MCP server identity result.

    Used internally when a service method needs to return the created/updated
    server ID without returning the full ORM model or API response schema.
    """

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: UUID
    workspace_id: UUID
    display_name: str
    is_enabled: bool


__all__ = ["McpServerResult"]
