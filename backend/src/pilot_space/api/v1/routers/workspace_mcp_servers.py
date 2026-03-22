"""Workspace MCP server CRUD + status + OAuth router (Phase 14, MCP-01 to MCP-06).

Provides endpoints for admins to register, list, inspect, and delete
remote Model Context Protocol (MCP) servers scoped to a workspace.
OAuth 2.0 authorization flow is supported for providers requiring it.

Routes are mounted under /api/v1/workspaces by main.py.
The OAuth callback route is mounted separately under /api/v1/oauth2.
"""

from __future__ import annotations

import secrets
import urllib.parse
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import httpx
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from pilot_space.api.v1.routers._mcp_server_schemas import (
    WORKSPACE_SLUG_RE,
    McpOAuthUrlResponse,
    McpServerStatusResponse,
    WorkspaceMcpServerCreate,
    WorkspaceMcpServerListResponse,
    WorkspaceMcpServerResponse,
)
from pilot_space.api.v1.routers._workspace_admin import get_admin_workspace
from pilot_space.dependencies import (
    CurrentUser,
    DbSession,
)
from pilot_space.infrastructure.database.models.workspace_mcp_server import (
    McpAuthType,
    WorkspaceMcpServer,
)
from pilot_space.infrastructure.database.rls import set_rls_context
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()
mcp_oauth_callback_router = APIRouter()


# ---------------------------------------------------------------------------
# POST /{workspace_id}/mcp-servers -- Register server (MCP-01, MCP-02)
# ---------------------------------------------------------------------------


@router.post(
    "/{workspace_id}/mcp-servers",
    response_model=WorkspaceMcpServerResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["workspaces", "mcp"],
)
async def register_mcp_server(
    workspace_id: UUID,
    body: WorkspaceMcpServerCreate,
    current_user: CurrentUser,
    session: DbSession,
) -> WorkspaceMcpServerResponse:
    """Register a new remote MCP server for the workspace (MCP-01).

    Bearer tokens are encrypted with Fernet before storage (MCP-02).
    Returns 201 with the created server; auth token is never echoed back.
    Requires admin role.

    Args:
        workspace_id: Target workspace UUID.
        body: Server registration data.
        current_user: Authenticated user (must be admin).
        session: Database session.

    Returns:
        Created MCP server details (without token).
    """
    await get_admin_workspace(workspace_id, current_user, session)
    await set_rls_context(session, current_user.user_id, workspace_id)

    from pilot_space.infrastructure.database.repositories.workspace_mcp_server_repository import (
        WorkspaceMcpServerRepository,
    )
    from pilot_space.infrastructure.encryption import encrypt_api_key

    token_encrypted: str | None = None
    if body.auth_token:
        token_encrypted = encrypt_api_key(body.auth_token)

    server = WorkspaceMcpServer(
        workspace_id=workspace_id,
        display_name=body.display_name,
        url=body.url,
        auth_type=body.auth_type,
        auth_token_encrypted=token_encrypted,
        oauth_client_id=body.oauth_client_id,
        oauth_auth_url=body.oauth_auth_url,
        oauth_token_url=body.oauth_token_url,
        oauth_scopes=body.oauth_scopes,
    )

    repo = WorkspaceMcpServerRepository(session=session)
    server = await repo.create(server)

    logger.info(
        "mcp_server_registered",
        workspace_id=str(workspace_id),
        server_id=str(server.id),
        auth_type=body.auth_type,
    )

    return WorkspaceMcpServerResponse.model_validate(server)


# ---------------------------------------------------------------------------
# GET /{workspace_id}/mcp-servers -- List active servers (MCP-01)
# ---------------------------------------------------------------------------


@router.get(
    "/{workspace_id}/mcp-servers",
    response_model=WorkspaceMcpServerListResponse,
    tags=["workspaces", "mcp"],
)
async def list_mcp_servers(
    workspace_id: UUID,
    current_user: CurrentUser,
    session: DbSession,
) -> WorkspaceMcpServerListResponse:
    """List all active (non-deleted) MCP servers for a workspace.

    Requires admin role.

    Args:
        workspace_id: Target workspace UUID.
        current_user: Authenticated user (must be admin).
        session: Database session.

    Returns:
        List of MCP server summaries.
    """
    await get_admin_workspace(workspace_id, current_user, session)
    await set_rls_context(session, current_user.user_id, workspace_id)

    from pilot_space.infrastructure.database.repositories.workspace_mcp_server_repository import (
        WorkspaceMcpServerRepository,
    )

    repo = WorkspaceMcpServerRepository(session=session)
    servers = await repo.get_active_by_workspace(workspace_id)
    items = [WorkspaceMcpServerResponse.model_validate(s) for s in servers]
    return WorkspaceMcpServerListResponse(items=items, total=len(items))


# ---------------------------------------------------------------------------
# GET /{workspace_id}/mcp-servers/{server_id}/status -- Connectivity probe (MCP-05)
# ---------------------------------------------------------------------------


@router.get(
    "/{workspace_id}/mcp-servers/{server_id}/status",
    response_model=McpServerStatusResponse,
    tags=["workspaces", "mcp"],
)
async def get_mcp_server_status(
    workspace_id: UUID,
    server_id: UUID,
    current_user: CurrentUser,
    session: DbSession,
) -> McpServerStatusResponse:
    """Probe connectivity of a registered MCP server (MCP-05).

    Sends an HTTP GET to the server URL with 5s timeout. Updates
    last_status and last_status_checked_at on the row before returning.
    Requires admin role.

    Status values:
      - "connected": HTTP < 500 received
      - "failed": HTTP >= 500 or connection error
      - "unknown": unexpected exception

    Args:
        workspace_id: Target workspace UUID.
        server_id: Server to probe.
        current_user: Authenticated user (must be admin).
        session: Database session.

    Returns:
        Status probe result.
    """
    await get_admin_workspace(workspace_id, current_user, session)
    await set_rls_context(session, current_user.user_id, workspace_id)

    from pilot_space.infrastructure.database.repositories.workspace_mcp_server_repository import (
        WorkspaceMcpServerRepository,
    )
    from pilot_space.infrastructure.encryption import decrypt_api_key

    repo = WorkspaceMcpServerRepository(session=session)
    server = await repo.get_by_workspace_and_id(server_id=server_id, workspace_id=workspace_id)
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MCP server not found",
        )

    # Build headers with auth if available
    headers: dict[str, str] = {}
    if server.auth_token_encrypted:
        try:
            token = decrypt_api_key(server.auth_token_encrypted)
            headers["Authorization"] = f"Bearer {token}"
        except Exception:
            logger.warning(
                "mcp_status_token_decrypt_failed",
                server_id=str(server_id),
                workspace_id=str(workspace_id),
            )

    # HTTP probe — follow_redirects=False prevents redirect-based SSRF bypass (SEC-H3)
    probe_status = "unknown"
    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=False) as client:
            response = await client.get(server.url, headers=headers)
            probe_status = "connected" if response.status_code < 500 else "failed"
    except (httpx.ConnectError, httpx.TimeoutException, httpx.RequestError):
        probe_status = "failed"
    except Exception:
        probe_status = "unknown"

    # Persist status
    checked_at = datetime.now(UTC)
    server.last_status = probe_status
    server.last_status_checked_at = checked_at
    await repo.update(server)

    logger.info(
        "mcp_server_status_probed",
        server_id=str(server_id),
        workspace_id=str(workspace_id),
        status=probe_status,
    )

    return McpServerStatusResponse(
        server_id=server_id,
        status=probe_status,
        checked_at=checked_at,
    )


# ---------------------------------------------------------------------------
# DELETE /{workspace_id}/mcp-servers/{server_id} -- Soft-delete (MCP-06)
# ---------------------------------------------------------------------------


@router.delete(
    "/{workspace_id}/mcp-servers/{server_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["workspaces", "mcp"],
)
async def delete_mcp_server(
    workspace_id: UUID,
    server_id: UUID,
    current_user: CurrentUser,
    session: DbSession,
) -> None:
    """Soft-delete a registered MCP server (MCP-06).

    Sets is_deleted=True on the row; the record is preserved for audit.
    The server will no longer appear in list responses or be loaded
    by PilotSpaceAgent hot-load.
    Requires admin role.

    Args:
        workspace_id: Target workspace UUID.
        server_id: Server to delete.
        current_user: Authenticated user (must be admin).
        session: Database session.
    """
    await get_admin_workspace(workspace_id, current_user, session)
    await set_rls_context(session, current_user.user_id, workspace_id)

    from pilot_space.infrastructure.database.repositories.workspace_mcp_server_repository import (
        WorkspaceMcpServerRepository,
    )

    repo = WorkspaceMcpServerRepository(session=session)
    server = await repo.get_by_workspace_and_id(server_id=server_id, workspace_id=workspace_id)
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MCP server not found",
        )

    await repo.soft_delete(server)
    logger.info(
        "mcp_server_deleted",
        workspace_id=str(workspace_id),
        server_id=str(server_id),
    )


# ---------------------------------------------------------------------------
# GET /{workspace_id}/mcp-servers/{server_id}/oauth-url -- OAuth init (MCP-03)
# ---------------------------------------------------------------------------


@router.get(
    "/{workspace_id}/mcp-servers/{server_id}/oauth-url",
    response_model=McpOAuthUrlResponse,
    tags=["workspaces", "mcp"],
)
async def get_mcp_oauth_url(
    workspace_id: UUID,
    server_id: UUID,
    current_user: CurrentUser,
    session: DbSession,
    request: Request,
) -> McpOAuthUrlResponse:
    """Build OAuth 2.0 authorization URL for a registered MCP server (MCP-03).

    Generates a cryptographic nonce, stores OAuth state in Redis with
    10-minute TTL, and returns the full authorization URL for the admin
    to open in a browser.

    Only valid when auth_type=oauth2 and oauth_auth_url is configured.
    Requires admin role.

    Args:
        workspace_id: Target workspace UUID.
        server_id: Server requiring OAuth authorization.
        current_user: Authenticated user (must be admin).
        session: Database session.
        request: FastAPI request (for Redis container access).

    Returns:
        Authorization URL and state token.
    """
    workspace = await get_admin_workspace(workspace_id, current_user, session)
    await set_rls_context(session, current_user.user_id, workspace_id)

    from pilot_space.infrastructure.database.repositories.workspace_mcp_server_repository import (
        WorkspaceMcpServerRepository,
    )

    repo = WorkspaceMcpServerRepository(session=session)
    server = await repo.get_by_workspace_and_id(server_id=server_id, workspace_id=workspace_id)
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MCP server not found",
        )
    if server.auth_type != McpAuthType.OAUTH2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Server is not configured for OAuth2 auth_type",
        )
    if not server.oauth_auth_url or not server.oauth_client_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Server missing oauth_auth_url or oauth_client_id",
        )

    nonce = secrets.token_urlsafe(32)
    state = f"mcp_oauth_{server_id}_{nonce}"

    # Store state in Redis with 10-minute TTL (includes workspace_slug for callback redirect
    # and user_id so the callback can set RLS context without re-authentication)
    redis_client = _get_redis_client(request)
    if redis_client is not None:
        state_data: dict[str, Any] = {
            "server_id": str(server_id),
            "workspace_id": str(workspace_id),
            "workspace_slug": workspace.slug,
            "user_id": str(current_user.user_id),
            "nonce": nonce,
        }
        import json

        await redis_client.client.set(
            f"mcp_oauth_state:{state}",
            json.dumps(state_data),
            ex=600,  # 10 minutes
        )

    # Build OAuth2 authorization URL
    callback_url = str(request.base_url).rstrip("/") + "/api/v1/oauth2/mcp-callback"
    params = {
        "response_type": "code",
        "client_id": server.oauth_client_id,
        "redirect_uri": callback_url,
        "state": state,
    }
    if server.oauth_scopes:
        params["scope"] = server.oauth_scopes

    auth_url = server.oauth_auth_url + "?" + urllib.parse.urlencode(params)

    logger.info(
        "mcp_oauth_url_generated",
        workspace_id=str(workspace_id),
        server_id=str(server_id),
    )

    return McpOAuthUrlResponse(auth_url=auth_url, state=state)


# ---------------------------------------------------------------------------
# OAuth callback -- mounted separately under /api/v1/oauth2
# ---------------------------------------------------------------------------


@mcp_oauth_callback_router.get(
    "/oauth2/mcp-callback",
    tags=["mcp", "oauth"],
    include_in_schema=True,
)
async def mcp_oauth_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    """Handle OAuth 2.0 callback for MCP server token exchange (MCP-03).

    No JWT authentication required -- this endpoint is called by the OAuth
    provider's redirect after the admin grants access. It:
      1. Reads OAuth state from Redis to get server_id + workspace_id + workspace_slug.
      2. POSTs to the server's token_url to exchange code for access token.
      3. Encrypts the access token and stores it in auth_token_encrypted.
      4. Redirects browser to /{workspace_slug}/settings/mcp-servers?status=connected.

    Args:
        request: FastAPI request (for Redis + DB access).
        code: Authorization code from provider.
        state: State token matching what was stored in Redis.
        error: OAuth error from provider (if authorization failed).
    """
    # Fallback redirect for error paths before state is parsed
    fallback_redirect = "/settings/mcp-servers"

    if error:
        logger.warning("mcp_oauth_callback_error", oauth_error=error)
        return RedirectResponse(
            url=fallback_redirect
            + "?"
            + urllib.parse.urlencode({"status": "error", "reason": error})
        )

    if not code or not state:
        return RedirectResponse(url=f"{fallback_redirect}?status=error&reason=missing_params")

    redis_client = _get_redis_client(request)
    if redis_client is None:
        return RedirectResponse(url=f"{fallback_redirect}?status=error&reason=no_redis")

    import json

    raw = await redis_client.client.get(f"mcp_oauth_state:{state}")
    if raw is None:
        return RedirectResponse(url=f"{fallback_redirect}?status=error&reason=invalid_state")

    try:
        state_data = json.loads(raw)
        server_id = UUID(state_data["server_id"])
        workspace_id = UUID(state_data["workspace_id"])
        # user_id stored in state by get_mcp_oauth_url for RLS context in callback
        initiating_user_id = UUID(state_data["user_id"])
    except (json.JSONDecodeError, KeyError, ValueError):
        return RedirectResponse(url=f"{fallback_redirect}?status=error&reason=state_decode_error")

    # Build redirect base with workspace slug (if available in state).
    # Validate slug against allowlist to prevent open redirect (SEC-C3).
    workspace_slug = state_data.get("workspace_slug", "")
    if workspace_slug and not WORKSPACE_SLUG_RE.match(workspace_slug):
        workspace_slug = ""
    redirect_base = (
        f"/{workspace_slug}/settings/mcp-servers" if workspace_slug else "/settings/mcp-servers"
    )

    # Invalidate state immediately (one-time use)
    await redis_client.client.delete(f"mcp_oauth_state:{state}")

    # Load server from DB
    from pilot_space.infrastructure.database import get_db_session
    from pilot_space.infrastructure.database.repositories.workspace_mcp_server_repository import (
        WorkspaceMcpServerRepository,
    )
    from pilot_space.infrastructure.encryption import encrypt_api_key

    try:
        async with get_db_session() as db_session:
            # SEC-C3: Set RLS context using the initiating user's ID stored in OAuth state
            await set_rls_context(db_session, initiating_user_id, workspace_id)
            repo = WorkspaceMcpServerRepository(session=db_session)
            server = await repo.get_by_workspace_and_id(
                server_id=server_id, workspace_id=workspace_id
            )
            if not server or not server.oauth_token_url:
                return RedirectResponse(url=f"{redirect_base}?status=error&reason=server_not_found")

            # Exchange code for token
            callback_url = str(request.base_url).rstrip("/") + "/api/v1/oauth2/mcp-callback"
            token_response = await _exchange_oauth_code(
                token_url=server.oauth_token_url,
                client_id=server.oauth_client_id or "",
                code=code,
                redirect_uri=callback_url,
            )

            if token_response is None:
                return RedirectResponse(
                    url=f"{redirect_base}?status=error&reason=token_exchange_failed"
                )

            # Encrypt and store token
            encrypted = encrypt_api_key(token_response)
            server.auth_token_encrypted = encrypted
            await repo.update(server)

            logger.info(
                "mcp_oauth_token_stored",
                server_id=str(server_id),
                workspace_id=str(workspace_id),
            )

    except Exception as exc:
        logger.error(
            "mcp_oauth_callback_exception",
            error=str(exc),
            exc_info=True,
        )
        return RedirectResponse(url=f"{redirect_base}?status=error&reason=internal_error")

    return RedirectResponse(url=f"{redirect_base}?status=connected")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_redis_client(request: Request) -> Any:
    """Extract RedisClient from app container, returning None if unavailable."""
    try:
        container = request.app.state.container
        return container.redis_client()
    except Exception:
        return None


async def _exchange_oauth_code(
    token_url: str,
    client_id: str,
    code: str,
    redirect_uri: str,
) -> str | None:
    """Exchange authorization code for access token.

    Args:
        token_url: OAuth 2.0 token endpoint.
        client_id: OAuth client ID.
        code: Authorization code from provider.
        redirect_uri: Redirect URI used in the authorization request.

    Returns:
        Access token string, or None on failure.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                token_url,
                data={
                    "grant_type": "authorization_code",
                    "client_id": client_id,
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
            return data.get("access_token")
    except Exception as exc:
        logger.warning("mcp_oauth_token_exchange_failed", error=str(exc))
        return None


__all__ = ["mcp_oauth_callback_router", "router"]
