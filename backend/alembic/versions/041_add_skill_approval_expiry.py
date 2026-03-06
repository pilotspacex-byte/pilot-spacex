"""Add pg_cron job for skill_executions approval expiry (T-070).

Revision ID: 041_add_skill_approval_expiry
Revises: 040_add_memory_engine
Create Date: 2026-02-19

Creates PostgreSQL function fn_expire_pending_skill_approvals() that marks
any skill_execution in pending_approval state older than 24 hours as 'expired'.

Scheduled via pg_cron to run every 30 minutes.

Feature 015: AI Workforce Platform — Sprint 2 (T-070)
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "041_add_skill_approval_expiry"
down_revision: str = "040_add_memory_engine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create skill approval expiry function and schedule cron job."""
    # Create the expiry function
    # Uses SECURITY DEFINER so it runs with owner privileges and can UPDATE
    # skill_executions regardless of RLS (internal cleanup function).
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_expire_pending_skill_approvals()
        RETURNS integer
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public
        AS $$
        DECLARE
            expired_count integer;
        BEGIN
            UPDATE skill_executions
            SET
                approval_status = 'expired',
                updated_at = NOW()
            WHERE
                approval_status = 'pending_approval'
                AND created_at < NOW() - INTERVAL '24 hours';

            GET DIAGNOSTICS expired_count = ROW_COUNT;

            RETURN expired_count;
        END;
        $$;
    """
    )

    # Schedule: run every 30 minutes to expire stale approvals
    # Supabase includes pg_cron — schedule runs as cron superuser
    # If pg_cron is not available, this is a no-op and the application-level
    # ApprovalService.expire_stale_requests() fallback handles expiry.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_extension
                WHERE extname = 'pg_cron'
            ) THEN
                -- Remove any existing schedule before creating new one
                PERFORM cron.unschedule('expire_pending_skill_approvals')
                WHERE EXISTS (
                    SELECT 1 FROM cron.job WHERE jobname = 'expire_pending_skill_approvals'
                );

                PERFORM cron.schedule(
                    'expire_pending_skill_approvals',
                    '*/30 * * * *',
                    $cron$SELECT fn_expire_pending_skill_approvals()$cron$
                );
            END IF;
        END;
        $$;
    """
    )


def downgrade() -> None:
    """Remove skill approval expiry cron job and function."""
    # Unschedule cron job if pg_cron is available
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_extension
                WHERE extname = 'pg_cron'
            ) THEN
                PERFORM cron.unschedule('expire_pending_skill_approvals')
                WHERE EXISTS (
                    SELECT 1 FROM cron.job WHERE jobname = 'expire_pending_skill_approvals'
                );
            END IF;
        END;
        $$;
    """
    )

    # Drop the function
    op.execute("DROP FUNCTION IF EXISTS fn_expire_pending_skill_approvals();")
