"""Workspace MCP server CRUD + status + OAuth router (Phase 14 / Phase 25).

Thin HTTP shell — all business logic delegated to McpServerService and
McpOAuthService. Router handles only admin auth checks, RLS context, and
HTTP response construction.

Routes are mounted under /api/v1/workspaces by main.py.
The OAuth callback route is mounted separately under /api/v1/oauth2.
"""

from __future__ import annotations

import urllib.parse
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query, Request, status
from fastapi.responses import RedirectResponse

from pilot_space.api.v1.dependencies import McpOAuthServiceDep, McpServerServiceDep
from pilot_space.api.v1.routers._workspace_admin import get_admin_workspace
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
from pilot_space.application.services.mcp_oauth import McpOAuthService
from pilot_space.dependencies import (
    CurrentUser,
    DbSession,
)
from pilot_space.infrastructure.database.models.workspace_mcp_server import (
    McpServerType,
    McpStatus,
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
    svc: McpServerServiceDep,
) -> WorkspaceMcpServerResponse:
    """Register a new MCP server for the workspace. Requires admin role."""
    await get_admin_workspace(workspace_id, current_user, session)
    await set_rls_context(session, current_user.user_id, workspace_id)

    server = await svc.register_server(
        workspace_id,
        display_name=body.display_name,
        url=body.url,
        url_or_command=body.url_or_command,
        server_type=body.server_type,
        command_runner=body.command_runner,
        transport=body.transport,
        command_args=[body.command_args] if body.command_args is not None else None,
        auth_type=body.auth_type,
        auth_token=body.auth_token,
        oauth_client_id=body.oauth_client_id,
        oauth_auth_url=body.oauth_auth_url,
        oauth_token_url=body.oauth_token_url,
        oauth_scopes=body.oauth_scopes,
        headers=body.headers,
        env_vars=body.env_vars,
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
    svc: McpServerServiceDep,
    server_type: McpServerType | None = Query(default=None),
    mcp_status: McpStatus | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, max_length=128),
) -> WorkspaceMcpServerListResponse:
    """List all active (non-deleted) MCP servers. Requires admin role."""
    await get_admin_workspace(workspace_id, current_user, session)
    await set_rls_context(session, current_user.user_id, workspace_id)

    servers = await svc.list_servers(
        workspace_id,
        server_type=server_type,
        status=mcp_status,
        search=search,
    )
    items = [WorkspaceMcpServerResponse.model_validate(s) for s in servers]
    return WorkspaceMcpServerListResponse(items=items, total=len(items))


# ---------------------------------------------------------------------------
# PATCH /{workspace_id}/mcp-servers/{server_id} -- Partial update (Phase 25)
# ---------------------------------------------------------------------------


@router.patch(
    "/{workspace_id}/mcp-servers/{server_id}",
    response_model=WorkspaceMcpServerResponse,
    tags=["workspaces", "mcp"],
)
async def update_mcp_server(
    workspace_id: UUID,
    server_id: UUID,
    body: WorkspaceMcpServerUpdate,
    current_user: CurrentUser,
    session: DbSession,
    svc: McpServerServiceDep,
) -> WorkspaceMcpServerResponse:
    """Partially update a registered MCP server. Requires admin role."""
    await get_admin_workspace(workspace_id, current_user, session)
    await set_rls_context(session, current_user.user_id, workspace_id)

    # Detect which fields were actually provided in the request body
    provided = body.model_fields_set

    server = await svc.update_server(
        workspace_id,
        server_id,
        display_name=body.display_name,
        url_or_command=body.url_or_command,
        server_type=body.server_type,
        command_runner=body.command_runner,
        transport=body.transport,
        command_args=[body.command_args] if body.command_args is not None else None,
        auth_type=body.auth_type,
        auth_token=body.auth_token,
        oauth_client_id=body.oauth_client_id,
        oauth_auth_url=body.oauth_auth_url,
        oauth_token_url=body.oauth_token_url,
        oauth_scopes=body.oauth_scopes,
        headers=body.headers,
        env_vars=body.env_vars,
        _has_server_type="server_type" in provided,
        _has_transport="transport" in provided,
        _has_url_or_command="url_or_command" in provided,
        _has_command_runner="command_runner" in provided,
        _has_command_args="command_args" in provided,
        _has_auth_type="auth_type" in provided,
        _has_auth_token="auth_token" in provided,
        _has_oauth_client_id="oauth_client_id" in provided,
        _has_oauth_auth_url="oauth_auth_url" in provided,
        _has_oauth_token_url="oauth_token_url" in provided,
        _has_oauth_scopes="oauth_scopes" in provided,
        _has_headers="headers" in provided,
        _has_env_vars="env_vars" in provided,
    )
    return WorkspaceMcpServerResponse.model_validate(server)


# ---------------------------------------------------------------------------
# GET /{workspace_id}/mcp-servers/{server_id}/status -- Legacy probe (MCP-05)
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
    svc: McpServerServiceDep,
) -> McpServerStatusResponse:
    """Legacy connectivity probe (MCP-05). Prefer POST .../test."""
    await get_admin_workspace(workspace_id, current_user, session)
    await set_rls_context(session, current_user.user_id, workspace_id)

    _server, probe_status, checked_at = await svc.probe_status(workspace_id, server_id)

    return McpServerStatusResponse(
        server_id=server_id,
        status=probe_status,
        checked_at=checked_at,
    )


# ---------------------------------------------------------------------------
# POST /{workspace_id}/mcp-servers/{server_id}/test -- Connection test (Phase 25)
# ---------------------------------------------------------------------------


@router.post(
    "/{workspace_id}/mcp-servers/{server_id}/test",
    response_model=McpServerTestResponse,
    tags=["workspaces", "mcp"],
)
async def test_mcp_server_connection(
    workspace_id: UUID,
    server_id: UUID,
    current_user: CurrentUser,
    session: DbSession,
    svc: McpServerServiceDep,
) -> McpServerTestResponse:
    """On-demand connection test. Requires admin role."""
    await get_admin_workspace(workspace_id, current_user, session)
    await set_rls_context(session, current_user.user_id, workspace_id)

    _server, result = await svc.test_connection(workspace_id, server_id)

    return McpServerTestResponse(
        server_id=server_id,
        status=result.status,
        latency_ms=result.latency_ms,
        checked_at=result.checked_at,
        error_detail=result.error_detail,
    )


# ---------------------------------------------------------------------------
# POST /{workspace_id}/mcp-servers/{server_id}/enable -- Enable (Phase 25)
# ---------------------------------------------------------------------------


@router.post(
    "/{workspace_id}/mcp-servers/{server_id}/enable",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["workspaces", "mcp"],
)
async def enable_mcp_server(
    workspace_id: UUID,
    server_id: UUID,
    current_user: CurrentUser,
    session: DbSession,
    svc: McpServerServiceDep,
) -> None:
    """Enable a previously disabled MCP server. Requires admin role."""
    await get_admin_workspace(workspace_id, current_user, session)
    await set_rls_context(session, current_user.user_id, workspace_id)

    await svc.enable_server(workspace_id, server_id)


# ---------------------------------------------------------------------------
# POST /{workspace_id}/mcp-servers/{server_id}/disable -- Disable (Phase 25)
# ---------------------------------------------------------------------------


@router.post(
    "/{workspace_id}/mcp-servers/{server_id}/disable",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["workspaces", "mcp"],
)
async def disable_mcp_server(
    workspace_id: UUID,
    server_id: UUID,
    current_user: CurrentUser,
    session: DbSession,
    svc: McpServerServiceDep,
) -> None:
    """Disable an MCP server. Requires admin role."""
    await get_admin_workspace(workspace_id, current_user, session)
    await set_rls_context(session, current_user.user_id, workspace_id)

    await svc.disable_server(workspace_id, server_id)


# ---------------------------------------------------------------------------
# POST /{workspace_id}/mcp-servers/import -- Bulk JSON import (Phase 25)
# ---------------------------------------------------------------------------


@router.post(
    "/{workspace_id}/mcp-servers/import",
    response_model=ImportMcpServersResponse,
    tags=["workspaces", "mcp"],
)
async def import_mcp_servers(
    workspace_id: UUID,
    body: ImportMcpServersRequest,
    current_user: CurrentUser,
    session: DbSession,
    svc: McpServerServiceDep,
) -> ImportMcpServersResponse:
    """Bulk import MCP servers from a Claude/Cursor/VS Code JSON config. Requires admin."""
    await get_admin_workspace(workspace_id, current_user, session)
    await set_rls_context(session, current_user.user_id, workspace_id)

    result = await svc.import_servers(workspace_id, body.config_json)

    return ImportMcpServersResponse(
        imported=[ImportedServerEntry(name=e.name, id=e.id) for e in result.imported],
        skipped=[SkippedServerEntry(name=e.name, reason=e.reason) for e in result.skipped],
        errors=[ErrorServerEntry(name=e.name, reason=e.reason) for e in result.errors],
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
    svc: McpServerServiceDep,
) -> None:
    """Soft-delete a registered MCP server. Requires admin role."""
    await get_admin_workspace(workspace_id, current_user, session)
    await set_rls_context(session, current_user.user_id, workspace_id)

    await svc.delete_server(workspace_id, server_id)


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
    svc: McpOAuthServiceDep,
) -> McpOAuthUrlResponse:
    """Build OAuth 2.0 authorization URL. Requires admin role."""
    workspace = await get_admin_workspace(workspace_id, current_user, session)
    await set_rls_context(session, current_user.user_id, workspace_id)

    from pilot_space.config import get_settings as _get_settings

    result = await svc.initiate_oauth(
        workspace_id=workspace_id,
        server_id=server_id,
        user_id=current_user.user_id,
        workspace_slug=workspace.slug,
        backend_url=_get_settings().backend_url,
    )
    return McpOAuthUrlResponse(auth_url=result.auth_url, state=result.state)


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
    """Handle OAuth 2.0 callback for MCP server token exchange (MCP-03)."""
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

    from pilot_space.config import get_settings as _get_settings

    result = await McpOAuthService.handle_callback(
        redis=redis_client,
        code=code,
        state=state,
        backend_url=_get_settings().backend_url,
        workspace_slug_re=WORKSPACE_SLUG_RE,
    )
    return RedirectResponse(url=result.redirect_path)


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


__all__ = ["mcp_oauth_callback_router", "router"]
