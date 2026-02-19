"""Add work_intents and intent_artifacts tables.

Creates the work_intents table for the AI workforce platform feature (015).
Stores detected/confirmed user intents with lifecycle tracking, dedup hashing,
and parent-child hierarchy for decomposed intents.

Revision ID: 038_add_work_intents
Revises: 037_add_task_management
Create Date: 2026-02-19
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision = "038_add_work_intents"
down_revision = "037_add_task_management"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add work_intents and intent_artifacts tables."""
    # 1. Create work_intents table
    op.create_table(
        "work_intents",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "workspace_id",
            UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("what", sa.Text(), nullable=False),
        sa.Column("why", sa.Text(), nullable=True),
        sa.Column("constraints", sa.JSON(), nullable=True),
        sa.Column("acceptance", sa.JSON(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "detected",
                "confirmed",
                "executing",
                "review",
                "accepted",
                "rejected",
                name="work_intent_status_enum",
            ),
            nullable=False,
            server_default="detected",
        ),
        sa.Column("owner", sa.String(255), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column(
            "parent_intent_id",
            UUID(as_uuid=True),
            sa.ForeignKey("work_intents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("source_block_id", UUID(as_uuid=True), nullable=True),
        sa.Column("dedup_hash", sa.String(64), nullable=True),
        sa.Column(
            "dedup_status",
            sa.Enum(
                "pending",
                "complete",
                name="intent_dedup_status_enum",
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
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
    )

    # 2. Indexes for work_intents
    op.create_index(
        "ix_work_intents_workspace_status",
        "work_intents",
        ["workspace_id", "status"],
    )
    op.create_index(
        "ix_work_intents_parent_intent_id",
        "work_intents",
        ["parent_intent_id"],
    )
    op.create_index(
        "ix_work_intents_source_block_id",
        "work_intents",
        ["source_block_id"],
    )
    op.create_index(
        "ix_work_intents_dedup_hash",
        "work_intents",
        ["dedup_hash"],
    )
    op.create_index(
        "ix_work_intents_is_deleted",
        "work_intents",
        ["is_deleted"],
    )

    # 3. RLS for work_intents
    op.execute("ALTER TABLE work_intents ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE work_intents FORCE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY "work_intents_workspace_isolation"
        ON work_intents FOR ALL
        USING (
            workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                AND wm.is_deleted = false
            )
        )
        WITH CHECK (
            workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                AND wm.is_deleted = false
            )
        )
    """)

    # 4. Create intent_artifacts table
    op.create_table(
        "intent_artifacts",
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
        sa.Column(
            "artifact_type",
            sa.Enum(
                "note_block",
                "issue",
                "note",
                name="intent_artifact_type_enum",
            ),
            nullable=False,
        ),
        sa.Column("reference_id", UUID(as_uuid=True), nullable=False),
        sa.Column("reference_type", sa.String(50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # 5. Indexes for intent_artifacts
    op.create_index(
        "ix_intent_artifacts_intent_id",
        "intent_artifacts",
        ["intent_id"],
    )
    op.create_index(
        "ix_intent_artifacts_reference_id",
        "intent_artifacts",
        ["reference_id"],
    )

    # 6. RLS for intent_artifacts (via join to work_intents.workspace_id)
    op.execute("ALTER TABLE intent_artifacts ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE intent_artifacts FORCE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY "intent_artifacts_workspace_isolation"
        ON intent_artifacts FOR ALL
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

    # 7. T-013: Stale intent expiry function (J-2) + pg_cron schedule
    # Expires detected intents older than 1 hour to 'rejected' status.
    # Scheduled every 15 minutes via pg_cron.
    op.execute("""
        CREATE OR REPLACE FUNCTION fn_expire_stale_intents()
        RETURNS void
        LANGUAGE plpgsql
        SECURITY DEFINER
        AS $$
        BEGIN
            UPDATE work_intents
            SET status = 'rejected',
                updated_at = now()
            WHERE status = 'detected'
              AND created_at < now() - interval '1 hour'
              AND is_deleted = false;
        END;
        $$
    """)

    # Schedule via pg_cron (runs every 15 minutes).
    # Wrapped in a DO block so it's skipped gracefully if pg_cron is not installed.
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron') THEN
                PERFORM cron.schedule(
                    'expire-stale-intents',
                    '*/15 * * * *',
                    'SELECT fn_expire_stale_intents()'
                );
            END IF;
        END;
        $$
    """)


def downgrade() -> None:
    """Remove work_intents and intent_artifacts tables."""
    # Remove pg_cron job (gracefully skips if pg_cron not installed)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron') THEN
                PERFORM cron.unschedule('expire-stale-intents');
            END IF;
        END;
        $$
    """)
    op.execute("DROP FUNCTION IF EXISTS fn_expire_stale_intents()")

    # Drop intent_artifacts first (FK dependency)
    op.execute('DROP POLICY IF EXISTS "intent_artifacts_workspace_isolation" ON intent_artifacts')
    op.execute("ALTER TABLE intent_artifacts DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_intent_artifacts_reference_id", table_name="intent_artifacts")
    op.drop_index("ix_intent_artifacts_intent_id", table_name="intent_artifacts")
    op.drop_table("intent_artifacts")
    op.execute("DROP TYPE IF EXISTS intent_artifact_type_enum")

    # Drop work_intents
    op.execute('DROP POLICY IF EXISTS "work_intents_workspace_isolation" ON work_intents')
    op.execute("ALTER TABLE work_intents DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_work_intents_is_deleted", table_name="work_intents")
    op.drop_index("ix_work_intents_dedup_hash", table_name="work_intents")
    op.drop_index("ix_work_intents_source_block_id", table_name="work_intents")
    op.drop_index("ix_work_intents_parent_intent_id", table_name="work_intents")
    op.drop_index("ix_work_intents_workspace_status", table_name="work_intents")
    op.drop_table("work_intents")
    op.execute("DROP TYPE IF EXISTS intent_dedup_status_enum")
    op.execute("DROP TYPE IF EXISTS work_intent_status_enum")
