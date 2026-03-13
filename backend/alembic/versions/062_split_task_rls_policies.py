"""Split tasks RLS policy into per-operation policies.

Revision ID: 062_split_task_rls_policies
Revises: 061_add_pgmq_rpc_wrappers
Create Date: 2026-03-12

Migration 037 created a single ``tasks_workspace_isolation`` policy using
``FOR ALL``.  This grants every workspace member (including GUEST) the ability
to delete any task in the workspace — a privilege that should be restricted to
OWNER/ADMIN roles only.

This migration replaces the single blanket policy with four per-operation
policies:

  tasks_member_select  — any workspace member can read tasks
  tasks_member_insert  — any workspace member can create tasks
  tasks_member_update  — any workspace member can update tasks
  tasks_member_delete  — only OWNER/ADMIN may delete tasks
  tasks_service_role   — service_role bypass for background jobs / admin

The ``workspace_role`` enum stores UPPERCASE values: 'OWNER', 'ADMIN',
'MEMBER', 'GUEST'.

The ``tasks`` table has no ``created_by`` column (see migration 037), so the
delete policy uses a role-only gate instead of owner-or-creator semantics.
"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "062_split_task_rls_policies"
down_revision: str = "061_add_pgmq_rpc_wrappers"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Replace FOR ALL policy with four per-operation policies."""
    # 1. Remove the blanket policy created in migration 037.
    op.execute('DROP POLICY IF EXISTS "tasks_workspace_isolation" ON tasks')

    # 2. SELECT — any active workspace member may read tasks.
    op.execute("""
        CREATE POLICY "tasks_member_select"
        ON tasks
        FOR SELECT
        USING (
            EXISTS (
                SELECT 1 FROM workspace_members wm
                WHERE wm.workspace_id = tasks.workspace_id
                AND wm.user_id::text = current_setting('app.current_user_id', true)
                AND wm.is_deleted = false
            )
        )
    """)

    # 3. INSERT — any active workspace member may create tasks.
    op.execute("""
        CREATE POLICY "tasks_member_insert"
        ON tasks
        FOR INSERT
        WITH CHECK (
            EXISTS (
                SELECT 1 FROM workspace_members wm
                WHERE wm.workspace_id = tasks.workspace_id
                AND wm.user_id::text = current_setting('app.current_user_id', true)
                AND wm.is_deleted = false
            )
        )
    """)

    # 4. UPDATE — any active workspace member may update tasks (read + write
    #    check both require membership so a member cannot move a task to a
    #    workspace they do not belong to).
    op.execute("""
        CREATE POLICY "tasks_member_update"
        ON tasks
        FOR UPDATE
        USING (
            EXISTS (
                SELECT 1 FROM workspace_members wm
                WHERE wm.workspace_id = tasks.workspace_id
                AND wm.user_id::text = current_setting('app.current_user_id', true)
                AND wm.is_deleted = false
            )
        )
        WITH CHECK (
            EXISTS (
                SELECT 1 FROM workspace_members wm
                WHERE wm.workspace_id = tasks.workspace_id
                AND wm.user_id::text = current_setting('app.current_user_id', true)
                AND wm.is_deleted = false
            )
        )
    """)

    # 5. DELETE — restricted to OWNER or ADMIN only.
    #    The tasks table has no created_by column (migration 037), so
    #    owner-or-creator semantics are not applicable here.
    op.execute("""
        CREATE POLICY "tasks_member_delete"
        ON tasks
        FOR DELETE
        USING (
            EXISTS (
                SELECT 1 FROM workspace_members wm
                WHERE wm.workspace_id = tasks.workspace_id
                AND wm.user_id::text = current_setting('app.current_user_id', true)
                AND wm.is_deleted = false
                AND wm.role IN ('OWNER', 'ADMIN')
            )
        )
    """)

    # 6. Service-role bypass so background jobs and admin tooling are not
    #    blocked by RLS.
    op.execute("""
        CREATE POLICY "tasks_service_role"
        ON tasks
        FOR ALL
        TO service_role
        USING (true)
        WITH CHECK (true)
    """)


def downgrade() -> None:
    """Drop per-operation policies and restore the original FOR ALL policy."""
    op.execute('DROP POLICY IF EXISTS "tasks_service_role" ON tasks')
    op.execute('DROP POLICY IF EXISTS "tasks_member_delete" ON tasks')
    op.execute('DROP POLICY IF EXISTS "tasks_member_update" ON tasks')
    op.execute('DROP POLICY IF EXISTS "tasks_member_insert" ON tasks')
    op.execute('DROP POLICY IF EXISTS "tasks_member_select" ON tasks')

    # Restore the original blanket policy from migration 037.
    op.execute("""
        CREATE POLICY "tasks_workspace_isolation"
        ON tasks FOR ALL
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
