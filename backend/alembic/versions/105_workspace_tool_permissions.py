"""Add workspace_tool_permissions and tool_permission_audit_log tables.

Phase 69 Wave 1 — granular per-workspace tool permissions for the AI
orchestrator (PERM-01, PERM-06). Both tables are workspace-scoped with
RLS: read for any workspace member, write restricted to OWNER/ADMIN,
service_role bypass.

Revision ID: 105_workspace_tool_permissions
Revises: 100_project_rbac_schema
Create Date: 2026-04-07
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "105_workspace_tool_permissions"
down_revision: str | None = "100_project_rbac_schema"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    # ── Table: workspace_tool_permissions ────────────────────────────────────
    op.create_table(
        "workspace_tool_permissions",
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
        sa.Column("tool_name", sa.String(length=128), nullable=False),
        sa.Column("mode", sa.String(length=8), nullable=False),
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
            "tool_name",
            name="uq_workspace_tool_permissions_workspace_tool",
        ),
        sa.CheckConstraint(
            "mode IN ('auto', 'ask', 'deny')",
            name="ck_workspace_tool_permissions_mode",
        ),
    )
    op.create_index(
        "ix_workspace_tool_permissions_workspace_tool",
        "workspace_tool_permissions",
        ["workspace_id", "tool_name"],
    )

    # ── Table: tool_permission_audit_log ─────────────────────────────────────
    op.create_table(
        "tool_permission_audit_log",
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
        sa.Column("tool_name", sa.String(length=128), nullable=False),
        sa.Column("old_mode", sa.String(length=8), nullable=True),
        sa.Column("new_mode", sa.String(length=8), nullable=False),
        sa.Column(
            "actor_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("reason", sa.String(length=256), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "new_mode IN ('auto', 'ask', 'deny')",
            name="ck_tool_permission_audit_log_new_mode",
        ),
        sa.CheckConstraint(
            "old_mode IS NULL OR old_mode IN ('auto', 'ask', 'deny')",
            name="ck_tool_permission_audit_log_old_mode",
        ),
    )
    op.create_index(
        "ix_tool_permission_audit_log_workspace_created",
        "tool_permission_audit_log",
        ["workspace_id", sa.text("created_at DESC")],
    )

    # ── RLS policies ─────────────────────────────────────────────────────────
    for table in ("workspace_tool_permissions", "tool_permission_audit_log"):
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
    for table in ("tool_permission_audit_log", "workspace_tool_permissions"):
        op.execute(text(f'DROP POLICY IF EXISTS "{table}_service_role_bypass" ON {table}'))
        op.execute(text(f'DROP POLICY IF EXISTS "{table}_admin_write" ON {table}'))
        op.execute(text(f'DROP POLICY IF EXISTS "{table}_workspace_isolation" ON {table}'))
        op.execute(text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY"))

    op.drop_index(
        "ix_tool_permission_audit_log_workspace_created",
        table_name="tool_permission_audit_log",
    )
    op.drop_table("tool_permission_audit_log")

    op.drop_index(
        "ix_workspace_tool_permissions_workspace_tool",
        table_name="workspace_tool_permissions",
    )
    op.drop_table("workspace_tool_permissions")
