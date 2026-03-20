"""SSRF and command-injection validators for MCP server configuration.

Shared by the API layer (WorkspaceMcpServerCreate/Update schemas) and the
application service layer (ImportMcpServersService) so that every code path
that stores a url_or_command value applies identical security rules.
"""

from __future__ import annotations

import ipaddress
import re
import socket
import urllib.parse

from pilot_space.infrastructure.database.models.workspace_mcp_server import McpServerType

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Shell metacharacters disallowed in NPX/UVX commands (command injection prevention)
SHELL_METACHAR_RE = re.compile(r"[;&|$`(){}<>]")

# Private, loopback, link-local and cloud-metadata CIDR ranges to block
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),       # RFC 1918
    ipaddress.ip_network("172.16.0.0/12"),     # RFC 1918
    ipaddress.ip_network("192.168.0.0/16"),    # RFC 1918
    ipaddress.ip_network("127.0.0.0/8"),       # Loopback
    ipaddress.ip_network("169.254.0.0/16"),    # Link-local / AWS metadata
    ipaddress.ip_network("100.64.0.0/10"),     # Shared address space (RFC 6598)
    ipaddress.ip_network("::1/128"),           # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),          # IPv6 unique local
    ipaddress.ip_network("fe80::/10"),         # IPv6 link-local
]

# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------


def validate_mcp_url(url: str) -> str:
    """Validate MCP server URL to prevent SSRF attacks.

    Enforces:
    - HTTPS scheme only.
    - Hostname must not resolve to private/loopback/link-local/metadata IPs.

    Note: Hostname resolution happens at validation time via getaddrinfo.
    Runtime probes must use ``follow_redirects=False`` to prevent redirect-based
    bypass.

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

    try:
        addr_infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        # Hostname cannot be resolved at validation time — allow through;
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


def validate_npx_uvx_command(command: str, server_type: McpServerType) -> str:
    """Validate NPX or UVX command to prevent command injection.

    Enforces:
    - Must not be empty.
    - Must not contain shell metacharacters: ; & | $ ` ( ) { } < >

    Args:
        command: The url_or_command string for a Command-type server.
        server_type: McpServerType.NPX or McpServerType.UVX.

    Returns:
        The validated command string.

    Raises:
        ValueError: If the command fails any validation check.
    """
    if not command.strip():
        raise ValueError("Command must not be empty")
    if SHELL_METACHAR_RE.search(command):
        raise ValueError(
            f"Command for {server_type.value} server contains disallowed shell metacharacters"
        )
    return command


__all__ = [
    "SHELL_METACHAR_RE",
    "validate_mcp_url",
    "validate_npx_uvx_command",
]
