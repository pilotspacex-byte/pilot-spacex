"""MCP server CRUD service.

Extracts business logic from workspace_mcp_servers.py router into a proper
service layer following Clean Architecture. Handles CRUD operations, cross-field
validation, encryption/decryption of server configs, status probing, and
enable/disable toggles.

All admin authorization and RLS context setup remain in the router.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.domain.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from pilot_space.infrastructure.database.models.workspace_mcp_server import (
    McpAuthType,
    McpServerType,
    McpStatus,
    McpTransport,
    WorkspaceMcpServer,
)
from pilot_space.infrastructure.database.repositories.workspace_mcp_server_repository import (
    WorkspaceMcpServerRepository,
)
from pilot_space.infrastructure.encryption import decrypt_api_key, encrypt_api_key
from pilot_space.infrastructure.encryption_kv import encrypt_kv
from pilot_space.infrastructure.logging import get_logger
from pilot_space.security.mcp_validation import (
    validate_command_package,
    validate_mcp_url,
)

logger = get_logger(__name__)


class McpServerService:
    """Handles MCP server CRUD, validation, encryption, and status probing.

    Router is responsible for admin auth checks and RLS context setup.
    This service owns all business logic: duplicate checks, cross-field
    validation, encryption of secrets, status probing, and enable/disable.
    """

    def __init__(
        self,
        session: AsyncSession,
        workspace_mcp_server_repository: WorkspaceMcpServerRepository,
    ) -> None:
        self._session = session
        self._repo = workspace_mcp_server_repository

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    async def register_server(
        self,
        workspace_id: UUID,
        *,
        display_name: str,
        url: str | None = None,
        url_or_command: str | None = None,
        server_type: McpServerType = McpServerType.REMOTE,
        command_runner: Any | None = None,
        transport: McpTransport = McpTransport.SSE,
        command_args: list[str] | None = None,
        auth_type: McpAuthType = McpAuthType.NONE,
        auth_token: str | None = None,
        oauth_client_id: str | None = None,
        oauth_auth_url: str | None = None,
        oauth_token_url: str | None = None,
        oauth_scopes: str | None = None,
        headers: dict[str, str] | None = None,
        env_vars: dict[str, str] | None = None,
    ) -> WorkspaceMcpServer:
        """Register a new MCP server for a workspace.

        Validates display_name uniqueness, encrypts secrets, and creates
        the database record.

        Returns:
            The created WorkspaceMcpServer ORM model.

        Raises:
            ConflictError: If display_name already exists in the workspace.
        """
        existing = await self._repo.get_by_display_name(workspace_id, display_name)
        if existing is not None:
            raise ConflictError(
                f"An MCP server named {display_name!r} already exists in this workspace"
            )

        token_encrypted: str | None = None
        if auth_token:
            token_encrypted = encrypt_api_key(auth_token)

        headers_json: str | None = None
        if headers:
            headers_json = json.dumps(headers)

        env_vars_encrypted: str | None = None
        if env_vars:
            env_vars_encrypted = encrypt_kv(env_vars)

        effective_url = url_or_command or url or ""
        url_val = effective_url if effective_url else None

        server = WorkspaceMcpServer(
            workspace_id=workspace_id,
            display_name=display_name,
            url=url_val,
            url_or_command=effective_url,
            server_type=server_type,
            command_runner=command_runner,
            transport=transport,
            command_args=command_args,
            auth_type=auth_type,
            auth_token_encrypted=token_encrypted,
            oauth_client_id=oauth_client_id,
            oauth_auth_url=oauth_auth_url,
            oauth_token_url=oauth_token_url,
            oauth_scopes=oauth_scopes,
            headers_json=headers_json,
            env_vars_encrypted=env_vars_encrypted,
            is_enabled=True,
            last_status=McpStatus.ENABLED,
        )

        server = await self._repo.create(server)

        logger.info(
            "mcp_server_registered",
            workspace_id=str(workspace_id),
            server_id=str(server.id),
            auth_type=auth_type,
            server_type=server_type,
        )

        return server

    # ------------------------------------------------------------------
    # LIST
    # ------------------------------------------------------------------

    async def list_servers(
        self,
        workspace_id: UUID,
        *,
        server_type: McpServerType | None = None,
        status: McpStatus | None = None,
        search: str | None = None,
    ) -> list[WorkspaceMcpServer]:
        """List active (non-deleted) MCP servers with optional filters."""
        return list(
            await self._repo.get_filtered(
                workspace_id=workspace_id,
                server_type=server_type,
                status=status,
                search=search,
            )
        )

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------

    async def update_server(
        self,
        workspace_id: UUID,
        server_id: UUID,
        *,
        display_name: str | None = None,
        url_or_command: str | None = None,
        server_type: McpServerType | None = None,
        command_runner: Any | None = None,
        transport: McpTransport | None = None,
        command_args: list[str] | None = None,
        auth_type: McpAuthType | None = None,
        auth_token: str | None = None,
        oauth_client_id: str | None = None,
        oauth_auth_url: str | None = None,
        oauth_token_url: str | None = None,
        oauth_scopes: str | None = None,
        headers: dict[str, str] | None = None,
        env_vars: dict[str, str] | None = None,
        # Sentinel to distinguish "not provided" from "set to None"
        _has_server_type: bool = False,
        _has_transport: bool = False,
        _has_url_or_command: bool = False,
        _has_command_runner: bool = False,
        _has_command_args: bool = False,
        _has_auth_type: bool = False,
        _has_auth_token: bool = False,
        _has_oauth_client_id: bool = False,
        _has_oauth_auth_url: bool = False,
        _has_oauth_token_url: bool = False,
        _has_oauth_scopes: bool = False,
        _has_headers: bool = False,
        _has_env_vars: bool = False,
    ) -> WorkspaceMcpServer:
        """Partially update an MCP server.

        Only provided fields are updated. For secret fields, omitting
        preserves the existing value. Providing an empty string clears it.

        Raises:
            NotFoundError: Server not found.
            ConflictError: Display name conflict.
            ValidationError: Cross-field validation failure.
        """
        server = await self._repo.get_by_workspace_and_id(
            server_id=server_id, workspace_id=workspace_id
        )
        if not server:
            raise NotFoundError("MCP server not found")

        # Display name uniqueness
        if display_name is not None:
            if display_name != server.display_name:
                name_conflict = await self._repo.get_by_display_name(workspace_id, display_name)
                if name_conflict is not None:
                    raise ConflictError(
                        f"An MCP server named {display_name!r} already exists in this workspace"
                    )
            server.display_name = display_name

        # Effective values for cross-field validation
        effective_server_type = server_type if _has_server_type else server.server_type
        effective_url_or_command = (
            url_or_command if _has_url_or_command else (server.url_or_command or server.url)
        )

        # Cross-field validation: server_type / url_or_command
        if _has_server_type or _has_url_or_command:
            # Skip when both are present in request — already validated by Pydantic
            if not (_has_server_type and _has_url_or_command):
                if not effective_url_or_command:
                    raise ValidationError("url_or_command is required when changing server_type")
                try:
                    if effective_server_type == McpServerType.REMOTE:
                        validate_mcp_url(effective_url_or_command)
                    elif effective_server_type == McpServerType.COMMAND:
                        effective_runner = (
                            command_runner if _has_command_runner else server.command_runner
                        )
                        if effective_runner is not None:
                            validate_command_package(effective_url_or_command, effective_runner)
                except ValueError as exc:
                    raise ValidationError(str(exc)) from exc

        # Cross-field validation: server_type / transport compatibility
        effective_transport: McpTransport | None = transport if _has_transport else server.transport
        if effective_transport is not None:
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

        # Apply scalar fields
        if _has_server_type:
            server.server_type = server_type  # type: ignore[assignment]
        if _has_command_runner:
            server.command_runner = command_runner
        if _has_transport:
            server.transport = transport  # type: ignore[assignment]
        if _has_command_args:
            server.command_args = command_args or None  # type: ignore[assignment]

        # auth_type: when it changes, scrub fields that belong to the old type
        if _has_auth_type and auth_type is not None:
            if auth_type != server.auth_type:
                if auth_type != McpAuthType.BEARER:
                    server.auth_token_encrypted = None
                if auth_type != McpAuthType.OAUTH2:
                    server.oauth_client_id = None
                    server.oauth_auth_url = None
                    server.oauth_token_url = None
                    server.oauth_scopes = None
            server.auth_type = auth_type

        # OAuth plaintext fields: None = omit, empty string = clear
        if _has_oauth_client_id and oauth_client_id is not None:
            server.oauth_client_id = oauth_client_id.strip() or None
        if _has_oauth_auth_url and oauth_auth_url is not None:
            server.oauth_auth_url = oauth_auth_url.strip() or None
        if _has_oauth_token_url and oauth_token_url is not None:
            server.oauth_token_url = oauth_token_url.strip() or None
        if _has_oauth_scopes and oauth_scopes is not None:
            server.oauth_scopes = oauth_scopes.strip() or None

        # url_or_command: already validated above
        if _has_url_or_command and url_or_command is not None:
            server.url_or_command = url_or_command
            server.url = url_or_command

        # auth_token: None = omit, empty string = clear, non-empty = re-encrypt
        if _has_auth_token and auth_token is not None:
            if auth_token.strip():
                server.auth_token_encrypted = encrypt_api_key(auth_token)
            else:
                server.auth_token_encrypted = None

        if _has_headers and headers is not None:
            if headers:
                server.headers_json = json.dumps(headers)
                server.headers_encrypted = None  # Clear legacy encrypted column
            else:
                server.headers_json = None
                server.headers_encrypted = None

        if _has_env_vars and env_vars is not None:
            if env_vars:
                server.env_vars_encrypted = encrypt_kv(env_vars)
            else:
                server.env_vars_encrypted = None

        server = await self._repo.update(server)

        logger.info(
            "mcp_server_updated",
            workspace_id=str(workspace_id),
            server_id=str(server_id),
        )

        return server

    # ------------------------------------------------------------------
    # STATUS PROBE (legacy)
    # ------------------------------------------------------------------

    async def probe_status(
        self,
        workspace_id: UUID,
        server_id: UUID,
    ) -> tuple[WorkspaceMcpServer, McpStatus, datetime]:
        """Legacy connectivity probe with 5-second timeout.

        Returns:
            Tuple of (server, probe_status, checked_at).

        Raises:
            NotFoundError: Server not found.
        """
        server = await self._repo.get_by_workspace_and_id(
            server_id=server_id, workspace_id=workspace_id
        )
        if not server:
            raise NotFoundError("MCP server not found")

        headers: dict[str, str] = {}

        # Merge plaintext headers from headers_json
        if server.headers_json:
            try:
                parsed = json.loads(server.headers_json)
                if isinstance(parsed, dict):
                    headers.update(parsed)
            except (ValueError, TypeError):
                logger.warning("mcp_status_headers_json_parse_failed", server_id=str(server_id))

        # Authorization from encrypted token
        if server.auth_token_encrypted:
            try:
                token = decrypt_api_key(server.auth_token_encrypted)
                headers["Authorization"] = f"Bearer {token}"
            except Exception:
                logger.warning("mcp_status_token_decrypt_failed", server_id=str(server_id))

        probe_status = McpStatus.ENABLED
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
        await self._repo.update(server)

        logger.info(
            "mcp_server_status_probed",
            server_id=str(server_id),
            workspace_id=str(workspace_id),
            status=probe_status.value,
        )

        return server, probe_status, checked_at

    # ------------------------------------------------------------------
    # CONNECTION TEST (Phase 25)
    # ------------------------------------------------------------------

    async def test_connection(
        self,
        workspace_id: UUID,
        server_id: UUID,
    ) -> tuple[WorkspaceMcpServer, Any]:
        """On-demand connection test with 10-second timeout.

        Returns:
            Tuple of (server, test_result) where test_result has status,
            latency_ms, checked_at, error_detail.

        Raises:
            NotFoundError: Server not found.
        """
        from pilot_space.application.services.mcp.mcp_connection_tester import (
            TestMcpConnectionService,
        )

        server = await self._repo.get_by_workspace_and_id(
            server_id=server_id, workspace_id=workspace_id
        )
        if not server:
            raise NotFoundError("MCP server not found")

        result = await TestMcpConnectionService.test(server)

        server.last_status = result.status
        server.last_status_checked_at = result.checked_at
        await self._repo.update(server)

        logger.info(
            "mcp_server_connection_tested",
            server_id=str(server_id),
            workspace_id=str(workspace_id),
            status=result.status,
            latency_ms=result.latency_ms,
        )

        return server, result

    # ------------------------------------------------------------------
    # ENABLE / DISABLE
    # ------------------------------------------------------------------

    async def enable_server(self, workspace_id: UUID, server_id: UUID) -> None:
        """Enable a previously disabled MCP server.

        Raises:
            NotFoundError: Server not found.
        """
        server = await self._repo.get_by_workspace_and_id(
            server_id=server_id, workspace_id=workspace_id
        )
        if not server:
            raise NotFoundError("MCP server not found")

        await self._repo.set_enabled(server, enabled=True)
        logger.info("mcp_server_enabled", workspace_id=str(workspace_id), server_id=str(server_id))

    async def disable_server(self, workspace_id: UUID, server_id: UUID) -> None:
        """Disable an MCP server.

        Raises:
            NotFoundError: Server not found.
        """
        server = await self._repo.get_by_workspace_and_id(
            server_id=server_id, workspace_id=workspace_id
        )
        if not server:
            raise NotFoundError("MCP server not found")

        await self._repo.set_enabled(server, enabled=False)
        logger.info("mcp_server_disabled", workspace_id=str(workspace_id), server_id=str(server_id))

    # ------------------------------------------------------------------
    # SOFT DELETE
    # ------------------------------------------------------------------

    async def delete_server(self, workspace_id: UUID, server_id: UUID) -> None:
        """Soft-delete a registered MCP server.

        Raises:
            NotFoundError: Server not found.
        """
        server = await self._repo.get_by_workspace_and_id(
            server_id=server_id, workspace_id=workspace_id
        )
        if not server:
            raise NotFoundError("MCP server not found")

        await self._repo.soft_delete(server)
        logger.info(
            "mcp_server_deleted",
            workspace_id=str(workspace_id),
            server_id=str(server_id),
        )

    # ------------------------------------------------------------------
    # BULK IMPORT
    # ------------------------------------------------------------------

    async def import_servers(
        self,
        workspace_id: UUID,
        config_json: str,
    ) -> Any:
        """Bulk import MCP servers from a Claude/Cursor/VS Code JSON config.

        Returns:
            ImportMcpServersService result with imported, skipped, errors.
        """
        from pilot_space.application.services.mcp.import_mcp_servers_service import (
            ImportMcpServersService,
        )

        parsed, parse_errors = ImportMcpServersService.parse_config_json(config_json)
        result = await ImportMcpServersService.import_servers(
            workspace_id=workspace_id,
            parsed=parsed,
            repo=self._repo,
            parse_errors=parse_errors,
        )

        logger.info(
            "mcp_servers_bulk_imported",
            workspace_id=str(workspace_id),
            imported=len(result.imported),
            skipped=len(result.skipped),
            errors=len(result.errors),
        )

        return result
