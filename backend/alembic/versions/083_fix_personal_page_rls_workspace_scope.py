"""Fix personal page RLS policy to include workspace_id scope.

Revision ID: 083_fix_personal_page_rls_workspace_scope
Revises: 082_add_base_url_model_name_to_api_keys
Create Date: 2026-03-13

Changes:
- RLS: Replace notes_personal_page_policy to add workspace_id membership check.
  Without this, a user who belongs to multiple workspaces could access their
  personal pages in workspaces they have since been removed from.
"""

from sqlalchemy import text

from alembic import op

revision = "083_fix_personal_page_rls_workspace_scope"
down_revision = "082_add_base_url_model_name_to_api_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Replace personal page RLS policy with workspace-scoped version."""
    op.execute(
        text("""
        DROP POLICY IF EXISTS "notes_personal_page_policy" ON notes;

        CREATE POLICY "notes_personal_page_policy"
        ON notes
        FOR ALL
        USING (
            project_id IS NULL
            AND owner_id = current_setting('app.current_user_id', true)::uuid
            AND workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                  AND wm.is_deleted = false
            )
        )
        WITH CHECK (
            project_id IS NULL
            AND owner_id = current_setting('app.current_user_id', true)::uuid
            AND workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                  AND wm.is_deleted = false
            )
        );
        """)
    )


def downgrade() -> None:
    """Restore personal page RLS policy without workspace scope."""
    op.execute(
        text("""
        DROP POLICY IF EXISTS "notes_personal_page_policy" ON notes;

        CREATE POLICY "notes_personal_page_policy"
        ON notes
        FOR ALL
        USING (
            project_id IS NULL
            AND owner_id = current_setting('app.current_user_id', true)::uuid
        )
        WITH CHECK (
            project_id IS NULL
            AND owner_id = current_setting('app.current_user_id', true)::uuid
        );
        """)
    )
