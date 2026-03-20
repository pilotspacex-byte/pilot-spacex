"""WorkspaceMcpServer SQLAlchemy model (Phase 14 — MCP-01, MCP-02, MCP-06)."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import WorkspaceScopedModel

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.workspace import Workspace


class McpAuthType(StrEnum):
    """Authentication type for remote MCP server connections."""

    BEARER = "bearer"
    OAUTH2 = "oauth2"


class McpTransportType(StrEnum):
    """Transport protocol for MCP server connections (remote or local stdio)."""

    SSE = "sse"
    HTTP = "http"
    STDIO = "stdio"


class McpApprovalMode(StrEnum):
    """Tool-call approval mode for a remote MCP server.

    Attributes:
        AUTO_APPROVE: All tool calls from this server are executed automatically.
        REQUIRE_APPROVAL: Every tool call must be approved by a workspace admin.
    """

    AUTO_APPROVE = "auto_approve"
    REQUIRE_APPROVAL = "require_approval"


class WorkspaceMcpServer(WorkspaceScopedModel):
    """Workspace-registered MCP server (remote SSE/HTTP or local stdio).

    Stores connection details and encrypted credentials for a Model Context
    Protocol server. Supports Bearer token and OAuth 2.0 authentication for
    remote servers, and stdio command execution for local servers.

    Attributes:
        workspace_id: Reference to parent workspace.
        display_name: Human-readable label shown in UI.
        url: Remote MCP server endpoint (SSE or HTTP transport); None for stdio.
        auth_type: Authentication mechanism (bearer or oauth2).
        auth_token_encrypted: Fernet-encrypted Bearer token or OAuth access token.
        oauth_client_id: OAuth 2.0 client ID (auth_type=oauth2 only).
        oauth_auth_url: OAuth 2.0 authorization endpoint URL.
        oauth_token_url: OAuth 2.0 token exchange endpoint URL.
        oauth_scopes: Space-separated OAuth 2.0 scope list.
        refresh_token_encrypted: Fernet-encrypted OAuth refresh token (None = not stored).
        token_expires_at: UTC timestamp when the access token expires (None = unknown).
        last_status: Cached connectivity status ('connected', 'failed', 'unknown').
        last_status_checked_at: Timestamp of last connectivity probe.
        stdio_command: Executable command for stdio transport (e.g., 'npx', 'node').
        stdio_args: JSON-encoded arguments list for stdio command.
    """

    __tablename__ = "workspace_mcp_servers"  # type: ignore[assignment]
    __table_args__ = ({"schema": None},)

    display_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        doc="Human-readable server label shown in UI",
    )
    url: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        doc="Remote MCP server endpoint URL (SSE or HTTP transport); None for stdio servers",
    )
    stdio_command: Mapped[str | None] = mapped_column(
        String(256),
        nullable=True,
        doc="Executable command for stdio transport (e.g., 'npx', 'node')",
    )
    stdio_args: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
        doc="JSON-encoded arguments list for stdio command",
    )
    auth_type: Mapped[McpAuthType] = mapped_column(
        Enum(
            McpAuthType,
            name="mcp_auth_type",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=McpAuthType.BEARER,
        doc="Authentication type: bearer token or OAuth 2.0",
    )
    transport_type: Mapped[McpTransportType] = mapped_column(
        Enum(
            McpTransportType,
            name="mcp_transport_type",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=McpTransportType.SSE,
        server_default="sse",
        doc="MCP transport protocol: 'sse', 'http', or 'stdio'",
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
    refresh_token_encrypted: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
        doc="Fernet-encrypted OAuth refresh token (None = no refresh token stored)",
    )
    token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="UTC timestamp when the access token expires (None = unknown or no expiry)",
    )

    # Cached connectivity status
    last_status: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
        doc="Last known connectivity status: 'connected', 'failed', or 'unknown'",
    )
    last_status_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of last connectivity probe",
    )

    # Approval mode — controls whether tool calls auto-execute or need admin approval
    approval_mode: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=McpApprovalMode.AUTO_APPROVE,
        doc="Tool-call approval mode: 'auto_approve' or 'require_approval'",
    )

    # Catalog tracking — MCPC-02, MCPC-03
    catalog_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mcp_catalog_entries.id", ondelete="SET NULL"),
        nullable=True,
        doc="Catalog entry this server was installed from (nullable)",
    )
    installed_catalog_version: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        doc="Catalog version string at install time for update drift detection",
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
            f"display_name={self.display_name!r})>"
        )


__all__ = ["McpApprovalMode", "McpAuthType", "McpTransportType", "WorkspaceMcpServer"]
