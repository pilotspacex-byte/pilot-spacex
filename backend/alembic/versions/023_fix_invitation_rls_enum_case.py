"""Fix RLS policy enum case for workspace_invitations.

Revision ID: 023_fix_invitation_rls_enum_case
Revises: 022_workspace_invitations
Create Date: 2026-02-04

The RLS policies in migration 022 used uppercase enum values ('OWNER', 'ADMIN')
but the workspace_role enum stores lowercase values ('owner', 'admin').
This mismatch causes RLS to silently block all access to workspace_invitations.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "023_fix_invitation_rls_enum_case"
down_revision: str | None = "022_workspace_invitations"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Drop and recreate RLS policies with correct lowercase enum values."""
    # Drop existing broken policies
    op.execute(
        'DROP POLICY IF EXISTS "workspace_invitation_isolation_select" ON workspace_invitations'
    )
    op.execute(
        'DROP POLICY IF EXISTS "workspace_invitation_isolation_modify" ON workspace_invitations'
    )

    # Recreate select policy with lowercase enum values
    op.execute("""
        CREATE POLICY "workspace_invitation_isolation_select"
        ON workspace_invitations
        FOR SELECT
        USING (
            workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                AND wm.role IN ('owner', 'admin')
                AND wm.is_deleted = false
            )
        )
    """)

    # Recreate modify policy with lowercase enum values
    op.execute("""
        CREATE POLICY "workspace_invitation_isolation_modify"
        ON workspace_invitations
        FOR ALL
        USING (
            workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                AND wm.role IN ('owner', 'admin')
                AND wm.is_deleted = false
            )
        )
        WITH CHECK (
            workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                AND wm.role IN ('owner', 'admin')
                AND wm.is_deleted = false
            )
        )
    """)


def downgrade() -> None:
    """Revert to original uppercase enum values (broken state)."""
    op.execute(
        'DROP POLICY IF EXISTS "workspace_invitation_isolation_select" ON workspace_invitations'
    )
    op.execute(
        'DROP POLICY IF EXISTS "workspace_invitation_isolation_modify" ON workspace_invitations'
    )

    op.execute("""
        CREATE POLICY "workspace_invitation_isolation_select"
        ON workspace_invitations
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
    """)

    op.execute("""
        CREATE POLICY "workspace_invitation_isolation_modify"
        ON workspace_invitations
        FOR ALL
        USING (
            workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                AND wm.role IN ('OWNER', 'ADMIN')
                AND wm.is_deleted = false
            )
        )
        WITH CHECK (
            workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                AND wm.role IN ('OWNER', 'ADMIN')
                AND wm.is_deleted = false
            )
        )
    """)
