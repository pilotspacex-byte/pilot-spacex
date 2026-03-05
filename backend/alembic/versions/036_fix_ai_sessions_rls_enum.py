"""Fix ai_sessions RLS policy enum case and add session_data GIN index.

Recreate ai_sessions_admin_select policy with correct UPPERCASE enum values
matching the workspace_role enum type (OWNER, ADMIN, MEMBER, GUEST).
Also adds a GIN index on session_data for JSONB search performance
(context_history lookups).

Revision ID: 036_fix_ai_sessions_rls_enum
Revises: 035_fix_digest_cron_security
Create Date: 2026-02-11
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "036_fix_ai_sessions_rls_enum"
down_revision = "035_fix_digest_cron_security"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Fix RLS enum case and add GIN index."""
    # Drop the broken policy with UPPERCASE enum values
    op.execute('DROP POLICY IF EXISTS "ai_sessions_admin_select" ON ai_sessions')

    # Recreate with correct UPPERCASE enum values matching workspace_role type
    op.execute(
        """
        CREATE POLICY "ai_sessions_admin_select"
        ON ai_sessions
        FOR SELECT
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

    # Add GIN index on session_data for JSONB search performance
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_ai_sessions_session_data_gin
        ON ai_sessions USING gin (session_data)
    """
    )


def downgrade() -> None:
    """Revert RLS policy to uppercase and drop GIN index."""
    op.execute("DROP INDEX IF EXISTS ix_ai_sessions_session_data_gin")

    op.execute('DROP POLICY IF EXISTS "ai_sessions_admin_select" ON ai_sessions')

    # Restore original policy (same UPPERCASE values, no functional change in downgrade)
    op.execute(
        """
        CREATE POLICY "ai_sessions_admin_select"
        ON ai_sessions
        FOR SELECT
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
