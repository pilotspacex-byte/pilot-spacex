"""Create RLS policies for workspace isolation.

Revision ID: 004_rls_policies
Revises: 003_project_entities
Create Date: 2026-01-23

Enables Row-Level Security (RLS) for multi-tenant data isolation.
All workspace-scoped tables are protected by RLS policies.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004_rls_policies"
down_revision: str | None = "003_project_entities"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Create RLS policies for all tables."""
    # Users table RLS
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE users FORCE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY "users_self_select"
        ON users
        FOR SELECT
        USING (
            id = current_setting('app.current_user_id', true)::uuid
        )
    """)

    op.execute("""
        CREATE POLICY "users_workspace_members_select"
        ON users
        FOR SELECT
        USING (
            id IN (
                SELECT wm.user_id
                FROM workspace_members wm
                WHERE wm.workspace_id IN (
                    SELECT wm2.workspace_id
                    FROM workspace_members wm2
                    WHERE wm2.user_id = current_setting('app.current_user_id', true)::uuid
                    AND wm2.is_deleted = false
                )
                AND wm.is_deleted = false
            )
        )
    """)

    op.execute("""
        CREATE POLICY "users_self_update"
        ON users
        FOR UPDATE
        USING (id = current_setting('app.current_user_id', true)::uuid)
        WITH CHECK (id = current_setting('app.current_user_id', true)::uuid)
    """)

    # Workspaces table RLS
    op.execute("ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE workspaces FORCE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY "workspaces_member_select"
        ON workspaces
        FOR SELECT
        USING (
            id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                AND wm.is_deleted = false
            )
        )
    """)

    op.execute("""
        CREATE POLICY "workspaces_owner_update"
        ON workspaces
        FOR UPDATE
        USING (
            id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                AND wm.role = 'OWNER'
                AND wm.is_deleted = false
            )
        )
    """)

    op.execute("""
        CREATE POLICY "workspaces_insert"
        ON workspaces
        FOR INSERT
        WITH CHECK (
            current_setting('app.current_user_id', true)::uuid IS NOT NULL
        )
    """)

    # Workspace members table RLS
    op.execute("ALTER TABLE workspace_members ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE workspace_members FORCE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY "workspace_members_select"
        ON workspace_members
        FOR SELECT
        USING (
            workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                AND wm.is_deleted = false
            )
        )
    """)

    op.execute("""
        CREATE POLICY "workspace_members_admin"
        ON workspace_members
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

    # Projects table RLS
    op.execute("ALTER TABLE projects ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE projects FORCE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY "projects_workspace_member"
        ON projects
        FOR ALL
        USING (
            workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                AND wm.is_deleted = false
            )
        )
        WITH CHECK (
            workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                AND wm.is_deleted = false
            )
        )
    """)

    # States table RLS
    op.execute("ALTER TABLE states ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE states FORCE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY "states_workspace_member"
        ON states
        FOR ALL
        USING (
            workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                AND wm.is_deleted = false
            )
        )
        WITH CHECK (
            workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                AND wm.is_deleted = false
            )
        )
    """)

    # Labels table RLS
    op.execute("ALTER TABLE labels ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE labels FORCE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY "labels_workspace_member"
        ON labels
        FOR ALL
        USING (
            workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                AND wm.is_deleted = false
            )
        )
        WITH CHECK (
            workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                AND wm.is_deleted = false
            )
        )
    """)

    # Modules table RLS
    op.execute("ALTER TABLE modules ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE modules FORCE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY "modules_workspace_member"
        ON modules
        FOR ALL
        USING (
            workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                AND wm.is_deleted = false
            )
        )
        WITH CHECK (
            workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                AND wm.is_deleted = false
            )
        )
    """)


def downgrade() -> None:
    """Drop RLS policies from all tables."""
    tables = ["modules", "labels", "states", "projects", "workspace_members", "workspaces", "users"]

    for table in tables:
        op.execute(f'DROP POLICY IF EXISTS "{table}_workspace_member" ON {table}')
        op.execute(f'DROP POLICY IF EXISTS "{table}_member_select" ON {table}')
        op.execute(f'DROP POLICY IF EXISTS "{table}_owner_update" ON {table}')
        op.execute(f'DROP POLICY IF EXISTS "{table}_insert" ON {table}')
        op.execute(f'DROP POLICY IF EXISTS "{table}_select" ON {table}')
        op.execute(f'DROP POLICY IF EXISTS "{table}_admin" ON {table}')
        op.execute(f'DROP POLICY IF EXISTS "{table}_self_select" ON {table}')
        op.execute(f'DROP POLICY IF EXISTS "{table}_workspace_members_select" ON {table}')
        op.execute(f'DROP POLICY IF EXISTS "{table}_self_update" ON {table}')
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
