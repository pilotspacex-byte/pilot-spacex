"""Fix artifacts RLS policy enum case — lowercase to UPPERCASE.

Migration 094 recreated the artifacts_workspace_isolation policy with
lowercase role values ('owner', 'admin', ...) but the workspace_role
enum uses UPPERCASE ('OWNER', 'ADMIN', ...). This causes
InvalidTextRepresentation errors during fresh migration runs.

Revision ID: 097_fix_artifacts_rls_enum_case
Revises: 096_add_note_chunk_node_type
Create Date: 2026-03-23
"""

from collections.abc import Sequence

from sqlalchemy import text

from alembic import op

revision: str = "097_fix_artifacts_rls_enum_case"
down_revision: str = "096_add_note_chunk_node_type"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
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
        WITH CHECK (
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


def downgrade() -> None:
    # Revert to migration 094's version (lowercase, broken but matches that state)
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
