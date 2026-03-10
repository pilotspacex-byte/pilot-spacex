"""Add notifications table.

Revision ID: 062_add_notifications_table
Revises: 061_add_pgmq_rpc_wrappers
Create Date: 2026-03-07

T-029: Notification Model + Migration.

Creates the notifications table with:
- UUID primary key
- workspace_id FK (CASCADE delete)
- user_id (recipient)
- type / priority enums
- title, body, entity_type, entity_id
- read_at (null = unread)
- Composite indexes for efficient user-scoped queries
- Row Level Security: users see only their own notifications
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "062_add_notifications_table"
down_revision: str = "061_add_pgmq_rpc_wrappers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create notifications table with enums, indexes, and RLS policies."""

    # --- Enum types ---
    op.execute(
        text(
            "CREATE TYPE notification_type AS ENUM "
            "('pr_review', 'assignment', 'sprint_deadline', 'mention', 'general')"
        )
    )
    op.execute(
        text("CREATE TYPE notification_priority AS ENUM ('low', 'medium', 'high', 'urgent')")
    )

    # --- Table ---
    op.create_table(
        "notifications",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        ),
        sa.Column(
            "workspace_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "type",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "title",
            sa.String(255),
            nullable=False,
        ),
        sa.Column(
            "body",
            sa.Text(),
            nullable=False,
            server_default="",
        ),
        sa.Column(
            "entity_type",
            sa.String(64),
            nullable=True,
        ),
        sa.Column(
            "entity_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "priority",
            sa.Text(),
            nullable=False,
            server_default="medium",
        ),
        sa.Column(
            "read_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=text("now()"),
            nullable=False,
        ),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            server_default=text("false"),
            nullable=False,
        ),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # Cast text columns to the enum types now that the table exists.
    # Drop defaults first — PostgreSQL cannot auto-cast a text default when changing column type.
    op.execute(text("ALTER TABLE notifications ALTER COLUMN type DROP DEFAULT"))
    op.execute(text("ALTER TABLE notifications ALTER COLUMN priority DROP DEFAULT"))
    op.execute(
        text(
            "ALTER TABLE notifications "
            "ALTER COLUMN type TYPE notification_type USING type::notification_type"
        )
    )
    op.execute(
        text(
            "ALTER TABLE notifications "
            "ALTER COLUMN priority TYPE notification_priority "
            "USING priority::notification_priority"
        )
    )
    op.execute(
        text(
            "ALTER TABLE notifications "
            "ALTER COLUMN priority SET DEFAULT 'medium'::notification_priority"
        )
    )

    # --- Indexes ---
    op.create_index(
        "ix_notifications_workspace_user_created",
        "notifications",
        ["workspace_id", "user_id", "created_at"],
    )
    op.create_index(
        "ix_notifications_workspace_user_read_at",
        "notifications",
        ["workspace_id", "user_id", "read_at"],
    )
    op.create_index(
        "ix_notifications_user_id",
        "notifications",
        ["user_id"],
    )

    # --- Row Level Security ---
    op.execute(text("ALTER TABLE notifications ENABLE ROW LEVEL SECURITY"))
    op.execute(text("ALTER TABLE notifications FORCE ROW LEVEL SECURITY"))

    # Users can only see/modify their own notifications
    op.execute(
        text(
            """
            CREATE POLICY "notifications_own_rows"
            ON notifications
            FOR ALL
            USING (
                current_setting('app.current_user_id', true)::uuid = user_id
            )
            WITH CHECK (
                current_setting('app.current_user_id', true)::uuid = user_id
            )
            """
        )
    )

    # Service role bypasses RLS (for worker inserts and admin operations)
    op.execute(
        text(
            """
            CREATE POLICY "notifications_service_role"
            ON notifications
            FOR ALL
            TO service_role
            USING (true)
            WITH CHECK (true)
            """
        )
    )


def downgrade() -> None:
    """Drop notifications table and enum types."""
    op.execute(text('DROP POLICY IF EXISTS "notifications_service_role" ON notifications'))
    op.execute(text('DROP POLICY IF EXISTS "notifications_own_rows" ON notifications'))
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_index("ix_notifications_workspace_user_read_at", table_name="notifications")
    op.drop_index("ix_notifications_workspace_user_created", table_name="notifications")
    op.drop_table("notifications")
    op.execute(text("DROP TYPE IF EXISTS notification_priority"))
    op.execute(text("DROP TYPE IF EXISTS notification_type"))
