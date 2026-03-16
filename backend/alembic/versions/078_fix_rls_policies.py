"""Fix RLS policy scoping and missing indexes on new tables.

Revision ID: 078_fix_rls_policies
Revises: 077_add_skill_templates
Create Date: 2026-03-12

Fixes:
- H-3: Add missing index on workspace_mcp_servers.workspace_id
- H-5: Drop and recreate workspace isolation policies without
  'TO authenticated' scope on tables 073-075, 077. The application
  connects via SQLAlchemy (not Supabase PostgREST), so the
  'authenticated' role scope does not apply. Aligns with the
  canonical get_workspace_rls_policy_sql() template in rls.py.
- M-4: Add UNIQUE constraint on workspace_github_credentials.workspace_id
"""

from alembic import op
from sqlalchemy import text

revision = "078_fix_rls_policies"
down_revision = "077_add_skill_templates"
branch_labels = None
depends_on = None

# Tables whose workspace_isolation policy needs TO authenticated removed
_TABLES_TO_FIX = [
    "workspace_role_skills",
    "workspace_plugins",
    "workspace_github_credentials",
    "skill_action_buttons",
    "skill_templates",
    "user_skills",
]


def upgrade() -> None:
    """Fix RLS policies and add missing indexes."""
    # H-3: Index on workspace_mcp_servers.workspace_id
    # Already created in 071_add_workspace_mcp_servers — use IF NOT EXISTS
    op.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_workspace_mcp_servers_workspace_id "
            "ON workspace_mcp_servers (workspace_id)"
        )
    )

    # M-4: Add UNIQUE constraint on workspace_github_credentials.workspace_id
    op.create_unique_constraint(
        "uq_workspace_github_credentials_workspace",
        "workspace_github_credentials",
        ["workspace_id"],
    )

    # H-5: Replace TO authenticated policies with unscoped versions
    for table in _TABLES_TO_FIX:
        policy_name = f"{table}_workspace_isolation"
        op.execute(text(f'DROP POLICY IF EXISTS "{policy_name}" ON {table}'))
        op.execute(
            text(
                f"""
            CREATE POLICY "{policy_name}"
            ON {table}
            FOR ALL
            USING (
                workspace_id IN (
                    SELECT wm.workspace_id
                    FROM workspace_members wm
                    WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                    AND wm.is_deleted = false
                )
            )
        """
            )
        )


def downgrade() -> None:
    """Revert RLS policy changes and indexes."""
    # Revert H-5: Restore TO authenticated scope
    for table in _TABLES_TO_FIX:
        policy_name = f"{table}_workspace_isolation"
        op.execute(text(f'DROP POLICY IF EXISTS "{policy_name}" ON {table}'))
        op.execute(
            text(
                f"""
            CREATE POLICY "{policy_name}"
            ON {table}
            FOR ALL
            TO authenticated
            USING (
                workspace_id IN (
                    SELECT wm.workspace_id
                    FROM workspace_members wm
                    WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                    AND wm.is_deleted = false
                )
            )
        """
            )
        )

    # Revert M-4
    op.drop_constraint(
        "uq_workspace_github_credentials_workspace",
        "workspace_github_credentials",
        type_="unique",
    )

    # Revert H-3
    op.drop_index("ix_workspace_mcp_servers_workspace_id", "workspace_mcp_servers")
