"""Workspace MCP server CRUD + status + OAuth router (Phase 14 / Phase 25).

Phase 25 additions:
- Extended POST /mcp-servers: new fields (server_type, transport, url_or_command, etc.)
- GET /mcp-servers: server_type, status, search query params
- PATCH /mcp-servers/{id}: partial update
- POST /mcp-servers/{id}/enable: admin enable
- POST /mcp-servers/{id}/disable: admin disable
- POST /mcp-servers/{id}/test: on-demand connection test
- POST /mcp-servers/import: bulk JSON import

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
from fastapi import APIRouter, Query, Request, status
from fastapi.responses import RedirectResponse

from pilot_space.api.v1.routers._mcp_server_schemas import (
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
from pilot_space.api.v1.routers._workspace_admin import get_admin_workspace
from pilot_space.dependencies import (
    CurrentUser,
    DbSession,
)
from pilot_space.domain.exceptions import (
    ConflictError,
    NotFoundError,
    ServiceUnavailableError,
    ValidationError,
)
from pilot_space.infrastructure.database.models.workspace_mcp_server import (
    McpAuthType,
    McpServerType,
    McpStatus,
    McpTransport,
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
    """Register a new MCP server for the workspace.

    Bearer tokens, headers, and env vars are encrypted with Fernet before storage.
    Secrets are never echoed back in the response (only boolean presence flags).
    Requires admin role.
    """
    await get_admin_workspace(workspace_id, current_user, session)
    await set_rls_context(session, current_user.user_id, workspace_id)

    from pilot_space.infrastructure.database.repositories.workspace_mcp_server_repository import (
        WorkspaceMcpServerRepository,
    )
    from pilot_space.infrastructure.encryption import encrypt_api_key
    from pilot_space.infrastructure.encryption_kv import encrypt_kv

    repo = WorkspaceMcpServerRepository(session=session)

    # Reject duplicate display_name within the workspace — gives a clean 409
    # instead of letting the DB partial-unique index raise an IntegrityError.
    existing = await repo.get_by_display_name(workspace_id, body.display_name)
    if existing is not None:
        raise ConflictError(
            f"An MCP server named {body.display_name!r} already exists in this workspace"
        )

    token_encrypted: str | None = None
    if body.auth_token:
        token_encrypted = encrypt_api_key(body.auth_token)

    # Headers stored as plaintext JSON (not sensitive)
    import json as _json

    headers_json: str | None = None
    if body.headers:
        headers_json = _json.dumps(body.headers)

    env_vars_encrypted: str | None = None
    if body.env_vars:
        env_vars_encrypted = encrypt_kv(body.env_vars)

    # url_or_command is validated and set by the model_validator
    url_or_command = body.url_or_command or body.url or ""
    # Mirror into legacy url column (same width now — no truncation needed)
    url_val = url_or_command if url_or_command else None

    server = WorkspaceMcpServer(
        workspace_id=workspace_id,
        display_name=body.display_name,
        url=url_val,
        url_or_command=url_or_command,
        server_type=body.server_type,
        command_runner=body.command_runner,
        transport=body.transport,
        command_args=body.command_args,
        auth_type=body.auth_type,
        auth_token_encrypted=token_encrypted,
        oauth_client_id=body.oauth_client_id,
        oauth_auth_url=body.oauth_auth_url,
        oauth_token_url=body.oauth_token_url,
        oauth_scopes=body.oauth_scopes,
        headers_json=headers_json,
        env_vars_encrypted=env_vars_encrypted,
        is_enabled=True,
        last_status=McpStatus.ENABLED,
    )

    server = await repo.create(server)

    logger.info(
        "mcp_server_registered",
        workspace_id=str(workspace_id),
        server_id=str(server.id),
        auth_type=body.auth_type,
        server_type=body.server_type,
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
    server_type: McpServerType | None = Query(default=None),
    mcp_status: McpStatus | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, max_length=128),
) -> WorkspaceMcpServerListResponse:
    """List all active (non-deleted) MCP servers for a workspace.

    Supports optional filtering by server_type, status, and name/URL search.
    Requires admin role.
    """
    await get_admin_workspace(workspace_id, current_user, session)
    await set_rls_context(session, current_user.user_id, workspace_id)

    from pilot_space.infrastructure.database.repositories.workspace_mcp_server_repository import (
        WorkspaceMcpServerRepository,
    )

    repo = WorkspaceMcpServerRepository(session=session)
    servers = await repo.get_filtered(
        workspace_id=workspace_id,
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
) -> WorkspaceMcpServerResponse:
    """Partially update a registered MCP server.

    Only provided fields are updated; omitted fields retain their current values.
    For secret fields (auth_token, headers, env_vars), omitting them preserves
    the existing encrypted value. Providing a new value overwrites the secret.
    Requires admin role.
    """
    await get_admin_workspace(workspace_id, current_user, session)
    await set_rls_context(session, current_user.user_id, workspace_id)

    from pilot_space.infrastructure.database.repositories.workspace_mcp_server_repository import (
        WorkspaceMcpServerRepository,
    )
    from pilot_space.infrastructure.encryption import encrypt_api_key
    from pilot_space.infrastructure.encryption_kv import encrypt_kv

    repo = WorkspaceMcpServerRepository(session=session)
    server = await repo.get_by_workspace_and_id(server_id=server_id, workspace_id=workspace_id)
    if not server:
        raise NotFoundError("MCP server not found")

    # Apply non-secret scalar fields
    if body.display_name is not None:
        # Reject rename to a name already taken by another active server.
        if body.display_name != server.display_name:
            name_conflict = await repo.get_by_display_name(workspace_id, body.display_name)
            if name_conflict is not None:
                raise ConflictError(
                    f"An MCP server named {body.display_name!r} already exists in this workspace"
                )
        server.display_name = body.display_name

    # Determine the effective server_type and url_or_command after this PATCH so
    # we can run the appropriate security validation before committing any change.
    effective_server_type = body.server_type if body.server_type is not None else server.server_type
    effective_url_or_command = (
        body.url_or_command
        if body.url_or_command is not None
        else (server.url_or_command or server.url)
    )

    # Cross-field validation: the model_validator on WorkspaceMcpServerUpdate
    # validates (url_or_command, server_type) only when both are present in
    # the request body.  Here we cover the remaining cases:
    #   1. Only server_type changes — re-validate stored url_or_command against new type.
    #   2. Only url_or_command changes — validate new value against stored server_type.
    if body.server_type is not None or body.url_or_command is not None:
        from pilot_space.security.mcp_validation import (
            validate_command_package as _validate_command_package,
            validate_mcp_url as _validate_mcp_url,
        )

        # Skip when both are present — already validated by the Pydantic model_validator.
        if not (body.server_type is not None and body.url_or_command is not None):
            if not effective_url_or_command:
                raise ValidationError("url_or_command is required when changing server_type")
            try:
                if effective_server_type == McpServerType.REMOTE:
                    _validate_mcp_url(effective_url_or_command)
                elif effective_server_type == McpServerType.COMMAND:
                    effective_runner = (
                        body.command_runner
                        if body.command_runner is not None
                        else server.command_runner
                    )
                    if effective_runner is not None:
                        _validate_command_package(effective_url_or_command, effective_runner)
            except ValueError as exc:
                raise ValidationError(str(exc)) from exc

    # Cross-field validation: server_type / transport compatibility.
    # The model_validator on WorkspaceMcpServerUpdate already covers the case
    # where both are present in the request body.  Here we handle the case
    # where only one changes — we must check against the stored value.
    effective_transport = body.transport if body.transport is not None else server.transport
    if effective_server_type == McpServerType.REMOTE:
        if effective_transport not in (McpTransport.SSE, McpTransport.STREAMABLE_HTTP):
            raise ValidationError(
                f"Remote servers only support 'sse' or 'streamable_http' transport, "
                f"got '{effective_transport.value}'"
            )
    elif effective_server_type == McpServerType.COMMAND:
        if effective_transport != McpTransport.STDIO:
            raise ValidationError(
                f"{effective_server_type.value} servers only support 'stdio' transport, "
                f"got '{effective_transport.value}'"
            )

    if body.server_type is not None:
        server.server_type = body.server_type
    if body.command_runner is not None:
        server.command_runner = body.command_runner
    if body.transport is not None:
        server.transport = body.transport
    if body.command_args is not None:
        server.command_args = body.command_args or None

    # auth_type: when it changes, scrub fields that belong to the old type
    if body.auth_type is not None:
        if body.auth_type != server.auth_type:
            if body.auth_type != McpAuthType.BEARER:
                # Switching away from bearer: clear the token
                server.auth_token_encrypted = None
            if body.auth_type != McpAuthType.OAUTH2:
                # Switching away from oauth2: clear all OAuth metadata
                server.oauth_client_id = None
                server.oauth_auth_url = None
                server.oauth_token_url = None
                server.oauth_scopes = None
        server.auth_type = body.auth_type

    # OAuth plaintext fields: None = omit, empty string = clear
    if body.oauth_client_id is not None:
        server.oauth_client_id = body.oauth_client_id.strip() or None
    if body.oauth_auth_url is not None:
        server.oauth_auth_url = body.oauth_auth_url.strip() or None
    if body.oauth_token_url is not None:
        server.oauth_token_url = body.oauth_token_url.strip() or None
    if body.oauth_scopes is not None:
        server.oauth_scopes = body.oauth_scopes.strip() or None

    # url_or_command: already validated above; write to ORM and keep url in sync
    if body.url_or_command is not None:
        server.url_or_command = body.url_or_command
        server.url = body.url_or_command

    # auth_token: None = omit, empty string = clear encrypted field, non-empty = re-encrypt
    if body.auth_token is not None:
        if body.auth_token.strip():
            server.auth_token_encrypted = encrypt_api_key(body.auth_token)
        else:
            server.auth_token_encrypted = None

    if body.headers is not None:
        import json as _json

        if body.headers:
            server.headers_json = _json.dumps(body.headers)
            server.headers_encrypted = None  # Clear legacy encrypted column
        else:
            # Empty dict means "clear headers"
            server.headers_json = None
            server.headers_encrypted = None

    if body.env_vars is not None:
        if body.env_vars:
            server.env_vars_encrypted = encrypt_kv(body.env_vars)
        else:
            server.env_vars_encrypted = None

    server = await repo.update(server)

    logger.info(
        "mcp_server_updated",
        workspace_id=str(workspace_id),
        server_id=str(server_id),
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
) -> McpServerStatusResponse:
    """Legacy connectivity probe (MCP-05).

    Uses 5-second timeout and returns old-style status strings.
    Prefer POST .../test for Phase 25 behavior.
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
        raise NotFoundError("MCP server not found")

    headers: dict[str, str] = {}

    # Merge plaintext headers from headers_json (e.g. custom API key headers)
    if server.headers_json:
        import json as _json

        try:
            parsed = _json.loads(server.headers_json)
            if isinstance(parsed, dict):
                headers.update(parsed)
        except (ValueError, TypeError):
            logger.warning("mcp_status_headers_json_parse_failed", server_id=str(server_id))

    # Authorization from encrypted token takes precedence over headers_json
    if server.auth_token_encrypted:
        try:
            token = decrypt_api_key(server.auth_token_encrypted)
            headers["Authorization"] = f"Bearer {token}"
        except Exception:
            logger.warning("mcp_status_token_decrypt_failed", server_id=str(server_id))

    probe_status = McpStatus.ENABLED  # optimistic default
    url = server.url_or_command or server.url
    if not url:
        probe_status = McpStatus.CONFIG_ERROR
    else:
        try:
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=False) as client:
                response = await client.get(url, headers=headers)
                if response.status_code // 100 == 2:
                    probe_status = McpStatus.ENABLED
                else:
                    probe_status = McpStatus.UNHEALTHY
        except (httpx.ConnectError, httpx.TimeoutException, httpx.RequestError):
            probe_status = McpStatus.UNREACHABLE
        except Exception:
            probe_status = McpStatus.UNHEALTHY

    checked_at = datetime.now(UTC)
    server.last_status_checked_at = checked_at
    server.last_status = probe_status
    await repo.update(server)

    logger.info(
        "mcp_server_status_probed",
        server_id=str(server_id),
        workspace_id=str(workspace_id),
        status=probe_status.value,
    )

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
) -> McpServerTestResponse:
    """On-demand connection test with 10-second timeout.

    Persists last_status and last_status_checked_at on the server row.
    Returns status, latency_ms, and error_detail.
    Requires admin role.
    """
    await get_admin_workspace(workspace_id, current_user, session)
    await set_rls_context(session, current_user.user_id, workspace_id)

    from pilot_space.application.services.mcp.mcp_connection_tester import (
        TestMcpConnectionService,
    )
    from pilot_space.infrastructure.database.repositories.workspace_mcp_server_repository import (
        WorkspaceMcpServerRepository,
    )

    repo = WorkspaceMcpServerRepository(session=session)
    server = await repo.get_by_workspace_and_id(server_id=server_id, workspace_id=workspace_id)
    if not server:
        raise NotFoundError("MCP server not found")

    result = await TestMcpConnectionService.test(server)

    # Persist result
    server.last_status = result.status
    server.last_status_checked_at = result.checked_at
    await repo.update(server)

    logger.info(
        "mcp_server_connection_tested",
        server_id=str(server_id),
        workspace_id=str(workspace_id),
        status=result.status,
        latency_ms=result.latency_ms,
    )

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
) -> None:
    """Enable a previously disabled MCP server.

    Sets is_enabled=True and clears last_status so the poller re-evaluates.
    Requires admin role.
    """
    await get_admin_workspace(workspace_id, current_user, session)
    await set_rls_context(session, current_user.user_id, workspace_id)

    from pilot_space.infrastructure.database.repositories.workspace_mcp_server_repository import (
        WorkspaceMcpServerRepository,
    )

    repo = WorkspaceMcpServerRepository(session=session)
    server = await repo.get_by_workspace_and_id(server_id=server_id, workspace_id=workspace_id)
    if not server:
        raise NotFoundError("MCP server not found")

    await repo.set_enabled(server, enabled=True)
    logger.info("mcp_server_enabled", workspace_id=str(workspace_id), server_id=str(server_id))


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
) -> None:
    """Disable an MCP server.

    Sets is_enabled=False and last_status=DISABLED.
    Disabled servers are excluded from polling and MCP routing.
    Requires admin role.
    """
    await get_admin_workspace(workspace_id, current_user, session)
    await set_rls_context(session, current_user.user_id, workspace_id)

    from pilot_space.infrastructure.database.repositories.workspace_mcp_server_repository import (
        WorkspaceMcpServerRepository,
    )

    repo = WorkspaceMcpServerRepository(session=session)
    server = await repo.get_by_workspace_and_id(server_id=server_id, workspace_id=workspace_id)
    if not server:
        raise NotFoundError("MCP server not found")

    await repo.set_enabled(server, enabled=False)
    logger.info("mcp_server_disabled", workspace_id=str(workspace_id), server_id=str(server_id))


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
) -> ImportMcpServersResponse:
    """Bulk import MCP servers from a Claude/Cursor/VS Code JSON config.

    Parses the config_json, validates each entry, skips name conflicts,
    and creates the rest. Returns imported, skipped, and errors lists.
    Requires admin role.
    """
    await get_admin_workspace(workspace_id, current_user, session)
    await set_rls_context(session, current_user.user_id, workspace_id)

    from pilot_space.application.services.mcp.import_mcp_servers_service import (
        ImportMcpServersService,
    )
    from pilot_space.infrastructure.database.repositories.workspace_mcp_server_repository import (
        WorkspaceMcpServerRepository,
    )

    parsed, parse_errors = ImportMcpServersService.parse_config_json(body.config_json)

    repo = WorkspaceMcpServerRepository(session=session)
    result = await ImportMcpServersService.import_servers(
        workspace_id=workspace_id,
        parsed=parsed,
        repo=repo,
        parse_errors=parse_errors,
    )

    logger.info(
        "mcp_servers_bulk_imported",
        workspace_id=str(workspace_id),
        imported=len(result.imported),
        skipped=len(result.skipped),
        errors=len(result.errors),
    )

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
) -> None:
    """Soft-delete a registered MCP server (MCP-06).

    Sets is_deleted=True on the row; the record is preserved for audit.
    Requires admin role.
    """
    await get_admin_workspace(workspace_id, current_user, session)
    await set_rls_context(session, current_user.user_id, workspace_id)

    from pilot_space.infrastructure.database.repositories.workspace_mcp_server_repository import (
        WorkspaceMcpServerRepository,
    )

    repo = WorkspaceMcpServerRepository(session=session)
    server = await repo.get_by_workspace_and_id(server_id=server_id, workspace_id=workspace_id)
    if not server:
        raise NotFoundError("MCP server not found")

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
        raise NotFoundError("MCP server not found")
    if server.auth_type != McpAuthType.OAUTH2:
        raise ValidationError("Server is not configured for OAuth2 auth_type")
    if not server.oauth_auth_url or not server.oauth_client_id:
        raise ValidationError("Server missing oauth_auth_url or oauth_client_id")

    redis_client = _get_redis_client(request)
    if redis_client is None:
        raise ServiceUnavailableError(
            "OAuth state storage (Redis) is unavailable; cannot initiate OAuth flow"
        )

    # Use a fully opaque state token. server_id and workspace context are stored
    # in Redis under the state key and do not need to be embedded in the state
    # parameter — embedding them unnecessarily exposes the server UUID to third-party
    # OAuth providers that may log or record the state parameter.
    state = secrets.token_urlsafe(32)

    import json

    state_data: dict[str, Any] = {
        "server_id": str(server_id),
        "workspace_id": str(workspace_id),
        "workspace_slug": workspace.slug,
        "user_id": str(current_user.user_id),
    }
    try:
        await redis_client.client.set(
            f"mcp_oauth_state:{state}",
            json.dumps(state_data),
            ex=600,
        )
    except Exception as exc:
        logger.exception("mcp_oauth_state_persist_failed", server_id=str(server_id), error=str(exc))
        raise ServiceUnavailableError(
            "Failed to persist OAuth state; cannot initiate OAuth flow"
        ) from exc

    # Use the configured backend_url instead of request.base_url (which relies on
    # the Host header and can be spoofed in reverse-proxy configurations).
    from pilot_space.config import get_settings as _get_settings

    callback_url = _get_settings().backend_url.rstrip("/") + "/api/v1/oauth2/mcp-callback"
    params = {
        "response_type": "code",
        "client_id": server.oauth_client_id,
        "redirect_uri": callback_url,
        "state": state,
    }
    if server.oauth_scopes:
        params["scope"] = server.oauth_scopes

    auth_url = server.oauth_auth_url + "?" + urllib.parse.urlencode(params)

    logger.info("mcp_oauth_url_generated", workspace_id=str(workspace_id), server_id=str(server_id))
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
        initiating_user_id = UUID(state_data["user_id"])
    except (json.JSONDecodeError, KeyError, ValueError):
        return RedirectResponse(url=f"{fallback_redirect}?status=error&reason=state_decode_error")

    workspace_slug = state_data.get("workspace_slug", "")
    if workspace_slug and not WORKSPACE_SLUG_RE.match(workspace_slug):
        workspace_slug = ""
    redirect_base = (
        f"/{workspace_slug}/settings/mcp-servers" if workspace_slug else "/settings/mcp-servers"
    )

    await redis_client.client.delete(f"mcp_oauth_state:{state}")

    from pilot_space.infrastructure.database import get_db_session
    from pilot_space.infrastructure.database.repositories.workspace_mcp_server_repository import (
        WorkspaceMcpServerRepository,
    )
    from pilot_space.infrastructure.encryption import encrypt_api_key

    try:
        async with get_db_session() as db_session:
            await set_rls_context(db_session, initiating_user_id, workspace_id)
            repo = WorkspaceMcpServerRepository(session=db_session)
            server = await repo.get_by_workspace_and_id(
                server_id=server_id, workspace_id=workspace_id
            )
            if not server or not server.oauth_token_url:
                return RedirectResponse(url=f"{redirect_base}?status=error&reason=server_not_found")

            from pilot_space.config import get_settings as _get_settings

            callback_url = _get_settings().backend_url.rstrip("/") + "/api/v1/oauth2/mcp-callback"
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

            encrypted = encrypt_api_key(token_response)
            server.auth_token_encrypted = encrypted
            await repo.update(server)

            logger.info(
                "mcp_oauth_token_stored",
                server_id=str(server_id),
                workspace_id=str(workspace_id),
            )

    except Exception as exc:
        logger.error("mcp_oauth_callback_exception", error=str(exc), exc_info=True)
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
    """Exchange authorization code for access token."""
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
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
