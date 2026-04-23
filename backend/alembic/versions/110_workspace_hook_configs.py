"""Add workspace_hook_configs table for declarative hook rules.

Phase 83 Wave 1 -- workspace-configurable PreToolUse/PostToolUse/Stop hooks
(HOOK-02, HOOK-05). Admin-created rules map tool patterns to actions
(allow/deny/require_approval) with priority-based evaluation order.

RLS policies enforce workspace isolation: any member can SELECT, only
OWNER/ADMIN can write, service_role bypass for backend operations.

Revision ID: 110_workspace_hook_configs
Revises: 109_security_hardening_rls_and_backfill
Create Date: 2026-04-18
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "110_workspace_hook_configs"
down_revision: str | None = "109_security_hardening_rls_and_backfill"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    # ── Table: workspace_hook_configs ────────────────────────────────────────
    op.create_table(
        "workspace_hook_configs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.String(length=512), nullable=True),
        sa.Column("tool_pattern", sa.String(length=256), nullable=False),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column(
            "event_type",
            sa.String(length=20),
            server_default=sa.text("'PreToolUse'"),
            nullable=False,
        ),
        sa.Column(
            "priority",
            sa.Integer(),
            server_default=sa.text("100"),
            nullable=False,
        ),
        sa.Column(
            "is_enabled",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "updated_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "name",
            name="uq_workspace_hook_configs_workspace_name",
        ),
        sa.CheckConstraint(
            "action IN ('allow', 'deny', 'require_approval')",
            name="ck_workspace_hook_configs_action",
        ),
        sa.CheckConstraint(
            "event_type IN ('PreToolUse', 'PostToolUse', 'Stop')",
            name="ck_workspace_hook_configs_event_type",
        ),
    )

    # ── Indexes ──────────────────────────────────────────────────────────────
    op.create_index(
        "ix_workspace_hook_configs_workspace_priority",
        "workspace_hook_configs",
        ["workspace_id", "priority"],
    )

    # ── RLS policies ─────────────────────────────────────────────────────────
    table = "workspace_hook_configs"
    op.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
    op.execute(text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))

    # Any workspace member can SELECT
    op.execute(
        text(f"""
        CREATE POLICY "{table}_workspace_isolation"
        ON {table}
        FOR SELECT
        USING (
            workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                  AND wm.is_deleted = false
            )
        )
        """)
    )

    # Only OWNER/ADMIN can INSERT/UPDATE/DELETE
    op.execute(
        text(f"""
        CREATE POLICY "{table}_admin_write"
        ON {table}
        FOR ALL
        USING (
            workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                  AND wm.role IN ('OWNER', 'ADMIN')
                  AND wm.is_deleted = false
            )
        )
        WITH CHECK (
            workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                  AND wm.role IN ('OWNER', 'ADMIN')
                  AND wm.is_deleted = false
            )
        )
        """)
    )

    # Service role bypass
    op.execute(
        text(f"""
        CREATE POLICY "{table}_service_role_bypass"
        ON {table}
        FOR ALL
        TO service_role
        USING (true)
        WITH CHECK (true)
        """)
    )


def downgrade() -> None:
    table = "workspace_hook_configs"

    # Drop RLS policies
    op.execute(text(f'DROP POLICY IF EXISTS "{table}_service_role_bypass" ON {table}'))
    op.execute(text(f'DROP POLICY IF EXISTS "{table}_admin_write" ON {table}'))
    op.execute(text(f'DROP POLICY IF EXISTS "{table}_workspace_isolation" ON {table}'))
    op.execute(text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY"))

    # Drop indexes and table
    op.drop_index(
        "ix_workspace_hook_configs_workspace_priority",
        table_name="workspace_hook_configs",
    )
    op.drop_table("workspace_hook_configs")
