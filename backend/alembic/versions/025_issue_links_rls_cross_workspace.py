"""Add WITH CHECK to issue_links RLS policy for cross-workspace validation.

Revision ID: 025_issue_links_rls
Revises: 024_enhanced_mcp_models
Create Date: 2026-02-06

The original policy only checks workspace membership for SELECT.
This revision adds a WITH CHECK clause for INSERT/UPDATE that verifies
both source_issue and target_issue belong to the same workspace_id,
preventing cross-workspace issue linking even if application logic is bypassed.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "025_issue_links_rls"
down_revision: str = "024_enhanced_mcp_models"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Replace issue_links RLS policy with cross-workspace validation."""
    # Drop the existing permissive policy
    op.execute(
        'DROP POLICY IF EXISTS "issue_links_workspace_member" ON issue_links'
    )

    # Recreate with separate SELECT (USING) and INSERT/UPDATE (WITH CHECK) clauses.
    # SELECT: user must be member of the link's workspace.
    # INSERT/UPDATE: additionally verify both issues belong to the link's workspace.
    op.execute("""
        CREATE POLICY "issue_links_workspace_member_select"
        ON issue_links
        FOR SELECT
        USING (
            workspace_id IN (
                SELECT wm.workspace_id FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
            )
        );
    """)

    op.execute("""
        CREATE POLICY "issue_links_workspace_member_mutate"
        ON issue_links
        FOR ALL
        USING (
            workspace_id IN (
                SELECT wm.workspace_id FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
            )
        )
        WITH CHECK (
            workspace_id IN (
                SELECT wm.workspace_id FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
            )
            AND EXISTS (
                SELECT 1 FROM issues
                WHERE issues.id = source_issue_id
                  AND issues.workspace_id = issue_links.workspace_id
            )
            AND EXISTS (
                SELECT 1 FROM issues
                WHERE issues.id = target_issue_id
                  AND issues.workspace_id = issue_links.workspace_id
            )
        );
    """)


def downgrade() -> None:
    """Revert to the original simpler RLS policy."""
    op.execute(
        'DROP POLICY IF EXISTS "issue_links_workspace_member_select" ON issue_links'
    )
    op.execute(
        'DROP POLICY IF EXISTS "issue_links_workspace_member_mutate" ON issue_links'
    )

    op.execute("""
        CREATE POLICY "issue_links_workspace_member"
        ON issue_links
        FOR ALL
        USING (
            workspace_id IN (
                SELECT wm.workspace_id FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
            )
        );
    """)
