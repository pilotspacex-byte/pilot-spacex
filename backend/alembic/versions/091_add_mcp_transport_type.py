"""Add mcp_transport_type enum and transport_type column to workspace_mcp_servers.

Revision ID: 091_add_mcp_transport_type
Revises: 090_add_tags_and_usage_to_skills
Create Date: 2026-03-20

Phase 31 — MCP Infrastructure Hardening (MCPI-02):

1. Creates mcp_transport_type PostgreSQL enum: ('sse', 'http').
2. Adds transport_type column to workspace_mcp_servers with server_default='sse'.

Downgrade removes the column and drops the enum type.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import text

from alembic import op

revision: str = "091_add_mcp_transport_type"
down_revision: str = "090_add_tags_and_usage_to_skills"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create mcp_transport_type enum and add transport_type column."""
    op.execute(text("CREATE TYPE mcp_transport_type AS ENUM ('sse', 'http')"))
    op.add_column(
        "workspace_mcp_servers",
        sa.Column(
            "transport_type",
            sa.Enum("sse", "http", name="mcp_transport_type", create_type=False),
            nullable=False,
            server_default=text("'sse'::mcp_transport_type"),
        ),
    )


def downgrade() -> None:
    """Drop transport_type column and mcp_transport_type enum."""
    op.drop_column("workspace_mcp_servers", "transport_type")
    op.execute(text("DROP TYPE IF EXISTS mcp_transport_type"))
