"""MCP Settings Redevelopment — add server_type, transport, url_or_command, etc.

Revision ID: 090_mcp_settings_redevelopment
Revises: 089_add_role_type_idx
Create Date: 2026-03-19

Phase 25 — MCP Settings Redevelopment:

Changes to workspace_mcp_servers table:
1. Creates three new PostgreSQL enum types:
   - mcp_server_type: ('remote', 'npx', 'uvx')
   - mcp_transport: ('sse', 'stdio', 'streamable_http')
   - mcp_status: ('enabled', 'disabled', 'unhealthy', 'unreachable', 'config_error')
2. Adds new columns:
   - server_type mcp_server_type NOT NULL DEFAULT 'remote'
   - transport mcp_transport NOT NULL DEFAULT 'sse'
   - url_or_command VARCHAR(1024) NULL
   - command_args VARCHAR(512) NULL
   - headers_encrypted TEXT NULL
   - env_vars_encrypted TEXT NULL
   - is_enabled BOOLEAN NOT NULL DEFAULT TRUE
3. Migrates last_status from VARCHAR(16) to mcp_status enum via USING cast:
   - 'connected' → 'enabled'
   - 'failed' → 'unreachable'
   - 'unknown' → NULL
   - NULL → NULL
4. Backfills url_or_command = url for existing rows.

Downgrade reverses all changes: casts mcp_status back to varchar, drops
new columns, drops new enum types.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "090_mcp_settings_redevelopment"
down_revision: str = "089_add_role_type_idx"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    """Add new columns, enums, and migrate last_status from VARCHAR to enum."""

    # 1. Create the three new enum types
    op.execute(
        text("CREATE TYPE mcp_server_type AS ENUM ('remote', 'npx', 'uvx')")
    )
    op.execute(
        text("CREATE TYPE mcp_transport AS ENUM ('sse', 'stdio', 'streamable_http')")
    )
    op.execute(
        text(
            "CREATE TYPE mcp_status AS ENUM "
            "('enabled', 'disabled', 'unhealthy', 'unreachable', 'config_error')"
        )
    )

    # 2. Add new columns (nullable first so migration works on existing rows)
    op.add_column(
        "workspace_mcp_servers",
        sa.Column(
            "server_type",
            sa.Enum(
                "remote", "npx", "uvx",
                name="mcp_server_type",
                create_type=False,
            ),
            nullable=True,  # temporarily nullable for backfill
        ),
    )
    op.add_column(
        "workspace_mcp_servers",
        sa.Column(
            "transport",
            sa.Enum(
                "sse", "stdio", "streamable_http",
                name="mcp_transport",
                create_type=False,
            ),
            nullable=True,  # temporarily nullable for backfill
        ),
    )
    op.add_column(
        "workspace_mcp_servers",
        sa.Column("url_or_command", sa.String(1024), nullable=True),
    )
    op.add_column(
        "workspace_mcp_servers",
        sa.Column("command_args", sa.String(512), nullable=True),
    )
    op.add_column(
        "workspace_mcp_servers",
        sa.Column("headers_encrypted", sa.Text, nullable=True),
    )
    op.add_column(
        "workspace_mcp_servers",
        sa.Column("env_vars_encrypted", sa.Text, nullable=True),
    )
    op.add_column(
        "workspace_mcp_servers",
        sa.Column("is_enabled", sa.Boolean, nullable=True),  # nullable during backfill
    )

    # 3. Backfill new columns on existing rows
    op.execute(
        text(
            """
            UPDATE workspace_mcp_servers
            SET
                url_or_command = url,
                server_type = 'remote'::mcp_server_type,
                transport = 'sse'::mcp_transport,
                is_enabled = TRUE
            """
        )
    )

    # 4. Set NOT NULL constraints and DB-level defaults on backfilled columns.
    #    server_default ensures raw INSERT statements that omit these columns
    #    use the intended values rather than failing at the DB level.
    op.alter_column(
        "workspace_mcp_servers",
        "server_type",
        nullable=False,
        server_default=sa.text("'remote'::mcp_server_type"),
    )
    op.alter_column(
        "workspace_mcp_servers",
        "transport",
        nullable=False,
        server_default=sa.text("'sse'::mcp_transport"),
    )
    op.alter_column(
        "workspace_mcp_servers",
        "is_enabled",
        nullable=False,
        server_default=sa.text("TRUE"),
    )

    # 5. Migrate last_status VARCHAR(16) → mcp_status enum
    #    Cast mapping: 'connected'→'enabled', 'failed'→'unreachable', others→NULL
    op.execute(
        text(
            """
            ALTER TABLE workspace_mcp_servers
            ALTER COLUMN last_status TYPE mcp_status
            USING (
                CASE last_status
                    WHEN 'connected' THEN 'enabled'::mcp_status
                    WHEN 'failed'    THEN 'unreachable'::mcp_status
                    ELSE NULL
                END
            )
            """
        )
    )


def downgrade() -> None:
    """Revert last_status to VARCHAR, drop new columns, drop new enums."""

    # 1. Cast last_status back from mcp_status enum to VARCHAR(16)
    op.execute(
        text(
            """
            ALTER TABLE workspace_mcp_servers
            ALTER COLUMN last_status TYPE VARCHAR(16)
            USING (
                CASE last_status::text
                    WHEN 'enabled'      THEN 'connected'
                    WHEN 'unreachable'  THEN 'failed'
                    WHEN 'unhealthy'    THEN 'failed'
                    ELSE NULL
                END
            )
            """
        )
    )

    # 2. Drop new columns
    op.drop_column("workspace_mcp_servers", "is_enabled")
    op.drop_column("workspace_mcp_servers", "env_vars_encrypted")
    op.drop_column("workspace_mcp_servers", "headers_encrypted")
    op.drop_column("workspace_mcp_servers", "command_args")
    op.drop_column("workspace_mcp_servers", "url_or_command")
    op.drop_column("workspace_mcp_servers", "transport")
    op.drop_column("workspace_mcp_servers", "server_type")

    # 3. Drop the new enum types (order matters — no dependencies)
    op.execute(text("DROP TYPE IF EXISTS mcp_status"))
    op.execute(text("DROP TYPE IF EXISTS mcp_transport"))
    op.execute(text("DROP TYPE IF EXISTS mcp_server_type"))
