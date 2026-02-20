"""Add note_note_links table for note-to-note linking.

Revision ID: 047_add_note_note_links
Revises: 046_add_work_intent_embedding
Create Date: 2026-02-20

Creates:
- note_note_link_type enum (inline, embed)
- note_note_links table with RLS policy
"""

import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "047_add_note_note_links"
down_revision: str | None = "046_add_work_intent_embedding"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Create note_note_links table with RLS."""
    # Create note_note_link_type enum
    note_note_link_type = postgresql.ENUM(
        "inline",
        "embed",
        name="note_note_link_type",
        create_type=True,
    )
    note_note_link_type.create(op.get_bind(), checkfirst=True)

    # Create note_note_links table
    op.create_table(
        "note_note_links",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_note_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_note_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "link_type",
            postgresql.ENUM(
                "inline",
                "embed",
                name="note_note_link_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("block_id", sa.String(100), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_note_id"], ["notes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_note_id"], ["notes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index(
        "ix_note_note_links_workspace_id",
        "note_note_links",
        ["workspace_id"],
    )
    op.create_index(
        "ix_note_note_links_source_note_id",
        "note_note_links",
        ["source_note_id"],
    )
    op.create_index(
        "ix_note_note_links_target_note_id",
        "note_note_links",
        ["target_note_id"],
    )
    op.create_index(
        "ix_note_note_links_link_type",
        "note_note_links",
        ["link_type"],
    )
    op.create_index(
        "ix_note_note_links_is_deleted",
        "note_note_links",
        ["is_deleted"],
    )

    # Partial unique index: enforce at most one unanchored link per source+target pair
    # when block_id IS NULL (regular UNIQUE constraint treats NULL != NULL in PostgreSQL)
    op.create_index(
        "uq_note_note_links_unanchored",
        "note_note_links",
        ["source_note_id", "target_note_id"],
        unique=True,
        postgresql_where=text("block_id IS NULL"),
    )

    # Partial unique index: enforce uniqueness only on non-deleted rows so soft-deleted
    # links do not block re-creation of the same source/target/block combination.
    op.create_index(
        "uq_note_note_links_source_target_block",
        "note_note_links",
        ["source_note_id", "target_note_id", "block_id"],
        unique=True,
        postgresql_where=text("is_deleted = false"),
    )

    # Create RLS policy (mirroring note_issue_links)
    op.execute("""
        ALTER TABLE note_note_links ENABLE ROW LEVEL SECURITY;
        ALTER TABLE note_note_links FORCE ROW LEVEL SECURITY;

        CREATE POLICY "note_note_links_workspace_member"
        ON note_note_links
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
        );
    """)


def downgrade() -> None:
    """Drop note_note_links table and RLS policy."""
    # Drop RLS policy
    op.execute("""
        DROP POLICY IF EXISTS "note_note_links_workspace_member" ON note_note_links;
        ALTER TABLE note_note_links DISABLE ROW LEVEL SECURITY;
    """)

    # Drop partial unique indexes
    op.drop_index("uq_note_note_links_source_target_block", table_name="note_note_links")
    op.drop_index("uq_note_note_links_unanchored", table_name="note_note_links")

    # Drop table
    op.drop_table("note_note_links")

    # Drop enum
    op.execute("DROP TYPE IF EXISTS note_note_link_type")
