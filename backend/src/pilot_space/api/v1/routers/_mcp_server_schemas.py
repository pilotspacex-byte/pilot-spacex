"""Pydantic schemas and SSRF validation for workspace MCP server endpoints.

Extracted from workspace_mcp_servers.py to stay within the 700-line limit.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from pilot_space.infrastructure.database.models.workspace_mcp_server import (
    McpAuthType,
    McpTransportType,
)
from pilot_space.infrastructure.ssrf import validate_mcp_url as _validate_mcp_url

# ---------------------------------------------------------------------------
# URL validation helpers
# ---------------------------------------------------------------------------

WORKSPACE_SLUG_RE = re.compile(r"^[a-z0-9-]+$")


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class WorkspaceMcpServerCreate(BaseModel):
    """Request body for registering a new remote MCP server."""

    display_name: str = Field(..., max_length=128, description="Human-readable label")
    url: str = Field(
        ..., max_length=512, description="Remote MCP server endpoint (SSE, HTTPS only)"
    )
    auth_type: McpAuthType = Field(default=McpAuthType.BEARER)
    transport_type: McpTransportType = Field(default=McpTransportType.SSE)
    auth_token: str | None = Field(
        default=None, description="Bearer token (will be encrypted at rest)"
    )
    oauth_client_id: str | None = Field(default=None, max_length=256)
    oauth_auth_url: str | None = Field(default=None, max_length=512)
    oauth_token_url: str | None = Field(default=None, max_length=512)
    oauth_scopes: str | None = Field(default=None, max_length=512)

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate main server URL against SSRF blocklist."""
        return _validate_mcp_url(v)

    @field_validator("oauth_auth_url", "oauth_token_url")
    @classmethod
    def validate_oauth_urls(cls, v: str | None) -> str | None:
        """Validate OAuth URLs against SSRF blocklist."""
        if v is None:
            return v
        return _validate_mcp_url(v)


class WorkspaceMcpServerResponse(BaseModel):
    """Response for a single MCP server (never echoes raw token)."""

    id: UUID
    workspace_id: UUID
    display_name: str
    url: str
    auth_type: McpAuthType
    transport_type: McpTransportType = McpTransportType.SSE
    last_status: str | None
    last_status_checked_at: datetime | None
    created_at: datetime
    approval_mode: str = "auto_approve"
    # OAuth fields (returned only for oauth2 servers)
    oauth_client_id: str | None = None
    oauth_auth_url: str | None = None
    oauth_scopes: str | None = None
    token_expires_at: datetime | None = None

    model_config = {"from_attributes": True}


class McpApprovalModeUpdate(BaseModel):
    """Request body for updating the approval mode of a registered MCP server."""

    approval_mode: Literal["auto_approve", "require_approval"]


class WorkspaceMcpServerListResponse(BaseModel):
    """List response for workspace MCP servers."""

    items: list[WorkspaceMcpServerResponse]
    total: int


class McpServerStatusResponse(BaseModel):
    """Status probe result for an MCP server."""

    server_id: UUID
    status: str  # "connected" | "failed" | "unknown"
    checked_at: datetime


class McpOAuthUrlResponse(BaseModel):
    """OAuth authorization URL for MCP server OAuth flow."""

    auth_url: str
    state: str
