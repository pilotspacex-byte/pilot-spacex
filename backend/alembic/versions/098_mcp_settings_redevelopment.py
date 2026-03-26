"""MCP Settings Redevelopment — add server_type, transport, url_or_command, etc.

Revision ID: 096_mcp_settings_redevelopment
Revises: 089_add_role_type_idx
Create Date: 2026-03-20

Phase 25 — MCP Settings Redevelopment (merged 090–092):

Changes to workspace_mcp_servers table:
1. Creates four new PostgreSQL enum types:
   - mcp_server_type: ('remote', 'command')
   - mcp_command_runner: ('npx', 'uvx')
   - mcp_transport: ('sse', 'stdio', 'streamable_http')
   - mcp_status: ('enabled', 'disabled', 'unhealthy', 'unreachable', 'config_error')
2. Adds new columns:
   - server_type mcp_server_type NOT NULL DEFAULT 'remote'
   - transport mcp_transport NOT NULL DEFAULT 'sse'
   - url_or_command VARCHAR(1024) NULL
   - command_args VARCHAR(512) NULL
   - command_runner mcp_command_runner NULL
   - headers_encrypted TEXT NULL
   - env_vars_encrypted TEXT NULL
   - headers_json TEXT NULL
   - is_enabled BOOLEAN NOT NULL DEFAULT TRUE
3. Widens url to VARCHAR(1024) NULL (was VARCHAR(512) NOT NULL).
4. Migrates last_status from VARCHAR(16) to mcp_status enum via USING cast:
   - 'connected' → 'enabled'
   - 'failed' → 'unreachable'
   - 'unknown' → NULL
   - NULL → NULL
5. Backfills url_or_command = url for existing rows.
6. Adds 'none' value to mcp_auth_type enum.
7. Creates partial unique index on (workspace_id, display_name) for active rows.

Downgrade reverses all changes.
Note: 'none' added to mcp_auth_type cannot be undone (PostgreSQL does not
support removing enum values).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "098_mcp_settings_redevelopment"
down_revision: str = "097_fix_artifact_annotations_rls"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    """Add new columns, enums, and migrate last_status from VARCHAR to enum."""

    # 1. Create the four new enum types (IF NOT EXISTS for idempotency).
    op.execute(text("DO $$ BEGIN CREATE TYPE mcp_server_type AS ENUM ('remote', 'command'); EXCEPTION WHEN duplicate_object THEN NULL; END $$"))
    op.execute(text("DO $$ BEGIN CREATE TYPE mcp_command_runner AS ENUM ('npx', 'uvx'); EXCEPTION WHEN duplicate_object THEN NULL; END $$"))
    op.execute(text("DO $$ BEGIN CREATE TYPE mcp_transport AS ENUM ('sse', 'stdio', 'streamable_http'); EXCEPTION WHEN duplicate_object THEN NULL; END $$"))
    op.execute(text("DO $$ BEGIN CREATE TYPE mcp_status AS ENUM ('enabled', 'disabled', 'unhealthy', 'unreachable', 'config_error'); EXCEPTION WHEN duplicate_object THEN NULL; END $$"))

    # 2. Add new columns (nullable first so migration works on existing rows).
    op.add_column(
        "workspace_mcp_servers",
        sa.Column(
            "server_type",
            sa.Enum("remote", "command", name="mcp_server_type", create_type=False),
            nullable=True,
        ),
    )
    op.add_column(
        "workspace_mcp_servers",
        sa.Column(
            "transport",
            sa.Enum(
                "sse",
                "stdio",
                "streamable_http",
                name="mcp_transport",
                create_type=False,
            ),
            nullable=True,
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
        sa.Column(
            "command_runner",
            sa.Enum("npx", "uvx", name="mcp_command_runner", create_type=False),
            nullable=True,
        ),
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
        sa.Column("is_enabled", sa.Boolean, nullable=True),
    )

    # 3. Widen the legacy url column to VARCHAR(1024) and allow NULL.
    op.execute(
        text(
            "ALTER TABLE workspace_mcp_servers "
            "ALTER COLUMN url TYPE VARCHAR(1024), "
            "ALTER COLUMN url DROP NOT NULL"
        )
    )

    # 4. Backfill new columns on existing rows.
    op.execute(
        text(
            """
            UPDATE workspace_mcp_servers
            SET
                url_or_command = url,
                server_type    = 'remote'::mcp_server_type,
                transport      = 'sse'::mcp_transport,
                is_enabled     = TRUE
            """
        )
    )

    # 5. Set NOT NULL constraints and DB-level defaults on backfilled columns.
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

    # 6. Migrate last_status VARCHAR(16) → mcp_status enum.
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

    # 7. Add 'none' to mcp_auth_type enum.
    #    ALTER TYPE ... ADD VALUE cannot run inside a transaction block.
    op.execute(text("COMMIT"))
    op.execute(
        text("ALTER TYPE mcp_auth_type ADD VALUE IF NOT EXISTS 'none' BEFORE 'bearer'")
    )
    op.execute(text("BEGIN"))

    # 8. Partial unique index on (workspace_id, display_name) for active rows.
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

    # 1. Drop the partial unique index.
    op.execute(
        text("DROP INDEX IF EXISTS uq_mcp_servers_workspace_display_name_active")
    )

    # 2. Cast last_status back from mcp_status enum to VARCHAR(16).
    op.execute(
        text(
            """
            ALTER TABLE workspace_mcp_servers
            ALTER COLUMN last_status TYPE VARCHAR(16)
            USING (
                CASE last_status::text
                    WHEN 'enabled'     THEN 'connected'
                    WHEN 'unreachable' THEN 'failed'
                    WHEN 'unhealthy'   THEN 'failed'
                    ELSE NULL
                END
            )
            """
        )
    )

    # 3. Drop new columns.
    op.drop_column("workspace_mcp_servers", "is_enabled")
    op.drop_column("workspace_mcp_servers", "headers_json")
    op.drop_column("workspace_mcp_servers", "env_vars_encrypted")
    op.drop_column("workspace_mcp_servers", "headers_encrypted")
    op.drop_column("workspace_mcp_servers", "command_runner")
    op.drop_column("workspace_mcp_servers", "command_args")
    op.drop_column("workspace_mcp_servers", "url_or_command")
    op.drop_column("workspace_mcp_servers", "transport")
    op.drop_column("workspace_mcp_servers", "server_type")

    # 4. Restore url to VARCHAR(512) NOT NULL (backfill NULLs first).
    op.execute(text("UPDATE workspace_mcp_servers SET url = '' WHERE url IS NULL"))
    op.execute(
        text(
            "ALTER TABLE workspace_mcp_servers "
            "ALTER COLUMN url TYPE VARCHAR(512), "
            "ALTER COLUMN url SET NOT NULL"
        )
    )

    # 5. Drop the new enum types (order matters — no dependencies).
    op.execute(text("DROP TYPE IF EXISTS mcp_status"))
    op.execute(text("DROP TYPE IF EXISTS mcp_transport"))
    op.execute(text("DROP TYPE IF EXISTS mcp_command_runner"))
    op.execute(text("DROP TYPE IF EXISTS mcp_server_type"))

    # Note: 'none' added to mcp_auth_type cannot be removed (PostgreSQL limitation).
