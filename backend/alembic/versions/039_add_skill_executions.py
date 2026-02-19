"""Add skill_executions table.

Creates the skill_executions table for recording SDK subagent executions
with approval workflow support (auto_approved / pending_approval / approved /
rejected / expired).

C-1 fix: Full CREATE TABLE — no prior skill_executions table exists, no backfill needed.
C-7 fix: required_approval_role column for role-based approval enforcement.
T-070: fn_expire_pending_approvals() pg_cron function added here.

Revision ID: 039_add_skill_executions
Revises: 038_add_work_intents
Create Date: 2026-02-19
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision = "039_add_skill_executions"
down_revision = "038_add_work_intents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create skill_executions table with approval workflow."""
    # 1. Create approval_status enum
    op.execute("""
        CREATE TYPE skill_approval_status_enum AS ENUM (
            'auto_approved',
            'pending_approval',
            'approved',
            'rejected',
            'expired'
        )
    """)

    # 2. Create required_approval_role enum (C-7)
    op.execute("""
        CREATE TYPE skill_approval_role_enum AS ENUM (
            'admin',
            'member'
        )
    """)

    # 3. Create skill_executions table
    op.create_table(
        "skill_executions",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "intent_id",
            UUID(as_uuid=True),
            sa.ForeignKey("work_intents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("skill_name", sa.Text(), nullable=False),
        sa.Column(
            "approval_status",
            sa.Enum(
                "auto_approved",
                "pending_approval",
                "approved",
                "rejected",
                "expired",
                name="skill_approval_status_enum",
                create_type=False,
            ),
            nullable=False,
            server_default="auto_approved",
        ),
        # C-7: role-based approval (nullable = no role restriction)
        sa.Column(
            "required_approval_role",
            sa.Enum(
                "admin",
                "member",
                name="skill_approval_role_enum",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("output", sa.JSON(), nullable=True),
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
        # BaseModel soft-delete columns (D-3 fix)
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 4. Indexes
    op.create_index(
        "ix_skill_executions_intent_id",
        "skill_executions",
        ["intent_id"],
    )
    op.create_index(
        "ix_skill_executions_approval_status",
        "skill_executions",
        ["approval_status"],
    )
    op.create_index(
        "ix_skill_executions_created_at",
        "skill_executions",
        ["created_at"],
    )

    # 5. RLS — workspace isolation via join to work_intents
    op.execute("ALTER TABLE skill_executions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE skill_executions FORCE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY "skill_executions_workspace_isolation"
        ON skill_executions FOR ALL
        USING (
            intent_id IN (
                SELECT wi.id
                FROM work_intents wi
                JOIN workspace_members wm ON wm.workspace_id = wi.workspace_id
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                AND wm.is_deleted = false
            )
        )
        WITH CHECK (
            intent_id IN (
                SELECT wi.id
                FROM work_intents wi
                JOIN workspace_members wm ON wm.workspace_id = wi.workspace_id
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                AND wm.is_deleted = false
            )
        )
    """)

    # 6. T-070: fn_expire_pending_approvals() pg_cron function
    # Sets approval_status='expired' on pending_approval rows older than 24h
    op.execute("""
        CREATE OR REPLACE FUNCTION fn_expire_pending_approvals()
        RETURNS void
        LANGUAGE plpgsql
        SECURITY DEFINER
        AS $$
        BEGIN
            UPDATE skill_executions
            SET approval_status = 'expired',
                updated_at = now()
            WHERE approval_status = 'pending_approval'
              AND created_at < now() - interval '24 hours';
        END;
        $$
    """)

    # Schedule hourly via pg_cron (requires pg_cron extension)
    # Skipped if pg_cron is not available — caller should schedule manually
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_extension WHERE extname = 'pg_cron'
            ) THEN
                PERFORM cron.schedule(
                    'expire-pending-approvals',
                    '0 * * * *',
                    'SELECT fn_expire_pending_approvals()'
                );
            END IF;
        END;
        $$
    """)


def downgrade() -> None:
    """Remove skill_executions table and supporting objects."""
    # Remove pg_cron job if pg_cron is available
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_extension WHERE extname = 'pg_cron'
            ) THEN
                PERFORM cron.unschedule('expire-pending-approvals');
            END IF;
        END;
        $$
    """)

    op.execute("DROP FUNCTION IF EXISTS fn_expire_pending_approvals()")

    op.execute('DROP POLICY IF EXISTS "skill_executions_workspace_isolation" ON skill_executions')
    op.execute("ALTER TABLE skill_executions DISABLE ROW LEVEL SECURITY")

    op.drop_index("ix_skill_executions_created_at", table_name="skill_executions")
    op.drop_index("ix_skill_executions_approval_status", table_name="skill_executions")
    op.drop_index("ix_skill_executions_intent_id", table_name="skill_executions")

    op.drop_table("skill_executions")

    op.execute("DROP TYPE IF EXISTS skill_approval_role_enum")
    op.execute("DROP TYPE IF EXISTS skill_approval_status_enum")
