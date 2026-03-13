"""WorkspaceMcpServer SQLAlchemy model (Phase 14 — MCP-01, MCP-02, MCP-06)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import WorkspaceScopedModel

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.workspace import Workspace


class McpAuthType(StrEnum):
    """Authentication type for remote MCP server connections."""

    BEARER = "bearer"
    OAUTH2 = "oauth2"


class WorkspaceMcpServer(WorkspaceScopedModel):
    """Workspace-registered remote MCP server.

    Stores connection details and encrypted credentials for a remote
    Model Context Protocol server. Supports both Bearer token and
    OAuth 2.0 authentication flows.

    Attributes:
        workspace_id: Reference to parent workspace.
        display_name: Human-readable label shown in UI.
        url: Remote MCP server endpoint (SSE or HTTP transport).
        auth_type: Authentication mechanism (bearer or oauth2).
        auth_token_encrypted: Fernet-encrypted Bearer token or OAuth access token.
        oauth_client_id: OAuth 2.0 client ID (auth_type=oauth2 only).
        oauth_auth_url: OAuth 2.0 authorization endpoint URL.
        oauth_token_url: OAuth 2.0 token exchange endpoint URL.
        oauth_scopes: Space-separated OAuth 2.0 scope list.
        last_status: Cached connectivity status ('connected', 'failed', 'unknown').
        last_status_checked_at: Timestamp of last connectivity probe.
    """

    __tablename__ = "workspace_mcp_servers"  # type: ignore[assignment]
    __table_args__ = ({"schema": None},)

    display_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        doc="Human-readable server label shown in UI",
    )
    url: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        doc="Remote MCP server endpoint URL (SSE or HTTP transport)",
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


__all__ = ["McpAuthType", "WorkspaceMcpServer"]
