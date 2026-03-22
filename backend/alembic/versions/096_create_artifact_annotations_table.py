"""Create artifact_annotations table with RLS policies.

Merges the two existing heads (095_add_transcript_cache_rls and
095_add_workspace_members_rls_index) into a single head.

RLS policies:
- artifact_annotations_workspace_isolation: workspace members can read/write their workspace's rows
- artifact_annotations_author_modify: only annotation author can update/delete

Revision ID: 096_create_artifact_annotations_table
Revises: 095_add_transcript_cache_rls, 095_add_workspace_members_rls_index
Create Date: 2026-03-22
"""

from collections.abc import Sequence

from sqlalchemy import text

from alembic import op

revision: str = "096_create_artifact_annotations_table"
down_revision: tuple[str, str] = (
    "095_add_transcript_cache_rls",
    "095_add_workspace_members_rls_index",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create artifact_annotations table
    op.execute(
        text("""
        CREATE TABLE artifact_annotations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            artifact_id UUID NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,
            slide_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            is_deleted BOOLEAN NOT NULL DEFAULT false,
            deleted_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    )

    # Create composite index for efficient per-slide queries
    op.execute(
        text("""
        CREATE INDEX ix_artifact_annotations_artifact_slide
        ON artifact_annotations (artifact_id, slide_index)
    """)
    )

    # Create workspace_id index for RLS and workspace-scoped queries
    op.execute(
        text("""
        CREATE INDEX ix_artifact_annotations_workspace_id
        ON artifact_annotations (workspace_id)
    """)
    )

    # Enable Row Level Security
    op.execute(text("ALTER TABLE artifact_annotations ENABLE ROW LEVEL SECURITY"))

    # Workspace isolation policy (ALL operations) — workspace members with lowercase roles
    op.execute(
        text("""
        CREATE POLICY "artifact_annotations_workspace_isolation"
        ON artifact_annotations
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

    # Author-only modify policy (UPDATE/DELETE) — only the annotation creator can modify/delete
    op.execute(
        text("""
        CREATE POLICY "artifact_annotations_author_modify"
        ON artifact_annotations
        FOR ALL
        USING (user_id = current_setting('app.current_user_id', true)::uuid)
        WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid)
    """)
    )


def downgrade() -> None:
    op.execute(
        text('DROP POLICY IF EXISTS "artifact_annotations_author_modify" ON artifact_annotations')
    )
    op.execute(
        text(
            'DROP POLICY IF EXISTS "artifact_annotations_workspace_isolation" ON artifact_annotations'
        )
    )
    op.execute(text("DROP TABLE IF EXISTS artifact_annotations"))
