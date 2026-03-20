"""Add stdio transport support for local MCP servers.

Revision ID: 097_add_stdio_mcp_support
Revises: 096_add_catalog_fk
Create Date: 2026-03-20

Phase 35 — MCPI-06 (stdio):
Adds stdio transport type and associated columns to workspace_mcp_servers so
local MCP servers (e.g., sequential-thinking via npx) can be registered.

Changes:
- Add 'stdio' value to mcp_transport_type enum.
- Add stdio_command VARCHAR(256) NULLABLE — executable for stdio transport.
- Add stdio_args VARCHAR(1024) NULLABLE — JSON-encoded args list.
- ALTER url to allow NULL — stdio servers don't have a URL.
- Seed 'Sequential Thinking' catalog entry.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import text

from alembic import op

revision: str = "097_add_stdio_mcp_support"
down_revision: str = "096_add_catalog_fk"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add stdio transport support columns and seed sequential-thinking catalog entry."""
    # Add 'stdio' to the existing mcp_transport_type enum
    op.execute(text("ALTER TYPE mcp_transport_type ADD VALUE IF NOT EXISTS 'stdio'"))

    # Add stdio_command column
    op.add_column(
        "workspace_mcp_servers",
        sa.Column(
            "stdio_command",
            sa.String(256),
            nullable=True,
        ),
    )

    # Add stdio_args column
    op.add_column(
        "workspace_mcp_servers",
        sa.Column(
            "stdio_args",
            sa.String(1024),
            nullable=True,
        ),
    )

    # Make url nullable (stdio servers don't have URLs)
    op.alter_column("workspace_mcp_servers", "url", nullable=True)

    # Seed sequential-thinking catalog entry
    # For stdio catalog entries, url_template stores command|arg1|arg2|... (pipe-separated)
    op.execute(
        text(
            """
            INSERT INTO mcp_catalog_entries (
                id, name, description, url_template, transport_type, auth_type,
                catalog_version, is_official, sort_order, setup_instructions,
                created_at, updated_at, is_deleted
            )
            VALUES (
                gen_random_uuid(),
                'Sequential Thinking',
                'Dynamic, reflective problem-solving through structured thinking sequences. '
                'Creates, revises, and branches thought processes for complex reasoning.',
                'npx|-y|@anthropic-ai/sequential-thinking',
                'stdio',
                'bearer',
                '1.0.0',
                true,
                2,
                'No setup needed — runs locally via npx. No API key required.',
                NOW(),
                NOW(),
                false
            )
            ON CONFLICT DO NOTHING
            """
        )
    )


def downgrade() -> None:
    """Remove stdio support columns (enum value cannot be removed from PostgreSQL)."""
    op.alter_column("workspace_mcp_servers", "url", nullable=False)
    op.drop_column("workspace_mcp_servers", "stdio_args")
    op.drop_column("workspace_mcp_servers", "stdio_command")
    # Note: PostgreSQL does not support removing enum values; 'stdio' remains in the enum.
