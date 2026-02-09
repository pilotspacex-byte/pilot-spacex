"""Add RLS policies for Homepage Hub tables.

Revision ID: 031_homepage_rls_policies
Revises: 030_add_notes_source_chat
Create Date: 2026-02-07

Enables Row-Level Security on workspace_digests and digest_dismissals:

workspace_digests:
  - SELECT: workspace members can read their workspace digests
  - INSERT: authenticated users (service role) can insert

digest_dismissals:
  - SELECT: users can read own dismissals
  - INSERT: users can create own dismissals (with workspace membership)
  - DELETE: users can delete own dismissals

Source: specs/012-homepage-note, plan.md Phase 0 (H004)
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "031_homepage_rls"
down_revision: str = "030_add_notes_source_chat"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Enable RLS and create policies for homepage tables."""
    # ── workspace_digests ──────────────────────────────────────────────
    op.execute("ALTER TABLE workspace_digests ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE workspace_digests FORCE ROW LEVEL SECURITY")

    # Members of the workspace can read digests
    op.execute("""
        CREATE POLICY "workspace_digests_member_select"
        ON workspace_digests
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

    # Service role (background jobs) can insert digests
    op.execute("""
        CREATE POLICY "workspace_digests_service_insert"
        ON workspace_digests
        FOR INSERT
        WITH CHECK (
            current_setting('app.current_user_id', true)::uuid IS NOT NULL
        )
    """)

    # ── digest_dismissals ──────────────────────────────────────────────
    op.execute("ALTER TABLE digest_dismissals ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE digest_dismissals FORCE ROW LEVEL SECURITY")

    # Users can read their own dismissals
    op.execute("""
        CREATE POLICY "digest_dismissals_user_select"
        ON digest_dismissals
        FOR SELECT
        USING (
            user_id = current_setting('app.current_user_id', true)::uuid
        )
    """)

    # Users can insert dismissals for themselves (must be workspace member)
    op.execute("""
        CREATE POLICY "digest_dismissals_user_insert"
        ON digest_dismissals
        FOR INSERT
        WITH CHECK (
            user_id = current_setting('app.current_user_id', true)::uuid
            AND workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                AND wm.is_deleted = false
            )
        )
    """)

    # Users can delete their own dismissals
    op.execute("""
        CREATE POLICY "digest_dismissals_user_delete"
        ON digest_dismissals
        FOR DELETE
        USING (
            user_id = current_setting('app.current_user_id', true)::uuid
        )
    """)


def downgrade() -> None:
    """Drop RLS policies and disable RLS on homepage tables."""
    # digest_dismissals policies
    op.execute('DROP POLICY IF EXISTS "digest_dismissals_user_delete" ON digest_dismissals')
    op.execute('DROP POLICY IF EXISTS "digest_dismissals_user_insert" ON digest_dismissals')
    op.execute('DROP POLICY IF EXISTS "digest_dismissals_user_select" ON digest_dismissals')
    op.execute("ALTER TABLE digest_dismissals DISABLE ROW LEVEL SECURITY")

    # workspace_digests policies
    op.execute('DROP POLICY IF EXISTS "workspace_digests_service_insert" ON workspace_digests')
    op.execute('DROP POLICY IF EXISTS "workspace_digests_member_select" ON workspace_digests')
    op.execute("ALTER TABLE workspace_digests DISABLE ROW LEVEL SECURITY")
