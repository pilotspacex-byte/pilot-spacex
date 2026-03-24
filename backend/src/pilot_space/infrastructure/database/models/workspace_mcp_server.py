"""WorkspaceMcpServer SQLAlchemy model (Phase 14 — MCP-01, MCP-02, MCP-06).

Extended in Phase 25 to support command server types, 5-state status enum,
encrypted headers/env-vars, and enable/disable toggling.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import WorkspaceScopedModel

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.workspace import Workspace


class McpAuthType(StrEnum):
    """Authentication type for remote MCP server connections."""

    NONE = "none"
    BEARER = "bearer"
    OAUTH2 = "oauth2"


class McpServerType(StrEnum):
    """Server type — remote HTTP endpoint or locally-launched process."""

    REMOTE = "remote"
    COMMAND = "command"


class McpCommandRunner(StrEnum):
    """Command runner for COMMAND-type servers."""

    NPX = "npx"
    UVX = "uvx"


class McpTransport(StrEnum):
    """Transport protocol for MCP server communication."""

    SSE = "sse"
    STDIO = "stdio"
    STREAMABLE_HTTP = "streamable_http"


class McpStatus(StrEnum):
    """5-state connectivity/admin status for an MCP server.

    Lifecycle:
        ENABLED: polling healthy; admin has not disabled.
        DISABLED: admin explicitly disabled; poller skips this server.
        UNHEALTHY: reachable but returning error responses.
        UNREACHABLE: connection timeout or network failure.
        CONFIG_ERROR: configuration invalid (e.g. bad URL, missing required field).
    """

    ENABLED = "enabled"
    DISABLED = "disabled"
    UNHEALTHY = "unhealthy"
    UNREACHABLE = "unreachable"
    CONFIG_ERROR = "config_error"


class WorkspaceMcpServer(WorkspaceScopedModel):
    """Workspace-registered MCP server (remote or command).

    Stores connection details and encrypted credentials for Model Context
    Protocol servers. Supports Bearer token and OAuth 2.0 authentication,
    plus encrypted environment variable blobs for command-type servers.

    Headers are stored as **plaintext** in ``headers_json`` and returned
    in full in API responses (they are not sensitive). The legacy
    ``headers_encrypted`` column is retained for migration from older rows
    but new writes always go to ``headers_json``.

    Attributes:
        workspace_id: Reference to parent workspace.
        display_name: Human-readable label shown in UI.
        url: Remote MCP server endpoint (backward-compat alias for url_or_command; nullable for command-type servers).
        auth_type: Authentication mechanism (none, bearer, or oauth2).
        auth_token_encrypted: Fernet-encrypted Bearer token or OAuth access token.
        oauth_client_id: OAuth 2.0 client ID (auth_type=oauth2 only).
        oauth_auth_url: OAuth 2.0 authorization endpoint URL.
        oauth_token_url: OAuth 2.0 token exchange endpoint URL.
        oauth_scopes: Space-separated OAuth 2.0 scope list.
        last_status: 5-state McpStatus enum (previously String(16)).
        last_status_checked_at: Timestamp of last connectivity probe.
        server_type: Remote or command.
        transport: SSE, stdio, or streamable_http.
        url_or_command: Primary URL (remote) or package/args (command).
        command_runner: npx or uvx — required for command-type servers.
        command_args: Extra CLI arguments for command launch.
        headers_json: Plaintext JSON blob of HTTP headers (returned in API responses).
        headers_encrypted: Legacy Fernet-encrypted headers (read-only migration fallback).
        env_vars_encrypted: Fernet-encrypted JSON blob of env var key-value pairs.
        is_enabled: Admin toggle; disabled servers are excluded from polling.
    """

    __tablename__ = "workspace_mcp_servers"  # type: ignore[assignment]
    __table_args__ = (
        # Partial unique index: active rows within a workspace must have distinct
        # display names.  Soft-deleted rows (is_deleted=True) are excluded so a
        # name can be re-used after deletion.
        Index(
            "uq_mcp_servers_workspace_display_name_active",
            "workspace_id",
            "display_name",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
        {"schema": None},
    )

    display_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        doc="Human-readable server label shown in UI",
    )
    url: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
        doc="Remote MCP server endpoint URL — legacy compat alias for url_or_command",
    )
    auth_type: Mapped[McpAuthType] = mapped_column(
        Enum(
            McpAuthType,
            name="mcp_auth_type",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=McpAuthType.NONE,
        doc="Authentication type: none, bearer token, or OAuth 2.0",
    )

    # Encrypted credential storage — Fernet symmetric encryption
    auth_token_encrypted: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
        doc="Fernet-encrypted Bearer token or OAuth access token (None = no token yet)",
    )

    # OAuth 2.0 metadata — required when auth_type=OAUTH2
    oauth_client_id: Mapped[str | None] = mapped_column(
        String(256),
        nullable=True,
        doc="OAuth 2.0 client ID",
    )
    oauth_auth_url: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        doc="OAuth 2.0 authorization endpoint",
    )
    oauth_token_url: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        doc="OAuth 2.0 token exchange endpoint",
    )
    oauth_scopes: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        doc="Space-separated OAuth 2.0 scope list",
    )

    # Cached connectivity status (Phase 25: replaces String(16) with McpStatus enum)
    last_status: Mapped[McpStatus | None] = mapped_column(
        Enum(
            McpStatus,
            name="mcp_status",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=True,
        doc="5-state connectivity/admin status enum",
    )
    last_status_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of last connectivity probe",
    )

    # --- Phase 25 new fields ---

    server_type: Mapped[McpServerType] = mapped_column(
        Enum(
            McpServerType,
            name="mcp_server_type",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=McpServerType.REMOTE,
        doc="Server type: remote HTTP endpoint or command",
    )
    transport: Mapped[McpTransport] = mapped_column(
        Enum(
            McpTransport,
            name="mcp_transport",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=McpTransport.SSE,
        doc="Transport protocol: sse, stdio, or streamable_http",
    )
    url_or_command: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
        doc="Primary URL (remote) or package/args (command) — authoritative field",
    )
    command_runner: Mapped[McpCommandRunner | None] = mapped_column(
        Enum(
            McpCommandRunner,
            name="mcp_command_runner",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=True,
        doc="Command runner for COMMAND-type servers: npx or uvx",
    )
    command_args: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        doc="Extra CLI arguments appended to command launch",
    )
    headers_encrypted: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Fernet-encrypted JSON blob of HTTP header key-value pairs (legacy — prefer headers_json)",
    )
    headers_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Plaintext JSON blob of HTTP header key-value pairs (not sensitive — visible in API response)",
    )
    env_vars_encrypted: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Fernet-encrypted JSON blob of environment variable key-value pairs",
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        doc="Admin toggle: disabled servers are excluded from polling and MCP routing",
    )

    # Relationships
    workspace: Mapped[Workspace] = relationship(
        "Workspace",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<WorkspaceMcpServer(id={self.id}, "
            f"workspace_id={self.workspace_id}, "
            f"display_name={self.display_name!r}, "
            f"server_type={self.server_type!r})>"
        )


__all__ = [
    "McpAuthType",
    "McpCommandRunner",
    "McpServerType",
    "McpStatus",
    "McpTransport",
    "WorkspaceMcpServer",
]
