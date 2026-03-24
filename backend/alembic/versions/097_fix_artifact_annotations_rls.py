"""Fix artifact_annotations RLS: add FORCE RLS, service_role bypass, fix role casing.

Fixes three issues in migration 096:
1. Missing FORCE ROW LEVEL SECURITY (table owners bypass RLS without it)
2. Missing service_role bypass policy (backend services need access)
3. Role enum casing: lowercase → UPPERCASE to match all other project RLS policies

Revision ID: 097_fix_artifact_annotations_rls
Revises: 096_create_artifact_annotations_table
Create Date: 2026-03-23
"""

from collections.abc import Sequence

from sqlalchemy import text

from alembic import op

revision: str = "097_fix_artifact_annotations_rls"
down_revision: tuple[str, str] = (
    "096_create_artifact_annotations_table",
    "096_add_note_chunk_node_type",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Add FORCE ROW LEVEL SECURITY (ensures table owner also respects RLS)
    op.execute(text("ALTER TABLE artifact_annotations FORCE ROW LEVEL SECURITY"))

    # 2. Add service_role bypass policy for backend service operations
    op.execute(
        text("""
        CREATE POLICY "artifact_annotations_service_role"
        ON artifact_annotations
        TO service_role
        USING (true)
        WITH CHECK (true)
    """)
    )

    # 3. Fix role enum casing: lowercase → UPPERCASE to match project convention.
    #    Drop and recreate the two workspace isolation policies with correct casing.

    # Fix SELECT policy
    op.execute(
        text(
            'DROP POLICY IF EXISTS "artifact_annotations_workspace_select" ON artifact_annotations'
        )
    )
    op.execute(
        text("""
        CREATE POLICY "artifact_annotations_workspace_select"
        ON artifact_annotations
        FOR SELECT
        USING (
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

    # Fix INSERT policy
    op.execute(
        text(
            'DROP POLICY IF EXISTS "artifact_annotations_workspace_insert" ON artifact_annotations'
        )
    )
    op.execute(
        text("""
        CREATE POLICY "artifact_annotations_workspace_insert"
        ON artifact_annotations
        FOR INSERT
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
    # Restore lowercase policies (revert to 096 state)
    op.execute(
        text(
            'DROP POLICY IF EXISTS "artifact_annotations_workspace_insert" ON artifact_annotations'
        )
    )
    op.execute(
        text("""
        CREATE POLICY "artifact_annotations_workspace_insert"
        ON artifact_annotations
        FOR INSERT
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

    op.execute(
        text(
            'DROP POLICY IF EXISTS "artifact_annotations_workspace_select" ON artifact_annotations'
        )
    )
    op.execute(
        text("""
        CREATE POLICY "artifact_annotations_workspace_select"
        ON artifact_annotations
        FOR SELECT
        USING (
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

    # Remove service_role bypass
    op.execute(
        text('DROP POLICY IF EXISTS "artifact_annotations_service_role" ON artifact_annotations')
    )

    # Remove FORCE (revert to just ENABLE from 096)
    op.execute(text("ALTER TABLE artifact_annotations NO FORCE ROW LEVEL SECURITY"))
