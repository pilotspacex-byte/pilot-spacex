"""Add artifact_annotations table with RLS policies.

Stores user-authored slide annotations on project artifacts.
Hard-delete model — no soft-delete columns beyond the inherited placeholders.
RLS follows the same workspace-isolation pattern as the artifacts table.

Revision ID: 097_add_artifact_annotations
Revises: 096_add_note_chunk_node_type
Create Date: 2026-03-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "097_add_artifact_annotations"
down_revision: str = "096_add_note_chunk_node_type"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create artifact_annotations table and enable RLS."""
    op.create_table(
        "artifact_annotations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "artifact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("artifacts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("slide_index", sa.Integer, nullable=True),
        sa.Column("content", sa.Text, nullable=False),
        # Inherited soft-delete columns (unused — hard delete only)
        sa.Column(
            "is_deleted",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_artifact_annotations_artifact_id",
        "artifact_annotations",
        ["artifact_id"],
    )
    op.create_index(
        "ix_artifact_annotations_workspace_artifact",
        "artifact_annotations",
        ["workspace_id", "artifact_id"],
    )

    # RLS: workspace isolation
    op.execute(text("ALTER TABLE artifact_annotations ENABLE ROW LEVEL SECURITY"))
    op.execute(text("ALTER TABLE artifact_annotations FORCE ROW LEVEL SECURITY"))

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
                AND wm.role IN ('OWNER', 'ADMIN', 'MEMBER', 'GUEST')
            )
        )
    """)
    )

    op.execute(
        text("""
        CREATE POLICY "artifact_annotations_service_role"
        ON artifact_annotations
        FOR ALL
        TO service_role
        USING (true)
    """)
    )


def downgrade() -> None:
    """Drop artifact_annotations table and policies."""
    op.execute(
        text('DROP POLICY IF EXISTS "artifact_annotations_service_role" ON artifact_annotations')
    )
    op.execute(
        text(
            'DROP POLICY IF EXISTS "artifact_annotations_workspace_isolation"'
            " ON artifact_annotations"
        )
    )
    op.execute(text("ALTER TABLE artifact_annotations DISABLE ROW LEVEL SECURITY"))
    op.drop_index(
        "ix_artifact_annotations_workspace_artifact",
        table_name="artifact_annotations",
    )
    op.drop_index("ix_artifact_annotations_artifact_id", table_name="artifact_annotations")
    op.drop_table("artifact_annotations")
