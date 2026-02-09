"""Add pg_cron scheduled job for hourly digest generation.

Revision ID: 032_digest_cron_job
Revises: 031_homepage_rls
Create Date: 2026-02-07

Creates a PostgreSQL function and pg_cron schedule that enqueues
workspace digest generation jobs every hour to the ai_low queue.

Source: specs/012-homepage-note, plan.md Phase 2 (H024)
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "032_digest_cron_job"
down_revision: str = "031_homepage_rls"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create digest cron function and schedule hourly job."""
    # Ensure pg_cron extension is available (Supabase includes it)
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_cron WITH SCHEMA pg_catalog;")

    # Create function that enqueues digest jobs for all active workspaces
    op.execute("""
        CREATE OR REPLACE FUNCTION fn_enqueue_workspace_digest_jobs()
        RETURNS void
        LANGUAGE plpgsql
        SECURITY DEFINER
        AS $$
        DECLARE
            ws_id uuid;
        BEGIN
            FOR ws_id IN
                SELECT DISTINCT w.id
                FROM workspaces w
                WHERE w.is_deleted = false
            LOOP
                PERFORM pgmq.send(
                    'ai_low',
                    jsonb_build_object(
                        'task_type', 'generate_workspace_digest',
                        'workspace_id', ws_id::text,
                        'trigger', 'scheduled'
                    )
                );
            END LOOP;
        END;
        $$;
    """)

    # Schedule hourly execution (at minute 0 of every hour)
    op.execute("""
        SELECT cron.schedule(
            'hourly_workspace_digests',
            '0 * * * *',
            'SELECT fn_enqueue_workspace_digest_jobs()'
        );
    """)


def downgrade() -> None:
    """Remove digest cron job and function."""
    # Unschedule the cron job (wrapped in exception handler for envs without pg_cron)
    op.execute("""
        DO $$
        BEGIN
            PERFORM cron.unschedule('hourly_workspace_digests');
        EXCEPTION WHEN undefined_table OR undefined_function THEN
            -- pg_cron not available, nothing to unschedule
            NULL;
        END $$;
    """)

    # Drop the function
    op.execute("DROP FUNCTION IF EXISTS fn_enqueue_workspace_digest_jobs();")
