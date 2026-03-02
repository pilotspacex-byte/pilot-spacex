"""Create chat_attachments table for temporary file attachment metadata.

Revision ID: 048_create_chat_attachments
Revises: 047_add_note_note_links
Create Date: 2026-02-26

Creates:
- chat_attachments table with RLS workspace member policy
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "048_create_chat_attachments"
down_revision: str | None = "047_add_note_note_links"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Create chat_attachments table with indexes and RLS."""
    op.create_table(
        "chat_attachments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", sa.Text(), nullable=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("drive_file_id", sa.String(255), nullable=True),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW() + INTERVAL '24 hours'"),
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
        sa.CheckConstraint("size_bytes > 0", name="ck_chat_attachments_size"),
        sa.CheckConstraint(
            "source IN ('local', 'google_drive')",
            name="ck_chat_attachments_source",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key", name="uq_chat_attachments_storage_key"),
    )

    # Create indexes
    op.create_index(
        "ix_chat_attachments_workspace_user",
        "chat_attachments",
        ["workspace_id", "user_id"],
    )
    op.create_index(
        "ix_chat_attachments_session",
        "chat_attachments",
        ["session_id"],
    )
    op.create_index(
        "ix_chat_attachments_expires_at",
        "chat_attachments",
        ["expires_at"],
    )

    # Enable RLS and create workspace member policy
    op.execute("""
        ALTER TABLE chat_attachments ENABLE ROW LEVEL SECURITY;
        ALTER TABLE chat_attachments FORCE ROW LEVEL SECURITY;

        CREATE POLICY "chat_attachments_workspace_member"
        ON chat_attachments
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
    """Drop chat_attachments table, indexes, and RLS policy."""
    # Drop RLS policy
    op.execute("""
        DROP POLICY IF EXISTS "chat_attachments_workspace_member" ON chat_attachments;
        ALTER TABLE chat_attachments DISABLE ROW LEVEL SECURITY;
    """)

    # Drop indexes
    op.drop_index("ix_chat_attachments_expires_at", table_name="chat_attachments")
    op.drop_index("ix_chat_attachments_session", table_name="chat_attachments")
    op.drop_index("ix_chat_attachments_workspace_user", table_name="chat_attachments")

    # Drop table (unique constraint and check constraints drop with it)
    op.drop_table("chat_attachments")
