"""OAuth helper functions for workspace MCP server management.

Extracted from workspace_mcp_servers.py to keep that file under 700 lines.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from pilot_space.infrastructure.database.models.workspace_mcp_server import WorkspaceMcpServer
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)


async def _refresh_oauth_token(
    server: WorkspaceMcpServer,
    repo: Any,
) -> bool:
    """POST a refresh_token grant to the server's OAuth token endpoint.

    On success, updates server.auth_token_encrypted (and optionally
    refresh_token_encrypted + token_expires_at) in-place and persists
    via repo.update(server), then returns True.

    On any failure (missing fields, HTTP error, missing access_token in
    response, unexpected exception), logs a WARNING and returns False.

    Args:
        server: WorkspaceMcpServer ORM instance to refresh.
        repo: WorkspaceMcpServerRepository bound to the active DB session.

    Returns:
        True if the access token was successfully refreshed, False otherwise.
    """
    from pilot_space.infrastructure.encryption import decrypt_api_key, encrypt_api_key

    if not server.refresh_token_encrypted or not server.oauth_token_url:
        return False
    try:
        refresh_token = decrypt_api_key(server.refresh_token_encrypted)
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                server.oauth_token_url,
                data={
                    "grant_type": "refresh_token",
                    "client_id": server.oauth_client_id or "",
                    "refresh_token": refresh_token,
                },
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()
        new_access = data.get("access_token")
        if not new_access:
            logger.warning(
                "mcp_oauth_refresh_no_access_token",
                server_id=str(server.id),
            )
            return False
        server.auth_token_encrypted = encrypt_api_key(new_access)
        new_refresh = data.get("refresh_token")
        if new_refresh:
            server.refresh_token_encrypted = encrypt_api_key(new_refresh)
        new_expires_in = data.get("expires_in")
        if new_expires_in is not None:
            server.token_expires_at = datetime.now(UTC) + timedelta(seconds=int(new_expires_in))
        await repo.update(server)
        logger.info("mcp_oauth_token_refreshed", server_id=str(server.id))
        return True
    except Exception as exc:
        logger.warning("mcp_oauth_refresh_exception", error=str(exc))
        return False


__all__ = ["_refresh_oauth_token"]
