"""Add memory_lifecycle_audit table for pin / forget / gdpr_forget events.

Phase 69 — PR #126 review finding H2. The memory lifecycle service previously
only wrote stdlib log lines on destructive actions, which is not defensible
under GDPR Article 30 (records of processing). This migration adds a
workspace-scoped, RLS-protected audit table written inside the same
transaction as the primary mutation.

Revision ID: 107_memory_lifecycle_audit
Revises: 106_phase69_memory_node_types
Create Date: 2026-04-08
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "107_memory_lifecycle_audit"
down_revision: str | None = "106_phase69_memory_node_types"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


_TABLE = "memory_lifecycle_audit"


def upgrade() -> None:
    op.create_table(
        _TABLE,
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
        sa.Column(
            "actor_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("action", sa.String(length=32), nullable=False),
        # node_id is nullable because gdpr_forget targets many rows at once.
        sa.Column("node_id", postgresql.UUID(as_uuid=True), nullable=True),
        # target_user_id is only populated for gdpr_forget.
        sa.Column("target_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("deleted_count", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "action IN ('pin', 'forget', 'gdpr_forget')",
            name="ck_memory_lifecycle_audit_action",
        ),
    )
    op.create_index(
        "ix_memory_lifecycle_audit_workspace_created",
        _TABLE,
        ["workspace_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_memory_lifecycle_audit_target_user",
        _TABLE,
        ["target_user_id"],
        postgresql_where=sa.text("target_user_id IS NOT NULL"),
    )

    # ── RLS ──────────────────────────────────────────────────────────────────
    op.execute(text(f"ALTER TABLE {_TABLE} ENABLE ROW LEVEL SECURITY"))
    op.execute(text(f"ALTER TABLE {_TABLE} FORCE ROW LEVEL SECURITY"))

    # Any workspace member can SELECT their own workspace's audit rows.
    op.execute(
        text(
            f"""
            CREATE POLICY "{_TABLE}_workspace_isolation"
            ON {_TABLE}
            FOR SELECT
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

    # Only OWNER/ADMIN can INSERT (audit rows are append-only — no UPDATE/DELETE policy).
    op.execute(
        text(
            f"""
            CREATE POLICY "{_TABLE}_admin_insert"
            ON {_TABLE}
            FOR INSERT
            WITH CHECK (
                workspace_id IN (
                    SELECT wm.workspace_id
                    FROM workspace_members wm
                    WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                      AND wm.role IN ('OWNER', 'ADMIN')
                      AND wm.is_deleted = false
                )
            )
            """
        )
    )

    # Service role bypass (background jobs / migrations).
    op.execute(
        text(
            f"""
            CREATE POLICY "{_TABLE}_service_role_bypass"
            ON {_TABLE}
            FOR ALL
            TO service_role
            USING (true)
            WITH CHECK (true)
            """
        )
    )


def downgrade() -> None:
    op.execute(text(f'DROP POLICY IF EXISTS "{_TABLE}_service_role_bypass" ON {_TABLE}'))
    op.execute(text(f'DROP POLICY IF EXISTS "{_TABLE}_admin_insert" ON {_TABLE}'))
    op.execute(text(f'DROP POLICY IF EXISTS "{_TABLE}_workspace_isolation" ON {_TABLE}'))
    op.execute(text(f"ALTER TABLE {_TABLE} DISABLE ROW LEVEL SECURITY"))
    op.drop_index("ix_memory_lifecycle_audit_target_user", table_name=_TABLE)
    op.drop_index("ix_memory_lifecycle_audit_workspace_created", table_name=_TABLE)
    op.drop_table(_TABLE)
