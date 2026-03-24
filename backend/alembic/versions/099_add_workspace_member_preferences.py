"""Add workspace_member_preferences table with RLS policies.

Stores per-user per-workspace theme and editor customization preferences.
All preference fields are nullable (client applies defaults).

Revision ID: 099_add_workspace_member_preferences
Revises: 098_add_editor_plugins
Create Date: 2026-03-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "099_add_workspace_member_preferences"
down_revision: str = "098_add_editor_plugins"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create workspace_member_preferences table and enable RLS."""
    op.create_table(
        "workspace_member_preferences",
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
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("theme_mode", sa.String(20), nullable=True),
        sa.Column("accent_color", sa.String(50), nullable=True),
        sa.Column("editor_theme_id", sa.String(100), nullable=True),
        sa.Column("font_size", sa.Integer, nullable=True),
        sa.Column("font_family", sa.String(100), nullable=True),
        # Inherited soft-delete columns
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

    # Unique constraint: one preferences row per user per workspace
    op.create_unique_constraint(
        "uq_workspace_member_preferences_workspace_user",
        "workspace_member_preferences",
        ["workspace_id", "user_id"],
    )

    # Indexes for FK lookups
    op.create_index(
        "ix_workspace_member_preferences_workspace_id",
        "workspace_member_preferences",
        ["workspace_id"],
    )
    op.create_index(
        "ix_workspace_member_preferences_user_id",
        "workspace_member_preferences",
        ["user_id"],
    )

    # RLS: workspace isolation
    op.execute(text("ALTER TABLE workspace_member_preferences ENABLE ROW LEVEL SECURITY"))
    op.execute(text("ALTER TABLE workspace_member_preferences FORCE ROW LEVEL SECURITY"))

    # SELECT policy: members can read their own preferences
    op.execute(
        text("""
        CREATE POLICY "workspace_member_preferences_select_own"
        ON workspace_member_preferences
        FOR SELECT
        USING (
            user_id = current_setting('app.current_user_id', true)::uuid
        )
    """)
    )

    # INSERT/UPDATE/DELETE policy: members can manage their own preferences
    op.execute(
        text("""
        CREATE POLICY "workspace_member_preferences_modify_own"
        ON workspace_member_preferences
        FOR ALL
        USING (
            user_id = current_setting('app.current_user_id', true)::uuid
        )
    """)
    )

    # Service role bypass
    op.execute(
        text("""
        CREATE POLICY "workspace_member_preferences_service_role"
        ON workspace_member_preferences
        FOR ALL
        TO service_role
        USING (true)
    """)
    )


def downgrade() -> None:
    """Drop workspace_member_preferences table and policies."""
    op.execute(
        text(
            'DROP POLICY IF EXISTS "workspace_member_preferences_service_role"'
            " ON workspace_member_preferences"
        )
    )
    op.execute(
        text(
            'DROP POLICY IF EXISTS "workspace_member_preferences_modify_own"'
            " ON workspace_member_preferences"
        )
    )
    op.execute(
        text(
            'DROP POLICY IF EXISTS "workspace_member_preferences_select_own"'
            " ON workspace_member_preferences"
        )
    )
    op.execute(text("ALTER TABLE workspace_member_preferences DISABLE ROW LEVEL SECURITY"))
    op.drop_index(
        "ix_workspace_member_preferences_user_id",
        table_name="workspace_member_preferences",
    )
    op.drop_index(
        "ix_workspace_member_preferences_workspace_id",
        table_name="workspace_member_preferences",
    )
    op.drop_constraint(
        "uq_workspace_member_preferences_workspace_user",
        "workspace_member_preferences",
    )
    op.drop_table("workspace_member_preferences")
