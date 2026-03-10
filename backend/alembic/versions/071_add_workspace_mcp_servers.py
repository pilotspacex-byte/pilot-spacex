"""Add workspace_mcp_servers table with mcp_auth_type enum and RLS policies.

Revision ID: 071_add_workspace_mcp_servers
Revises: 070_extend_ai_config_custom_provider
Create Date: 2026-03-10

Phase 14 — Remote MCP Server Management (MCP-01, MCP-02, MCP-06):

1. Creates mcp_auth_type PostgreSQL enum: ('bearer', 'oauth2').
2. Creates workspace_mcp_servers table with:
   - Standard WorkspaceScopedModel columns (id, workspace_id, created_at,
     updated_at, is_deleted, deleted_at)
   - display_name VARCHAR(128): human-readable label
   - url VARCHAR(512): remote MCP server endpoint
   - auth_type mcp_auth_type: authentication mechanism
   - auth_token_encrypted VARCHAR(1024): Fernet-encrypted Bearer/OAuth token
   - oauth_client_id/auth_url/token_url/scopes: OAuth 2.0 metadata
   - last_status VARCHAR(16): cached connectivity status
   - last_status_checked_at TIMESTAMPTZ: last probe timestamp
3. Enables RLS with workspace isolation policy and service_role bypass.
4. Creates index on workspace_id for efficient workspace-scoped queries.

Downgrade reverses all changes: drops policies, table, and enum.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "071_add_workspace_mcp_servers"
down_revision: str = "070_extend_ai_config_custom_provider"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    """Create mcp_auth_type enum, workspace_mcp_servers table, and RLS policies."""

    # 1+2. Create mcp_auth_type enum and workspace_mcp_servers table
    # sa.Enum without create_type=False lets op.create_table emit CREATE TYPE automatically.
    op.create_table(
        "workspace_mcp_servers",
        # Primary key
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
            nullable=False,
        ),
        # Workspace scoping (FK with cascade delete)
        sa.Column(
            "workspace_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        # Soft delete
        sa.Column(
            "is_deleted",
            sa.Boolean,
            server_default=text("false"),
            nullable=False,
        ),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        # MCP server fields
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column("url", sa.String(512), nullable=False),
        sa.Column(
            "auth_type",
            sa.Enum("bearer", "oauth2", name="mcp_auth_type"),
            nullable=False,
            server_default=text("'bearer'::mcp_auth_type"),
        ),
        # Encrypted credential
        sa.Column("auth_token_encrypted", sa.String(1024), nullable=True),
        # OAuth 2.0 metadata
        sa.Column("oauth_client_id", sa.String(256), nullable=True),
        sa.Column("oauth_auth_url", sa.String(512), nullable=True),
        sa.Column("oauth_token_url", sa.String(512), nullable=True),
        sa.Column("oauth_scopes", sa.String(512), nullable=True),
        # Cached connectivity status
        sa.Column("last_status", sa.String(16), nullable=True),
        sa.Column("last_status_checked_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 3. Enable RLS on workspace_mcp_servers
    op.execute(text("ALTER TABLE workspace_mcp_servers ENABLE ROW LEVEL SECURITY"))
    op.execute(text("ALTER TABLE workspace_mcp_servers FORCE ROW LEVEL SECURITY"))

    # 4. Workspace isolation policy: users see rows in workspaces they are members of
    op.execute(
        text(
            """
            CREATE POLICY "workspace_mcp_servers_workspace_isolation"
            ON workspace_mcp_servers
            FOR ALL
            USING (
                workspace_id IN (
                    SELECT wm.workspace_id
                    FROM workspace_members wm
                    WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                    AND wm.is_deleted = false
                )
            )
            """
        )
    )

    # 5. Service-role bypass policy (for admin/background operations)
    op.execute(
        text(
            """
            CREATE POLICY "workspace_mcp_servers_service_role"
            ON workspace_mcp_servers
            FOR ALL
            TO service_role
            USING (true)
            WITH CHECK (true)
            """
        )
    )

    # 6. Index on workspace_id for efficient workspace-scoped queries
    op.create_index(
        "ix_workspace_mcp_servers_workspace_id",
        "workspace_mcp_servers",
        ["workspace_id"],
    )


def downgrade() -> None:
    """Drop RLS policies, workspace_mcp_servers table, and mcp_auth_type enum."""

    # 1. Drop RLS policies
    op.execute(
        text(
            'DROP POLICY IF EXISTS "workspace_mcp_servers_workspace_isolation" '
            "ON workspace_mcp_servers"
        )
    )
    op.execute(
        text('DROP POLICY IF EXISTS "workspace_mcp_servers_service_role" ON workspace_mcp_servers')
    )

    # 2. Drop index
    op.drop_index("ix_workspace_mcp_servers_workspace_id", table_name="workspace_mcp_servers")

    # 3. Drop table
    op.drop_table("workspace_mcp_servers")

    # 4. Drop the enum type
    op.execute(text("DROP TYPE IF EXISTS mcp_auth_type"))
