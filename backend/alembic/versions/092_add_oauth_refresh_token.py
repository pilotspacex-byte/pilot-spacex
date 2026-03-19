"""Add refresh_token_encrypted and token_expires_at to workspace_mcp_servers.

Revision ID: 092_add_oauth_refresh_token
Revises: 091_add_mcp_transport_type
Create Date: 2026-03-20

Phase 32 — OAuth Refresh Flow (MCPO-01):

1. Adds refresh_token_encrypted String(1024) nullable — Fernet-encrypted OAuth refresh token.
2. Adds token_expires_at DateTime(timezone=True) nullable — UTC expiry of the access token.

Both columns are nullable so existing rows are unaffected.

Downgrade removes both columns in reverse order.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "092_add_oauth_refresh_token"
down_revision: str = "091_add_mcp_transport_type"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add refresh_token_encrypted and token_expires_at columns."""
    op.add_column(
        "workspace_mcp_servers",
        sa.Column(
            "refresh_token_encrypted",
            sa.String(1024),
            nullable=True,
        ),
    )
    op.add_column(
        "workspace_mcp_servers",
        sa.Column(
            "token_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Drop token_expires_at and refresh_token_encrypted columns."""
    op.drop_column("workspace_mcp_servers", "token_expires_at")
    op.drop_column("workspace_mcp_servers", "refresh_token_encrypted")
