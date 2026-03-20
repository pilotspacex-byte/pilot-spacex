"""Fix artifacts RLS policy enum case — lowercase to match DB values.

Known bug: workspace_role enum stores lowercase ('owner', 'admin', 'member',
'guest') but migration 092 used UPPERCASE in the RLS policy, making all
artifact rows invisible to authenticated users. This migration drops and
recreates the workspace isolation policy with correct lowercase values.

See also: migrations 023 and 066 which fixed the same enum case issue on
other tables.

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
    # Drop the policy with incorrect UPPERCASE enum values
    op.execute(text('DROP POLICY IF EXISTS "artifacts_workspace_isolation" ON artifacts'))

    # Recreate with correct lowercase enum values matching DB storage
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


def downgrade() -> None:
    # Revert to the original UPPERCASE policy from migration 091
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
