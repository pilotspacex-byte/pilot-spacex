"""Pydantic schemas for workspace MCP server management (Phase 14).

Covers MCP-01, MCP-02, MCP-06 request/response shapes for:
- Registering remote MCP servers (Bearer and OAuth 2.0 auth)
- Listing registered servers
- Status probe responses
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from pilot_space.infrastructure.database.models.workspace_mcp_server import McpAuthType


class WorkspaceMcpServerCreate(BaseModel):
    """Request schema for registering a new remote MCP server.

    The `auth_token` field carries the plaintext Bearer token and is
    never echoed back — the router encrypts it before storing in
    `auth_token_encrypted`.
    """

    display_name: str = Field(
        ..., max_length=128, description="Human-readable label for the server"
    )
    url: str = Field(..., description="Remote MCP server endpoint (SSE or HTTP transport)")
    auth_type: McpAuthType = McpAuthType.BEARER

    # Bearer auth
    auth_token: str | None = Field(
        None,
        description="Plaintext Bearer token; stored encrypted at rest (never returned in responses)",
    )

    # OAuth 2.0 fields (required when auth_type=oauth2)
    oauth_client_id: str | None = Field(None, max_length=256, description="OAuth 2.0 client ID")
    oauth_auth_url: str | None = Field(
        None, max_length=512, description="OAuth 2.0 authorization endpoint URL"
    )
    oauth_token_url: str | None = Field(
        None, max_length=512, description="OAuth 2.0 token exchange endpoint URL"
    )
    oauth_scopes: str | None = Field(
        None, max_length=512, description="Space-separated OAuth 2.0 scope list"
    )


class WorkspaceMcpServerUpdate(BaseModel):
    """Request schema for updating an existing MCP server registration.

    All fields are optional — only provided fields are updated (partial update).
    """

    display_name: str | None = Field(None, max_length=128)
    url: str | None = Field(None, description="New MCP server endpoint URL")
    auth_token: str | None = Field(
        None, description="New plaintext Bearer token (replaces existing encrypted value)"
    )
    oauth_client_id: str | None = Field(None, max_length=256)
    oauth_auth_url: str | None = Field(None, max_length=512)
    oauth_token_url: str | None = Field(None, max_length=512)
    oauth_scopes: str | None = Field(None, max_length=512)


class WorkspaceMcpServerResponse(BaseModel):
    """Response schema for a single registered MCP server.

    The encrypted token field is intentionally excluded — callers never
    receive the raw ciphertext or plaintext token.
    """

    id: UUID
    workspace_id: UUID
    display_name: str
    url: str
    auth_type: McpAuthType
    last_status: str | None = None
    last_status_checked_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkspaceMcpServerListResponse(BaseModel):
    """Paginated list of registered MCP servers for a workspace."""

    items: list[WorkspaceMcpServerResponse]
    total: int


class McpServerStatusResponse(BaseModel):
    """Response schema for the MCP server status probe endpoint (MCP-05).

    `status` reflects the result of the most recent connectivity check.
    Values:
    - "connected": Server responded with 2xx to the ping/SSE probe.
    - "failed": Server returned an error or was unreachable.
    - "unknown": No connectivity check has been performed yet.
    """

    server_id: UUID
    status: Literal["connected", "failed", "unknown"]
    checked_at: datetime


__all__ = [
    "McpServerStatusResponse",
    "WorkspaceMcpServerCreate",
    "WorkspaceMcpServerListResponse",
    "WorkspaceMcpServerResponse",
    "WorkspaceMcpServerUpdate",
]
