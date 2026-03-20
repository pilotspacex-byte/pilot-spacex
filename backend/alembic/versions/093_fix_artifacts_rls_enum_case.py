"""Remove redundant role IN filter from artifacts RLS policy.

Migration 092 included an unnecessary `wm.role IN (...)` filter in the
workspace isolation policy — membership in workspace_members is sufficient,
the role check adds no security value and caused enum case confusion.

Revision ID: 093_fix_artifacts_rls_enum_case
Revises: 092_add_artifacts_rls_policies
Create Date: 2026-03-20
"""

from collections.abc import Sequence

from sqlalchemy import text

from alembic import op

revision: str = "093_fix_artifacts_rls_enum_case"
down_revision: str = "092_add_artifacts_rls_policies"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop the policy with the redundant role IN filter
    op.execute(text('DROP POLICY IF EXISTS "artifacts_workspace_isolation" ON artifacts'))

    # Recreate without the role filter — membership is the only check needed
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
            )
        )
    """)
    )


def downgrade() -> None:
    # Revert to the original policy from migration 092
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
                AND wm.role IN ('OWNER', 'ADMIN', 'MEMBER', 'GUEST')
            )
        )
    """)
    )
