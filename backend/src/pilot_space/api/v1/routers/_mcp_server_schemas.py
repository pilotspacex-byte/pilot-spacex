"""Pydantic schemas for workspace MCP server endpoints.

Extracted from workspace_mcp_servers.py to stay within the 700-line limit.

Extended in Phase 25 to support:
- McpServerType / McpTransport / McpStatus type enums
- WorkspaceMcpServerUpdate (partial PATCH)
- Extended WorkspaceMcpServerCreate with new fields
- WorkspaceMcpServerResponse with boolean secret presence flags
- Command injection validation for command url_or_command values
- Bulk import request/response schemas
- Connection test response schema

SSRF and command-injection validation is delegated to
``pilot_space.security.mcp_validation`` so that the import service layer can
apply identical rules without importing from the API layer.
"""

from __future__ import annotations

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from pilot_space.infrastructure.database.models.workspace_mcp_server import (
    McpAuthType,
    McpCommandRunner,
    McpServerType,
    McpStatus,
    McpTransport,
)
from pilot_space.security.mcp_validation import (
    SHELL_METACHAR_RE as _SHELL_METACHAR_RE,
    validate_command_package as _validate_command_package,
    validate_mcp_url as _validate_mcp_url,
)

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

WORKSPACE_SLUG_RE = re.compile(r"^[a-z0-9-]+$")

# Relaxed variant for command_args: allows $ for env var references ($VAR_NAME syntax)
# Still blocks shell chaining/redirection/subshell metacharacters
_SHELL_METACHAR_ARGS_RE = re.compile(r"[;&|`(){}<>]")


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class WorkspaceMcpServerCreate(BaseModel):
    """Request body for registering a new MCP server.

    Supports all server types (remote, command) with appropriate
    validation rules for each type.
    """

    display_name: str = Field(..., max_length=128, description="Human-readable label")

    # Legacy field — kept for backward compat; url_or_command takes precedence
    url: str | None = Field(
        default=None,
        max_length=512,
        description="Legacy remote URL field (use url_or_command instead)",
    )

    # Phase 25 primary fields
    server_type: McpServerType = Field(
        default=McpServerType.REMOTE,
        description="Server type: remote or command",
    )
    command_runner: McpCommandRunner | None = Field(
        default=None,
        description="Command runner: npx or uvx. Required when server_type=command.",
    )
    transport: McpTransport = Field(
        default=McpTransport.SSE,
        description="Transport protocol: sse, stdio, or streamable_http",
    )
    url_or_command: str | None = Field(
        default=None,
        max_length=1024,
        description="HTTPS URL for remote, or package/args for command",
    )
    command_args: str | None = Field(
        default=None,
        max_length=512,
        description="Extra CLI arguments for command launch (command only)",
    )
    headers: dict[str, str] | None = Field(
        default=None,
        description="HTTP headers to inject (stored as plaintext; returned in API responses)",
    )
    env_vars: dict[str, str] | None = Field(
        default=None,
        description="Environment variables for command launch (will be encrypted at rest)",
    )

    # Auth fields
    auth_type: McpAuthType = Field(default=McpAuthType.NONE)
    auth_token: str | None = Field(
        default=None, max_length=512, description="Bearer token (will be encrypted at rest)"
    )
    oauth_client_id: str | None = Field(default=None, max_length=256)
    oauth_auth_url: str | None = Field(default=None, max_length=512)
    oauth_token_url: str | None = Field(default=None, max_length=512)
    oauth_scopes: str | None = Field(default=None, max_length=512)

    @model_validator(mode="after")
    def validate_server_type_transport(self) -> WorkspaceMcpServerCreate:
        """Reject invalid server_type / transport combinations.

        Remote servers must use SSE or Streamable HTTP.
        Command-type servers must use stdio.
        """
        if self.server_type == McpServerType.REMOTE:
            if self.transport not in (McpTransport.SSE, McpTransport.STREAMABLE_HTTP):
                raise ValueError(
                    f"Remote servers only support 'sse' or 'streamable_http' transport, "
                    f"got '{self.transport.value}'"
                )
        elif self.server_type == McpServerType.COMMAND:
            if self.transport != McpTransport.STDIO:
                raise ValueError(
                    f"{self.server_type.value} servers only support 'stdio' transport, "
                    f"got '{self.transport.value}'"
                )
        return self

    @model_validator(mode="after")
    def validate_command_runner_required(self) -> WorkspaceMcpServerCreate:
        """command_runner is required when server_type=command; must not be set for remote."""
        if self.server_type == McpServerType.COMMAND and self.command_runner is None:
            raise ValueError("command_runner ('npx' or 'uvx') is required for command-type servers")
        if self.server_type == McpServerType.REMOTE and self.command_runner is not None:
            raise ValueError("command_runner must not be set for remote servers")
        return self

    @model_validator(mode="after")
    def validate_url_or_command(self) -> WorkspaceMcpServerCreate:
        """Ensure url_or_command is set, defaulting from url for backward compat.

        Also validates URL/command format based on server_type.
        """
        # Resolve effective url_or_command
        effective = self.url_or_command or self.url
        if not effective:
            raise ValueError("url_or_command is required")

        if self.server_type == McpServerType.REMOTE:
            _validate_mcp_url(effective)
        elif self.server_type == McpServerType.COMMAND:
            if self.command_runner is not None:
                _validate_command_package(effective, self.command_runner)

        # Always populate url_or_command so downstream code has one source of truth
        self.url_or_command = effective
        # Keep url in sync for backward compat with AI agent hot-loader
        self.url = effective

        return self

    @field_validator("oauth_auth_url", "oauth_token_url")
    @classmethod
    def validate_oauth_urls(cls, v: str | None) -> str | None:
        """Validate OAuth URLs against SSRF blocklist."""
        if v is None:
            return v
        return _validate_mcp_url(v)

    @field_validator("command_args")
    @classmethod
    def validate_command_args(cls, v: str | None) -> str | None:
        """Validate command_args for shell metacharacters.

        $ is permitted to allow $VAR_NAME env var references (e.g. --api-key $API_KEY).
        Shell chaining operators (;, &, |) and subshell/redirect chars remain blocked.
        """
        if v is not None and _SHELL_METACHAR_ARGS_RE.search(v):
            raise ValueError("command_args contains disallowed shell metacharacters")
        return v

    @field_validator("headers")
    @classmethod
    def validate_headers(cls, v: dict[str, str] | None) -> dict[str, str] | None:
        """Validate header keys are valid HTTP header name format."""
        if v is None:
            return v
        if len(v) > 10:
            raise ValueError("Maximum 10 HTTP headers allowed")
        header_key_re = re.compile(r"^[a-zA-Z0-9-]+$")
        for key in v:
            if not header_key_re.match(key):
                raise ValueError(
                    f"Invalid HTTP header name: {key!r} "
                    "(must contain only alphanumeric characters and hyphens)"
                )
        return v

    @field_validator("env_vars")
    @classmethod
    def validate_env_vars(cls, v: dict[str, str] | None) -> dict[str, str] | None:
        """Validate env var keys follow POSIX naming convention."""
        if v is None:
            return v
        if len(v) > 20:
            raise ValueError("Maximum 20 environment variables allowed")
        env_key_re = re.compile(r"^[A-Z_][A-Z0-9_]*$")
        for key in v:
            if not env_key_re.match(key):
                raise ValueError(f"Invalid env var name: {key!r} (must match [A-Z_][A-Z0-9_]*)")
        return v


class WorkspaceMcpServerUpdate(BaseModel):
    """Request body for partial PATCH update of an MCP server.

    All fields are optional. Fields not included in the request are left
    unchanged. For secret fields (auth_token, env_vars), omitting the field
    preserves the existing encrypted value. Headers are stored as plaintext
    and returned in API responses.
    """

    display_name: str | None = Field(default=None, max_length=128)
    server_type: McpServerType | None = Field(default=None)
    command_runner: McpCommandRunner | None = Field(default=None)
    transport: McpTransport | None = Field(default=None)
    url_or_command: str | None = Field(default=None, max_length=1024)
    command_args: str | None = Field(default=None, max_length=512)
    auth_type: McpAuthType | None = Field(default=None)

    # Secret fields: only update if non-None and non-empty
    auth_token: str | None = Field(default=None, max_length=512)
    headers: dict[str, str] | None = Field(default=None)
    env_vars: dict[str, str] | None = Field(default=None)

    # OAuth
    oauth_client_id: str | None = Field(default=None, max_length=256)
    oauth_auth_url: str | None = Field(default=None, max_length=512)
    oauth_token_url: str | None = Field(default=None, max_length=512)
    oauth_scopes: str | None = Field(default=None, max_length=512)

    @model_validator(mode="after")
    def validate_server_type_transport(self) -> WorkspaceMcpServerUpdate:
        """Reject invalid server_type / transport combinations when both are in the PATCH."""
        if self.server_type is not None and self.transport is not None:
            if self.server_type == McpServerType.REMOTE:
                if self.transport not in (McpTransport.SSE, McpTransport.STREAMABLE_HTTP):
                    raise ValueError(
                        f"Remote servers only support 'sse' or 'streamable_http' transport, "
                        f"got '{self.transport.value}'"
                    )
            elif self.server_type == McpServerType.COMMAND:
                if self.transport != McpTransport.STDIO:
                    raise ValueError(
                        f"{self.server_type.value} servers only support 'stdio' transport, "
                        f"got '{self.transport.value}'"
                    )
        return self

    @model_validator(mode="after")
    def validate_command_runner_required(self) -> WorkspaceMcpServerUpdate:
        """When server_type is provided in PATCH, validate command_runner consistency."""
        if self.server_type == McpServerType.COMMAND and self.command_runner is None:
            # Only enforce if server_type is being changed to command without runner
            # The route handler must check the stored value if runner not in request
            pass
        if self.server_type == McpServerType.REMOTE and self.command_runner is not None:
            raise ValueError("command_runner must not be set for remote servers")
        return self

    @model_validator(mode="after")
    def validate_url_or_command(self) -> WorkspaceMcpServerUpdate:
        """Validate url_or_command when it is present in the PATCH body.

        Rules applied when url_or_command is provided:
        - Must not be an empty string.
        - If server_type is also provided in this request, validate the value
          against the new type (SSRF check for REMOTE, injection check for COMMAND).
        - If server_type is NOT provided, we cannot know the stored type here;
          the route handler performs cross-field validation using the stored value.
        """
        if self.url_or_command is not None:
            if not self.url_or_command.strip():
                raise ValueError("url_or_command must not be empty")

            if self.server_type is not None:
                # Both fields present in the PATCH — validate the new value against
                # the new type immediately.
                if self.server_type == McpServerType.REMOTE:
                    _validate_mcp_url(self.url_or_command)
                elif self.server_type == McpServerType.COMMAND:
                    # Validate shell metacharacters even without command_runner
                    if not self.url_or_command.strip():
                        raise ValueError("Command must not be empty")
                    if _SHELL_METACHAR_RE.search(self.url_or_command):
                        raise ValueError("Command contains disallowed shell metacharacters")

        return self

    @field_validator("command_args")
    @classmethod
    def validate_command_args(cls, v: str | None) -> str | None:
        """Validate command_args for shell metacharacters.

        $ is permitted to allow $VAR_NAME env var references (e.g. --api-key $API_KEY).
        Shell chaining operators (;, &, |) and subshell/redirect chars remain blocked.
        """
        if v is not None and _SHELL_METACHAR_ARGS_RE.search(v):
            raise ValueError("command_args contains disallowed shell metacharacters")
        return v

    @field_validator("headers")
    @classmethod
    def validate_headers(cls, v: dict[str, str] | None) -> dict[str, str] | None:
        """Validate header keys are valid HTTP header name format."""
        if v is None:
            return v
        if len(v) > 10:
            raise ValueError("Maximum 10 HTTP headers allowed")
        header_key_re = re.compile(r"^[a-zA-Z0-9-]+$")
        for key in v:
            if not header_key_re.match(key):
                raise ValueError(f"Invalid HTTP header name: {key!r}")
        return v

    @field_validator("env_vars")
    @classmethod
    def validate_env_vars(cls, v: dict[str, str] | None) -> dict[str, str] | None:
        """Validate env var keys follow POSIX naming convention."""
        if v is None:
            return v
        if len(v) > 20:
            raise ValueError("Maximum 20 environment variables allowed")
        env_key_re = re.compile(r"^[A-Z_][A-Z0-9_]*$")
        for key in v:
            if not env_key_re.match(key):
                raise ValueError(f"Invalid env var name: {key!r}")
        return v


class WorkspaceMcpServerResponse(BaseModel):
    """Response for a single MCP server.

    Secrets (auth_token_encrypted, env_vars_encrypted) are NEVER returned.
    Headers are stored as plaintext and returned in full.
    Env var keys (without values) are returned for edit form display.
    """

    id: UUID
    workspace_id: UUID
    display_name: str

    # Phase 25 fields
    server_type: McpServerType
    transport: McpTransport
    url_or_command: str | None
    command_runner: McpCommandRunner | None = None
    command_args: str | None = None
    is_enabled: bool

    # Legacy field for backward compat
    url: str | None = None

    auth_type: McpAuthType

    # Boolean presence flags — raw secrets are NEVER returned
    has_auth_secret: bool = False
    has_headers: bool = False
    has_headers_encrypted: bool = False
    has_env_secret: bool = False

    # Headers are NOT secret — returned in full for editing
    headers: dict[str, str] | None = None

    # Env var keys only (values are secret and never returned)
    env_var_keys: list[str] | None = None

    # OAuth metadata (read-only)
    oauth_client_id: str | None = None
    oauth_auth_url: str | None = None
    oauth_scopes: str | None = None

    last_status: McpStatus | None = None
    last_status_checked_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_model(cls, server: object) -> WorkspaceMcpServerResponse:
        """Build response from ORM model, populating secret flags and visible data.

        Headers are returned in full (plaintext). Env var keys are extracted
        from the encrypted blob (values are never returned).
        """
        from pilot_space.infrastructure.database.models.workspace_mcp_server import (
            WorkspaceMcpServer as OrmModel,
        )

        assert isinstance(server, OrmModel)

        # Determine url_or_command — fallback to url for legacy rows
        uoc = server.url_or_command or server.url

        # Resolve headers — prefer headers_json, fallback to decrypting headers_encrypted
        headers_data: dict[str, str] | None = None
        if server.headers_json:
            import json

            try:
                headers_data = json.loads(server.headers_json)
            except (json.JSONDecodeError, TypeError):
                headers_data = None
        elif server.headers_encrypted:
            try:
                from pilot_space.infrastructure.encryption_kv import decrypt_kv

                headers_data = decrypt_kv(server.headers_encrypted)
            except Exception:
                headers_data = None

        # Extract env var keys (never values)
        env_keys: list[str] | None = None
        if server.env_vars_encrypted:
            try:
                from pilot_space.infrastructure.encryption_kv import decrypt_kv

                env_data = decrypt_kv(server.env_vars_encrypted)
                env_keys = sorted(env_data.keys())
            except Exception:
                env_keys = None

        return cls(
            id=server.id,
            workspace_id=server.workspace_id,
            display_name=server.display_name,
            server_type=server.server_type,
            transport=server.transport,
            url_or_command=uoc,
            command_runner=server.command_runner,
            command_args=server.command_args,
            is_enabled=server.is_enabled,
            url=server.url,
            auth_type=server.auth_type,
            has_auth_secret=bool(server.auth_token_encrypted),
            has_headers=bool(server.headers_encrypted or server.headers_json),
            has_headers_encrypted=bool(server.headers_encrypted),
            has_env_secret=bool(server.env_vars_encrypted),
            headers=headers_data,
            env_var_keys=env_keys,
            oauth_client_id=server.oauth_client_id,
            oauth_auth_url=server.oauth_auth_url,
            oauth_scopes=server.oauth_scopes,
            last_status=server.last_status,
            last_status_checked_at=server.last_status_checked_at,
            created_at=server.created_at,
        )

    @classmethod
    def model_validate(  # type: ignore[override]
        cls, obj: object, *args: object, **kwargs: object
    ) -> WorkspaceMcpServerResponse:
        """Override model_validate to use from_orm_model when obj is an ORM instance.

        Falls back to Pydantic's default model_validate for dict inputs.
        """
        from pilot_space.infrastructure.database.models.workspace_mcp_server import (
            WorkspaceMcpServer as OrmModel,
        )

        if isinstance(obj, OrmModel):
            return cls.from_orm_model(obj)
        return super().model_validate(obj, *args, **kwargs)


class WorkspaceMcpServerListResponse(BaseModel):
    """List response for workspace MCP servers."""

    items: list[WorkspaceMcpServerResponse]
    total: int


class McpServerStatusResponse(BaseModel):
    """Status probe result for an MCP server (legacy endpoint)."""

    server_id: UUID
    status: McpStatus
    checked_at: datetime


class McpServerTestResponse(BaseModel):
    """Connection test result for an MCP server (Phase 25 test endpoint)."""

    server_id: UUID
    status: McpStatus
    latency_ms: int | None = None
    checked_at: datetime
    error_detail: str | None = None


class McpOAuthUrlResponse(BaseModel):
    """OAuth authorization URL for MCP server OAuth flow."""

    auth_url: str
    state: str


# ---------------------------------------------------------------------------
# Bulk import schemas
# ---------------------------------------------------------------------------


class ImportMcpServersRequest(BaseModel):
    """Request body for bulk MCP server import."""

    config_json: str = Field(
        ..., description="Raw JSON config string in Claude/Cursor/VS Code format"
    )


class ImportedServerEntry(BaseModel):
    """A successfully imported server entry in the import response."""

    name: str
    id: UUID


class SkippedServerEntry(BaseModel):
    """A skipped server entry in the import response."""

    name: str
    reason: str


class ErrorServerEntry(BaseModel):
    """An errored server entry in the import response."""

    name: str
    reason: str


class ImportMcpServersResponse(BaseModel):
    """Response for bulk MCP server import."""

    imported: list[ImportedServerEntry]
    skipped: list[SkippedServerEntry]
    errors: list[ErrorServerEntry]
