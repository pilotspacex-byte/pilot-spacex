"""Create drive_credentials table for Google Drive OAuth token storage.

Revision ID: 049_create_drive_credentials
Revises: 048_create_chat_attachments
Create Date: 2026-02-26

Creates:
- drive_credentials table with user-scoped RLS policy
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "049_create_drive_credentials"
down_revision: str | None = "048_create_chat_attachments"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Create drive_credentials table with indexes and user-scoped RLS."""
    op.create_table(
        "drive_credentials",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("google_email", sa.String(255), nullable=False),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=False),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scope", sa.Text(), nullable=False),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "workspace_id",
            name="uq_drive_credentials_user_workspace",
        ),
    )

    # Create indexes
    op.create_index(
        "ix_drive_credentials_user_workspace",
        "drive_credentials",
        ["user_id", "workspace_id"],
    )
    op.create_index(
        "ix_drive_credentials_expires_at",
        "drive_credentials",
        ["token_expires_at"],
    )

    # Enable RLS and create user-scoped policy (only owner can CRUD)
    op.execute("""
        ALTER TABLE drive_credentials ENABLE ROW LEVEL SECURITY;
        ALTER TABLE drive_credentials FORCE ROW LEVEL SECURITY;

        CREATE POLICY "drive_credentials_owner_only"
        ON drive_credentials
        FOR ALL
        USING (
            user_id = current_setting('app.current_user_id', true)::uuid
        )
        WITH CHECK (
            user_id = current_setting('app.current_user_id', true)::uuid
        );
    """)


def downgrade() -> None:
    """Drop drive_credentials table, indexes, and RLS policy."""
    # Drop RLS policy
    op.execute("""
        DROP POLICY IF EXISTS "drive_credentials_owner_only" ON drive_credentials;
        ALTER TABLE drive_credentials DISABLE ROW LEVEL SECURITY;
    """)

    # Drop indexes
    op.drop_index("ix_drive_credentials_expires_at", table_name="drive_credentials")
    op.drop_index("ix_drive_credentials_user_workspace", table_name="drive_credentials")

    # Drop table (unique constraint drops with it)
    op.drop_table("drive_credentials")
