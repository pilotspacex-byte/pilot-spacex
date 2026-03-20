"""Pydantic schemas and SSRF validation for workspace MCP server endpoints.

Extracted from workspace_mcp_servers.py to stay within the 700-line limit.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

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
    """Request body for registering a new MCP server (remote SSE/HTTP or local stdio)."""

    display_name: str = Field(..., max_length=128, description="Human-readable label")
    url: str | None = Field(
        default=None,
        max_length=512,
        description="Remote MCP server endpoint (SSE, HTTPS only); omit for stdio",
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
    catalog_entry_id: UUID | None = Field(
        default=None, description="Catalog entry this server was installed from"
    )
    installed_catalog_version: str | None = Field(
        default=None, max_length=32, description="Catalog version at install time"
    )
    stdio_command: str | None = Field(
        default=None,
        max_length=256,
        description="Executable command for stdio transport (e.g., 'npx', 'node')",
    )
    stdio_args: list[str] | None = Field(default=None, description="Arguments for stdio command")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        """Validate main server URL against SSRF blocklist (only if provided)."""
        if v is None:
            return v
        return _validate_mcp_url(v)

    @field_validator("oauth_auth_url", "oauth_token_url")
    @classmethod
    def validate_oauth_urls(cls, v: str | None) -> str | None:
        """Validate OAuth URLs against SSRF blocklist."""
        if v is None:
            return v
        return _validate_mcp_url(v)

    @model_validator(mode="after")
    def validate_transport_requirements(self) -> WorkspaceMcpServerCreate:
        """Enforce transport-specific required fields.

        - stdio transport: stdio_command is required; url is not needed.
        - sse/http transport: url is required.
        """
        if self.transport_type == McpTransportType.STDIO:
            if not self.stdio_command:
                raise ValueError("stdio_command is required when transport_type is 'stdio'")
        elif not self.url:
            raise ValueError("url is required when transport_type is 'sse' or 'http'")
        return self


class WorkspaceMcpServerResponse(BaseModel):
    """Response for a single MCP server (never echoes raw token)."""

    id: UUID
    workspace_id: UUID
    display_name: str
    url: str | None = None
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
    # Catalog tracking fields (MCPC-02, MCPC-03)
    catalog_entry_id: str | None = None
    installed_catalog_version: str | None = None
    # Stdio fields (returned only for stdio servers)
    stdio_command: str | None = None
    stdio_args: str | None = None  # JSON string from DB

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
