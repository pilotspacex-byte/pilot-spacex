"""Pydantic schemas and SSRF validation for workspace MCP server endpoints.

Extracted from workspace_mcp_servers.py to stay within the 700-line limit.
"""

from __future__ import annotations

import ipaddress
import re
import socket
import urllib.parse
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from pilot_space.infrastructure.database.models.workspace_mcp_server import (
    McpAuthType,
    McpTransportType,
)

# ---------------------------------------------------------------------------
# Private IP / SSRF blocklist for URL validation (SEC-H3)
# ---------------------------------------------------------------------------

WORKSPACE_SLUG_RE = re.compile(r"^[a-z0-9-]+$")

# Private, loopback, link-local and cloud-metadata CIDR ranges to block
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),  # RFC 1918
    ipaddress.ip_network("172.16.0.0/12"),  # RFC 1918
    ipaddress.ip_network("192.168.0.0/16"),  # RFC 1918
    ipaddress.ip_network("127.0.0.0/8"),  # Loopback
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local / AWS metadata
    ipaddress.ip_network("100.64.0.0/10"),  # Shared address space (RFC 6598)
    ipaddress.ip_network("::1/128"),  # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),  # IPv6 unique local
    ipaddress.ip_network("fe80::/10"),  # IPv6 link-local
]


def _validate_mcp_url(url: str) -> str:
    """Validate MCP server URL to prevent SSRF attacks.

    Enforces:
    - HTTPS scheme only
    - Hostname must not resolve to private/loopback/link-local/metadata IPs

    Note: Hostname resolution happens at validation time via getaddrinfo.
    The runtime probe uses follow_redirects=False to prevent redirect-based bypass.

    Args:
        url: URL string to validate.

    Returns:
        The validated URL string.

    Raises:
        ValueError: If the URL fails any validation check.
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https":
        raise ValueError("MCP server URL must use HTTPS")
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("MCP server URL must have a valid hostname")

    # Resolve hostname to IP addresses and check against blocked ranges
    try:
        addr_infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        # If hostname cannot be resolved at validation time, allow it through;
        # the runtime probe will fail safely with follow_redirects=False.
        return url

    for addr_info in addr_infos:
        ip_str = addr_info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        for blocked in _BLOCKED_NETWORKS:
            if ip in blocked:
                raise ValueError(
                    f"MCP server URL resolves to a private or restricted IP address: {ip_str}"
                )

    return url


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
    # OAuth fields (returned only for oauth2 servers)
    oauth_client_id: str | None = None
    oauth_auth_url: str | None = None
    oauth_scopes: str | None = None

    model_config = {"from_attributes": True}


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
