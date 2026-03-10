"""Add audit_log table with immutability trigger, RLS, and pg_cron retention.

Revision ID: 065_add_audit_log_table
Revises: 064_add_sso_rbac_session_tables
Create Date: 2026-03-08

Phase 2 — Compliance & Audit foundation:

- AUDIT-01: audit_log table capturing all workspace actions
- AUDIT-02: AI action recording columns (ai_input, ai_output, ai_model, etc.)
- AUDIT-06: fn_audit_log_immutable BEFORE trigger blocks UPDATE/DELETE
  (except pg_cron purge which sets app.audit_purge=true session variable)
- AUDIT-05: fn_purge_audit_log_expired SECURITY DEFINER function + daily pg_cron schedule
- workspaces.audit_retention_days column (default: 90 days, admin-configurable)

RLS policies:
  - INSERT: workspace members (is_deleted=false)
  - SELECT: OWNER/ADMIN roles only (UPPERCASE values)
  - service_role bypass for worker/admin operations

Immutability bypass for purge:
  - fn_audit_log_immutable checks current_setting('app.audit_purge', true) == 'true'
  - fn_purge_audit_log_expired sets app.audit_purge=true before DELETE, resets after
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "065_add_audit_log_table"
down_revision: str = "064_add_sso_rbac_session_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create audit_log table, immutability trigger, RLS, and pg_cron retention job."""

    # ------------------------------------------------------------------
    # Step 3a. CREATE TABLE audit_log
    # ------------------------------------------------------------------
    op.create_table(
        "audit_log",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Actor
        sa.Column(
            "actor_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("actor_type", sa.String(10), nullable=False),
        # Action
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column(
            "resource_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        # Payload diff: {"before": {...}, "after": {...}}
        sa.Column("payload", sa.dialects.postgresql.JSONB(), nullable=True),
        # AI-specific fields
        sa.Column("ai_input", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("ai_output", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("ai_model", sa.String(100), nullable=True),
        sa.Column("ai_token_cost", sa.Integer(), nullable=True),
        sa.Column("ai_rationale", sa.Text(), nullable=True),
        # Request context
        sa.Column("ip_address", sa.String(45), nullable=True),
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

    # Composite indexes for common query patterns
    op.create_index(
        "ix_audit_log_workspace_created",
        "audit_log",
        ["workspace_id", "created_at"],
    )
    op.create_index(
        "ix_audit_log_workspace_actor",
        "audit_log",
        ["workspace_id", "actor_id"],
    )
    op.create_index(
        "ix_audit_log_workspace_action",
        "audit_log",
        ["workspace_id", "action"],
    )
    op.create_index(
        "ix_audit_log_workspace_resource_type",
        "audit_log",
        ["workspace_id", "resource_type"],
    )

    # ------------------------------------------------------------------
    # Step 3b. CREATE FUNCTION fn_audit_log_immutable
    # Blocks UPDATE and DELETE. Allows bypass when app.audit_purge='true'
    # (set by the pg_cron retention function before its DELETE).
    # ------------------------------------------------------------------
    op.execute(
        text(
            """
            CREATE OR REPLACE FUNCTION fn_audit_log_immutable()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            BEGIN
                -- Allow bypass for the pg_cron purge function only.
                -- fn_purge_audit_log_expired sets this session variable before DELETE.
                IF current_setting('app.audit_purge', true) = 'true' THEN
                    RETURN OLD;
                END IF;

                RAISE EXCEPTION
                    'audit_log rows are immutable — UPDATE and DELETE are not permitted. '
                    'Action: %, Actor: %, Resource: %',
                    OLD.action,
                    OLD.actor_type,
                    OLD.resource_type;
            END;
            $$;
            """
        )
    )

    # ------------------------------------------------------------------
    # Step 3c. CREATE TRIGGER trg_audit_log_immutable
    # Must be created AFTER both table and function exist.
    # ------------------------------------------------------------------
    op.execute(
        text(
            """
            CREATE TRIGGER trg_audit_log_immutable
            BEFORE UPDATE OR DELETE ON audit_log
            FOR EACH ROW EXECUTE FUNCTION fn_audit_log_immutable();
            """
        )
    )

    # ------------------------------------------------------------------
    # Step 3d. RLS — ENABLE and FORCE
    # ------------------------------------------------------------------
    op.execute(text("ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY"))
    op.execute(text("ALTER TABLE audit_log FORCE ROW LEVEL SECURITY"))

    # ------------------------------------------------------------------
    # Step 3e. INSERT policy — workspace members (is_deleted=false)
    # ------------------------------------------------------------------
    op.execute(
        text(
            """
            CREATE POLICY "audit_log_insert_workspace_member"
            ON audit_log
            FOR INSERT
            TO authenticated
            WITH CHECK (
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

    # ------------------------------------------------------------------
    # Step 3f. SELECT policy — OWNER/ADMIN only (UPPERCASE values)
    # ------------------------------------------------------------------
    op.execute(
        text(
            """
            CREATE POLICY "audit_log_select_admin_owner"
            ON audit_log
            FOR SELECT
            TO authenticated
            USING (
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

    # ------------------------------------------------------------------
    # Step 3g. Service role bypass
    # ------------------------------------------------------------------
    op.execute(
        text(
            """
            CREATE POLICY "audit_log_service_role"
            ON audit_log
            FOR ALL
            TO service_role
            USING (true)
            WITH CHECK (true)
            """
        )
    )

    # ------------------------------------------------------------------
    # Step 3h. ADD audit_retention_days to workspaces
    # Default 90 days; admin-configurable via API.
    # ------------------------------------------------------------------
    op.add_column(
        "workspaces",
        sa.Column(
            "audit_retention_days",
            sa.Integer(),
            server_default=text("90"),
            nullable=True,
        ),
    )

    # ------------------------------------------------------------------
    # Step 3i. CREATE FUNCTION fn_purge_audit_log_expired
    # SECURITY DEFINER — runs as the function owner (superuser), not caller.
    # Sets app.audit_purge=true to bypass immutability trigger, then resets.
    # ------------------------------------------------------------------
    op.execute(
        text(
            """
            CREATE OR REPLACE FUNCTION fn_purge_audit_log_expired()
            RETURNS void
            LANGUAGE plpgsql
            SECURITY DEFINER
            AS $$
            DECLARE
                deleted_count bigint;
            BEGIN
                -- Signal the immutability trigger that this DELETE is authorized.
                PERFORM set_config('app.audit_purge', 'true', true);

                DELETE FROM audit_log al
                USING workspaces w
                WHERE al.workspace_id = w.id
                  AND al.created_at < NOW() - (COALESCE(w.audit_retention_days, 90) * INTERVAL '1 day');

                GET DIAGNOSTICS deleted_count = ROW_COUNT;

                -- Reset the bypass flag.
                PERFORM set_config('app.audit_purge', 'false', true);

                RAISE NOTICE 'fn_purge_audit_log_expired: deleted % expired audit log rows', deleted_count;
            EXCEPTION
                WHEN OTHERS THEN
                    -- Always reset the bypass flag even on error.
                    PERFORM set_config('app.audit_purge', 'false', true);
                    RAISE;
            END;
            $$;
            """
        )
    )

    # ------------------------------------------------------------------
    # Step 3j. Schedule daily purge at 2am UTC via pg_cron
    # pg_cron is available as a Supabase native extension.
    # Catch all errors to handle environments where pg_cron is not installed.
    # ------------------------------------------------------------------
    op.execute(
        text(
            """
            DO $outer$
            BEGIN
                PERFORM cron.schedule(
                    'purge-audit-log',
                    '0 2 * * *',
                    'SELECT fn_purge_audit_log_expired()'
                );
            EXCEPTION
                WHEN OTHERS THEN
                    RAISE NOTICE 'pg_cron not available (%) — skipping cron.schedule for purge-audit-log', SQLERRM;
            END $outer$;
            """
        )
    )


def downgrade() -> None:
    """Reverse migration 065: remove cron job, functions, table, and workspaces column."""

    # ------------------------------------------------------------------
    # Unschedule pg_cron job (catch all errors — pg_cron may not be installed)
    # ------------------------------------------------------------------
    op.execute(
        text(
            """
            DO $outer$
            BEGIN
                PERFORM cron.unschedule('purge-audit-log');
            EXCEPTION
                WHEN OTHERS THEN
                    RAISE NOTICE 'pg_cron unschedule skipped (%)', SQLERRM;
            END $outer$;
            """
        )
    )

    # ------------------------------------------------------------------
    # Drop purge function
    # ------------------------------------------------------------------
    op.execute(text("DROP FUNCTION IF EXISTS fn_purge_audit_log_expired()"))

    # ------------------------------------------------------------------
    # Remove audit_retention_days from workspaces
    # ------------------------------------------------------------------
    op.drop_column("workspaces", "audit_retention_days")

    # ------------------------------------------------------------------
    # Drop RLS policies
    # ------------------------------------------------------------------
    op.execute(text('DROP POLICY IF EXISTS "audit_log_service_role" ON audit_log'))
    op.execute(text('DROP POLICY IF EXISTS "audit_log_select_admin_owner" ON audit_log'))
    op.execute(text('DROP POLICY IF EXISTS "audit_log_insert_workspace_member" ON audit_log'))

    # ------------------------------------------------------------------
    # Drop trigger (must come before function)
    # ------------------------------------------------------------------
    op.execute(text("DROP TRIGGER IF EXISTS trg_audit_log_immutable ON audit_log"))

    # ------------------------------------------------------------------
    # Drop immutability function
    # ------------------------------------------------------------------
    op.execute(text("DROP FUNCTION IF EXISTS fn_audit_log_immutable()"))

    # ------------------------------------------------------------------
    # Drop indexes and table
    # ------------------------------------------------------------------
    op.drop_index("ix_audit_log_workspace_resource_type", table_name="audit_log")
    op.drop_index("ix_audit_log_workspace_action", table_name="audit_log")
    op.drop_index("ix_audit_log_workspace_actor", table_name="audit_log")
    op.drop_index("ix_audit_log_workspace_created", table_name="audit_log")
    op.drop_table("audit_log")
