"""Add WITH CHECK clause to artifacts workspace isolation RLS policy.

The existing policy only has USING (controls SELECT/UPDATE/DELETE visibility)
but no WITH CHECK (controls INSERT/UPDATE new row values). Without WITH CHECK,
a user who can manipulate workspace_id in INSERT could write rows to any workspace.

Revision ID: 094_add_artifacts_rls_with_check
Revises: 093_fix_artifacts_rls_enum_case
Create Date: 2026-03-20
"""

from collections.abc import Sequence

from sqlalchemy import text

from alembic import op

revision: str = "094_add_artifacts_rls_with_check"
down_revision: str = "093_fix_artifacts_rls_enum_case"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop and recreate with both USING and WITH CHECK clauses
    op.execute(text('DROP POLICY IF EXISTS "artifacts_workspace_isolation" ON artifacts'))

    op.execute(
        text("""
        CREATE POLICY "artifacts_workspace_isolation"
        ON artifacts
        FOR ALL
        USING (
            workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                AND wm.is_deleted = false
                AND wm.role IN ('owner', 'admin', 'member', 'guest')
            )
        )
        WITH CHECK (
            workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                AND wm.is_deleted = false
                AND wm.role IN ('owner', 'admin', 'member', 'guest')
            )
        )
    """)
    )


def downgrade() -> None:
    # Revert to USING-only policy from migration 093
    op.execute(text('DROP POLICY IF EXISTS "artifacts_workspace_isolation" ON artifacts'))

    op.execute(
        text("""
        CREATE POLICY "artifacts_workspace_isolation"
        ON artifacts
        FOR ALL
        USING (
            workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                AND wm.is_deleted = false
                AND wm.role IN ('owner', 'admin', 'member', 'guest')
            )
        )
    """)
    )
