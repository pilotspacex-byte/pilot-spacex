"""RLS (Row-Level Security) helper functions.

Provides utilities for workspace isolation via PostgreSQL RLS policies.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import text

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


async def set_rls_context(
    session: AsyncSession,
    user_id: UUID,
    workspace_id: UUID | None = None,
) -> None:
    """Set RLS context variables for the current session.

    Sets PostgreSQL session variables that RLS policies use to filter data.
    Must be called at the start of each request that accesses workspace data.

    Args:
        session: The async database session.
        user_id: Current authenticated user ID.
        workspace_id: Optional workspace ID for scoped queries.
    """
    # Set user_id for RLS policies
    await session.execute(text(f"SET LOCAL app.current_user_id = '{user_id}'"))

    # Set workspace_id if provided
    if workspace_id:
        await session.execute(text(f"SET LOCAL app.current_workspace_id = '{workspace_id}'"))


async def clear_rls_context(session: AsyncSession) -> None:
    """Clear RLS context variables.

    Resets session variables to prevent data leakage between requests.
    Called automatically by the session cleanup.

    Args:
        session: The async database session.
    """
    await session.execute(text("RESET app.current_user_id"))
    await session.execute(text("RESET app.current_workspace_id"))


def get_workspace_rls_policy_sql(table_name: str) -> str:
    """Generate RLS policy SQL for workspace-scoped tables.

    Args:
        table_name: Name of the table.

    Returns:
        SQL statements to create RLS policy.
    """
    return f"""
-- Enable RLS on {table_name}
ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY;

-- Policy: Users can only see rows in workspaces they are members of
CREATE POLICY "{table_name}_workspace_isolation"
ON {table_name}
FOR ALL
USING (
    workspace_id IN (
        SELECT wm.workspace_id
        FROM workspace_members wm
        WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
        AND wm.is_deleted = false
    )
);

-- Policy: Service role bypasses RLS (for admin operations)
CREATE POLICY "{table_name}_service_role"
ON {table_name}
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);
"""


def get_user_rls_policy_sql() -> str:
    """Generate RLS policy SQL for users table.

    Users can see themselves and members of their workspaces.

    Returns:
        SQL statements to create RLS policy.
    """
    return """
-- Enable RLS on users
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE users FORCE ROW LEVEL SECURITY;

-- Policy: Users can see themselves
CREATE POLICY "users_self"
ON users
FOR SELECT
USING (
    id = current_setting('app.current_user_id', true)::uuid
);

-- Policy: Users can see members of their workspaces
CREATE POLICY "users_workspace_members"
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
);

-- Policy: Users can update themselves
CREATE POLICY "users_self_update"
ON users
FOR UPDATE
USING (
    id = current_setting('app.current_user_id', true)::uuid
)
WITH CHECK (
    id = current_setting('app.current_user_id', true)::uuid
);

-- Policy: Service role bypasses RLS
CREATE POLICY "users_service_role"
ON users
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);
"""


def get_workspace_members_rls_policy_sql() -> str:
    """Generate RLS policy SQL for workspace_members table.

    Members can see other members of workspaces they belong to.
    Only admins/owners can modify membership.

    Returns:
        SQL statements to create RLS policy.
    """
    return """
-- Enable RLS on workspace_members
ALTER TABLE workspace_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspace_members FORCE ROW LEVEL SECURITY;

-- Policy: Users can see members of their workspaces
CREATE POLICY "workspace_members_read"
ON workspace_members
FOR SELECT
USING (
    workspace_id IN (
        SELECT wm.workspace_id
        FROM workspace_members wm
        WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
        AND wm.is_deleted = false
    )
);

-- Policy: Admins/Owners can manage members
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
);

-- Policy: Service role bypasses RLS
CREATE POLICY "workspace_members_service_role"
ON workspace_members
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);
"""
