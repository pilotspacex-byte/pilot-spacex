"""Add RLS policies to artifacts table.

Security: Enables Row-Level Security on the artifacts table and creates
workspace isolation + service-role bypass policies. Required for multi-tenant
data isolation — artifacts must only be visible to workspace members.

Revision ID: 092_add_artifacts_rls_policies
Revises: 091_add_artifacts_table
Create Date: 2026-03-20
"""

from collections.abc import Sequence

from sqlalchemy import text

from alembic import op

revision: str = "092_add_artifacts_rls_policies"
down_revision: str = "091_add_artifacts_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Enable and force RLS on the artifacts table
    op.execute(text("ALTER TABLE artifacts ENABLE ROW LEVEL SECURITY"))
    op.execute(text("ALTER TABLE artifacts FORCE ROW LEVEL SECURITY"))

    # Workspace isolation policy: only workspace members can access artifacts
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

    # Service-role bypass policy for backend operations
    op.execute(
        text("""
        CREATE POLICY "artifacts_service_role"
        ON artifacts
        FOR ALL
        TO service_role
        USING (true)
    """)
    )


def downgrade() -> None:
    op.execute(text('DROP POLICY IF EXISTS "artifacts_service_role" ON artifacts'))
    op.execute(text('DROP POLICY IF EXISTS "artifacts_workspace_isolation" ON artifacts'))
    op.execute(text("ALTER TABLE artifacts DISABLE ROW LEVEL SECURITY"))
