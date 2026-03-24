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
down_revision: str = "22403cf6e40a"  # pragma: allowlist secret
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add unique index on artifacts(id, workspace_id) to support composite FK
    # from artifact_annotations — enforces workspace tenancy at DB level.
    op.execute(
        text("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_artifacts_id_workspace
        ON artifacts (id, workspace_id)
    """)
    )

    # Create artifact_annotations table with composite FK tying workspace_id to artifact
    op.execute(
        text("""
        CREATE TABLE artifact_annotations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            artifact_id UUID NOT NULL,
            slide_index INTEGER NOT NULL CHECK (slide_index >= 0),
            content TEXT NOT NULL,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            workspace_id UUID NOT NULL,
            is_deleted BOOLEAN NOT NULL DEFAULT false,
            deleted_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT fk_annotation_artifact_workspace
                FOREIGN KEY (artifact_id, workspace_id)
                REFERENCES artifacts(id, workspace_id) ON DELETE CASCADE
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

    # Workspace isolation — SELECT: workspace members can read all annotations
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

    # Workspace isolation — INSERT: workspace members can create annotations.
    # Prevents user_id spoofing (must match session user) and ties workspace_id
    # to the referenced artifact's workspace.
    op.execute(
        text("""
        CREATE POLICY "artifact_annotations_workspace_insert"
        ON artifact_annotations
        FOR INSERT
        WITH CHECK (
            user_id = current_setting('app.current_user_id', true)::uuid
            AND workspace_id IN (
                SELECT a.workspace_id
                FROM artifacts a
                WHERE a.id = artifact_id
            )
            AND workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                AND wm.is_deleted = false
                AND wm.role IN ('OWNER', 'ADMIN', 'MEMBER', 'GUEST')
            )
        )
    """)
    )

    # Author-only UPDATE — only the annotation creator can modify, scoped to workspace
    op.execute(
        text("""
        CREATE POLICY "artifact_annotations_author_update"
        ON artifact_annotations
        FOR UPDATE
        USING (
            user_id = current_setting('app.current_user_id', true)::uuid
            AND workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                AND wm.is_deleted = false
            )
        )
        WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid)
    """)
    )

    # Author-only DELETE — only the annotation creator can delete, scoped to workspace
    op.execute(
        text("""
        CREATE POLICY "artifact_annotations_author_delete"
        ON artifact_annotations
        FOR DELETE
        USING (
            user_id = current_setting('app.current_user_id', true)::uuid
            AND workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                AND wm.is_deleted = false
            )
        )
    """)
    )


def downgrade() -> None:
    op.execute(
        text('DROP POLICY IF EXISTS "artifact_annotations_author_delete" ON artifact_annotations')
    )
    op.execute(
        text('DROP POLICY IF EXISTS "artifact_annotations_author_update" ON artifact_annotations')
    )
    op.execute(
        text(
            'DROP POLICY IF EXISTS "artifact_annotations_workspace_insert" ON artifact_annotations'
        )
    )
    op.execute(
        text(
            'DROP POLICY IF EXISTS "artifact_annotations_workspace_select" ON artifact_annotations'
        )
    )
    op.execute(text("DROP TABLE IF EXISTS artifact_annotations"))
    op.execute(text("DROP INDEX IF EXISTS uq_artifacts_id_workspace"))
