"""Fix Homepage Hub RLS policies for security compliance.

Revision ID: 034_fix_homepage_rls_policies
Revises: 033_fix_dismissals_nullable_and_constraints
Create Date: 2026-02-07

Fixes:
- SEC-C2: workspace_digests INSERT policy now requires workspace membership
  instead of just checking user is authenticated.
- SEC-C3: Adds UPDATE (admin-only) and DELETE (admin-only) policies on
  workspace_digests to prevent unauthorized mutations.
- ARCH-M5: Replaces current_setting('app.current_user_id') with auth.uid()
  to match project-standard RLS pattern.

Source: PR #9 Devil's Advocate Review
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "034_fix_homepage_rls_policies"
down_revision: str = "033_fix_dismissals_nullable_and_constraints"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Replace insecure RLS policies with auth.uid() standard."""
    # ── workspace_digests: drop and recreate all policies ───────────────

    # Drop old policies
    op.execute('DROP POLICY IF EXISTS "workspace_digests_service_insert" ON workspace_digests')
    op.execute('DROP POLICY IF EXISTS "workspace_digests_member_select" ON workspace_digests')

    # SEC-C2 + ARCH-M5: SELECT — workspace members only (using auth.uid())
    op.execute("""
        CREATE POLICY "workspace_digests_member_select"
        ON workspace_digests
        FOR SELECT
        USING (
            workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = auth.uid()
                AND wm.is_deleted = false
            )
        )
    """)

    # SEC-C2: INSERT — must be a member of the workspace
    op.execute("""
        CREATE POLICY "workspace_digests_member_insert"
        ON workspace_digests
        FOR INSERT
        WITH CHECK (
            workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = auth.uid()
                AND wm.is_deleted = false
            )
        )
    """)

    # SEC-C3: UPDATE — admin/owner only
    op.execute("""
        CREATE POLICY "workspace_digests_admin_update"
        ON workspace_digests
        FOR UPDATE
        USING (
            workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = auth.uid()
                AND wm.role IN ('admin', 'owner')
                AND wm.is_deleted = false
            )
        )
    """)

    # SEC-C3: DELETE — admin/owner only
    op.execute("""
        CREATE POLICY "workspace_digests_admin_delete"
        ON workspace_digests
        FOR DELETE
        USING (
            workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = auth.uid()
                AND wm.role IN ('admin', 'owner')
                AND wm.is_deleted = false
            )
        )
    """)

    # ── digest_dismissals: migrate to auth.uid() ──────────────────────

    # Drop old policies
    op.execute('DROP POLICY IF EXISTS "digest_dismissals_user_select" ON digest_dismissals')
    op.execute('DROP POLICY IF EXISTS "digest_dismissals_user_insert" ON digest_dismissals')
    op.execute('DROP POLICY IF EXISTS "digest_dismissals_user_delete" ON digest_dismissals')

    # Recreate with auth.uid()
    op.execute("""
        CREATE POLICY "digest_dismissals_user_select"
        ON digest_dismissals
        FOR SELECT
        USING (user_id = auth.uid())
    """)

    op.execute("""
        CREATE POLICY "digest_dismissals_user_insert"
        ON digest_dismissals
        FOR INSERT
        WITH CHECK (
            user_id = auth.uid()
            AND workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = auth.uid()
                AND wm.is_deleted = false
            )
        )
    """)

    op.execute("""
        CREATE POLICY "digest_dismissals_user_delete"
        ON digest_dismissals
        FOR DELETE
        USING (user_id = auth.uid())
    """)


def downgrade() -> None:
    """Revert to original policies."""
    # Drop new digest_dismissals policies
    op.execute('DROP POLICY IF EXISTS "digest_dismissals_user_delete" ON digest_dismissals')
    op.execute('DROP POLICY IF EXISTS "digest_dismissals_user_insert" ON digest_dismissals')
    op.execute('DROP POLICY IF EXISTS "digest_dismissals_user_select" ON digest_dismissals')

    # Drop new workspace_digests policies
    op.execute('DROP POLICY IF EXISTS "workspace_digests_admin_delete" ON workspace_digests')
    op.execute('DROP POLICY IF EXISTS "workspace_digests_admin_update" ON workspace_digests')
    op.execute('DROP POLICY IF EXISTS "workspace_digests_member_insert" ON workspace_digests')
    op.execute('DROP POLICY IF EXISTS "workspace_digests_member_select" ON workspace_digests')

    # Restore original policies (current_setting based)
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

    op.execute("""
        CREATE POLICY "workspace_digests_service_insert"
        ON workspace_digests
        FOR INSERT
        WITH CHECK (
            current_setting('app.current_user_id', true)::uuid IS NOT NULL
        )
    """)

    op.execute("""
        CREATE POLICY "digest_dismissals_user_select"
        ON digest_dismissals
        FOR SELECT
        USING (
            user_id = current_setting('app.current_user_id', true)::uuid
        )
    """)

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

    op.execute("""
        CREATE POLICY "digest_dismissals_user_delete"
        ON digest_dismissals
        FOR DELETE
        USING (
            user_id = current_setting('app.current_user_id', true)::uuid
        )
    """)
