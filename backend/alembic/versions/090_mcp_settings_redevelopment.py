"""MCP Settings Redevelopment — add server_type, transport, url_or_command, etc.

Revision ID: 090_mcp_settings_redevelopment
Revises: 089_add_role_type_idx
Create Date: 2026-03-20

Phase 25 — MCP Settings Redevelopment (merged 090–094):

Changes to workspace_mcp_servers table:
1. Creates three new PostgreSQL enum types:
   - mcp_server_type: ('remote', 'npx', 'uvx', 'command')
   - mcp_transport: ('sse', 'stdio', 'streamable_http')
   - mcp_status: ('enabled', 'disabled', 'unhealthy', 'unreachable', 'config_error')
2. Adds new columns:
   - server_type mcp_server_type NOT NULL DEFAULT 'remote'
   - transport mcp_transport NOT NULL DEFAULT 'sse'
   - url_or_command VARCHAR(1024) NULL
   - command_args VARCHAR(512) NULL
   - headers_encrypted TEXT NULL
   - env_vars_encrypted TEXT NULL
   - headers_json TEXT NULL
   - is_enabled BOOLEAN NOT NULL DEFAULT TRUE
3. Migrates last_status from VARCHAR(16) to mcp_status enum via USING cast:
   - 'connected' → 'enabled'
   - 'failed' → 'unreachable'
   - 'unknown' → NULL
   - NULL → NULL
4. Backfills url_or_command = url for existing rows.
5. Adds 'none' value to mcp_auth_type enum.
6. Creates partial unique index on (workspace_id, display_name) for active rows.

Downgrade reverses all changes: casts mcp_status back to varchar, drops
new columns, drops new enum types, drops the unique index.
Note: 'none' added to mcp_auth_type and 'command' added to mcp_server_type
cannot be undone (PostgreSQL does not support removing enum values).
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

    # 1. Create the three new enum types.
    #    mcp_server_type includes 'command' from the start — no separate ADD VALUE needed.
    op.execute(
        text(
            "CREATE TYPE mcp_server_type AS ENUM ('remote', 'npx', 'uvx', 'command')"
        )
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
                "remote", "npx", "uvx", "command",
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
        sa.Column("headers_json", sa.Text(), nullable=True),
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

    # 6. Add 'none' to mcp_auth_type enum.
    #    ALTER TYPE ... ADD VALUE cannot run inside a transaction block.
    op.execute(text("COMMIT"))
    op.execute(
        text("ALTER TYPE mcp_auth_type ADD VALUE IF NOT EXISTS 'none' BEFORE 'bearer'")
    )
    op.execute(text("BEGIN"))

    # 7. Partial unique index on (workspace_id, display_name) for active rows.
    op.execute(
        text(
            """
            CREATE UNIQUE INDEX uq_mcp_servers_workspace_display_name_active
            ON workspace_mcp_servers (workspace_id, display_name)
            WHERE is_deleted = false
            """
        )
    )


def downgrade() -> None:
    """Revert last_status to VARCHAR, drop new columns, drop new enums, drop index."""

    # 1. Drop the partial unique index
    op.execute(
        text("DROP INDEX IF EXISTS uq_mcp_servers_workspace_display_name_active")
    )

    # 2. Cast last_status back from mcp_status enum to VARCHAR(16)
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

    # 3. Drop new columns
    op.drop_column("workspace_mcp_servers", "is_enabled")
    op.drop_column("workspace_mcp_servers", "headers_json")
    op.drop_column("workspace_mcp_servers", "env_vars_encrypted")
    op.drop_column("workspace_mcp_servers", "headers_encrypted")
    op.drop_column("workspace_mcp_servers", "command_args")
    op.drop_column("workspace_mcp_servers", "url_or_command")
    op.drop_column("workspace_mcp_servers", "transport")
    op.drop_column("workspace_mcp_servers", "server_type")

    # 4. Drop the new enum types (order matters — no dependencies)
    op.execute(text("DROP TYPE IF EXISTS mcp_status"))
    op.execute(text("DROP TYPE IF EXISTS mcp_transport"))
    op.execute(text("DROP TYPE IF EXISTS mcp_server_type"))

    # Note: 'none' added to mcp_auth_type and cannot be removed.
    # Note: 'command' was included in mcp_server_type at creation, so dropping
    #       the type above handles that entirely.
