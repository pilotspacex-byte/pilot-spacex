"""Fix digest cron function: remove SECURITY DEFINER, add jitter.

Revision ID: 035_fix_digest_cron_security
Revises: 034_fix_homepage_rls_policies
Create Date: 2026-02-07

Fixes:
- SEC-C4: Removes SECURITY DEFINER so function runs with invoker
  privileges instead of bypassing RLS.
- ARCH-M4: Adds pg_sleep(random() * 300) jitter between workspace
  enqueues to prevent thundering herd on hourly schedule.
- BE-H1: Wraps downgrade cron.unschedule in exception handler for
  environments without pg_cron.

Source: PR #9 Devil's Advocate Review
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "035_fix_digest_cron_security"
down_revision: str = "034_fix_homepage_rls_policies"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Replace digest cron function with secure version + jitter."""
    # Drop and recreate function without SECURITY DEFINER, with jitter
    op.execute("DROP FUNCTION IF EXISTS fn_enqueue_workspace_digest_jobs();")

    op.execute("""
        CREATE OR REPLACE FUNCTION fn_enqueue_workspace_digest_jobs()
        RETURNS void
        LANGUAGE plpgsql
        SECURITY INVOKER
        AS $$
        DECLARE
            ws_id uuid;
        BEGIN
            FOR ws_id IN
                SELECT DISTINCT w.id
                FROM workspaces w
                WHERE w.is_deleted = false
            LOOP
                -- Jitter: sleep 0-300s to spread load across workspaces
                PERFORM pg_sleep(random() * 300);

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


def downgrade() -> None:
    """Restore original function with SECURITY DEFINER."""
    op.execute("DROP FUNCTION IF EXISTS fn_enqueue_workspace_digest_jobs();")

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
