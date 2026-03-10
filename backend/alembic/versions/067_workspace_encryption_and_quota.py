"""Add workspace_encryption_keys table and workspace quota columns.

Revision ID: 067_workspace_encryption_and_quota
Revises: 066_fix_rls_enum_case
Create Date: 2026-03-08

Phase 3 — Multi-Tenant Isolation (TENANT-02):

workspace_encryption_keys table:
  - Stores per-workspace Fernet key encrypted with system master key
  - RLS: NO SELECT for regular users (encrypted_workspace_key must never reach client)
  - service_role bypass for backend service operations only
  - One record per workspace (UNIQUE on workspace_id)

workspace quota columns (added to workspaces table):
  - rate_limit_standard_rpm: Standard API requests per minute limit (NULL = no limit)
  - rate_limit_ai_rpm: AI API requests per minute limit (NULL = no limit)
  - storage_quota_mb: Max storage in megabytes (NULL = no limit)
  - storage_used_bytes: Current storage usage in bytes (NOT NULL DEFAULT 0)

RLS Design for workspace_encryption_keys:
  Intentionally NO user-facing SELECT policy.
  Only service_role can query this table.
  Backend resolves the key server-side and never returns it to clients.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic
revision: str = "067_workspace_encryption_and_quota"
down_revision: str = "066_fix_rls_enum_case"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Create workspace_encryption_keys table with RLS and add quota columns."""

    # ------------------------------------------------------------------
    # Step 1: CREATE TABLE workspace_encryption_keys
    # ------------------------------------------------------------------
    op.create_table(
        "workspace_encryption_keys",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        # Master-key-encrypted workspace Fernet key — never returned to clients
        sa.Column(
            "encrypted_workspace_key",
            sa.Text,
            nullable=False,
        ),
        # Last 8 chars of raw key for UI display only (not sensitive)
        sa.Column(
            "key_hint",
            sa.String(8),
            nullable=True,
        ),
        # Monotonically increasing version counter for key rotations
        sa.Column(
            "key_version",
            sa.Integer,
            nullable=False,
            server_default="1",
        ),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=text("now()"),
            nullable=False,
        ),
    )

    # One encryption key per workspace
    op.create_unique_constraint(
        "uq_workspace_encryption_key_workspace",
        "workspace_encryption_keys",
        ["workspace_id"],
    )

    # ------------------------------------------------------------------
    # Step 2: Enable RLS on workspace_encryption_keys
    # ------------------------------------------------------------------
    op.execute(text("ALTER TABLE workspace_encryption_keys ENABLE ROW LEVEL SECURITY"))
    op.execute(text("ALTER TABLE workspace_encryption_keys FORCE ROW LEVEL SECURITY"))

    # service_role bypass — backend service operates as service_role
    # Intentionally NO user-facing SELECT policy:
    # encrypted_workspace_key must never reach the client via any API path.
    op.execute(
        text("""
            CREATE POLICY "service_role_bypass" ON workspace_encryption_keys
                AS PERMISSIVE
                FOR ALL
                TO service_role
                USING (true)
                WITH CHECK (true);
        """)
    )

    # ------------------------------------------------------------------
    # Step 3: Add quota columns to workspaces table
    # ------------------------------------------------------------------
    op.execute(
        text("""
            ALTER TABLE workspaces
                ADD COLUMN IF NOT EXISTS rate_limit_standard_rpm INTEGER,
                ADD COLUMN IF NOT EXISTS rate_limit_ai_rpm INTEGER,
                ADD COLUMN IF NOT EXISTS storage_quota_mb INTEGER,
                ADD COLUMN IF NOT EXISTS storage_used_bytes BIGINT NOT NULL DEFAULT 0;
        """)
    )


def downgrade() -> None:
    """Remove quota columns from workspaces and drop workspace_encryption_keys table."""

    # Remove quota columns from workspaces
    op.execute(
        text("""
            ALTER TABLE workspaces
                DROP COLUMN IF EXISTS storage_used_bytes,
                DROP COLUMN IF EXISTS storage_quota_mb,
                DROP COLUMN IF EXISTS rate_limit_ai_rpm,
                DROP COLUMN IF EXISTS rate_limit_standard_rpm;
        """)
    )

    # Drop RLS policy before dropping the table
    op.execute(
        text("""
            DROP POLICY IF EXISTS "service_role_bypass" ON workspace_encryption_keys;
        """)
    )

    # Drop the table (cascades unique constraint and indexes)
    op.drop_table("workspace_encryption_keys")
