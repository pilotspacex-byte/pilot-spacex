"""Create AI conversational tables for Wave 2.

Revision ID: 020_create_ai_conversational_tables
Revises: 019_annotation_enum_enum
Create Date: 2026-01-28

Creates tables for:
- ai_messages: Individual messages in conversation sessions
- ai_tool_calls: Tool invocations during AI processing
- ai_tasks: Tracked units of work with dependencies
- Updates ai_approval_requests: Add Wave 2 columns (message_id, description, etc.)
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "020_create_ai_conv"
down_revision: str | None = "019_annotation_enum"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Create AI conversational tables."""
    # 1. Create ai_messages table
    op.create_table(
        "ai_messages",
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
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["ai_sessions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_messages_session_id", "ai_messages", ["session_id"])
    op.create_index("ix_ai_messages_session_created", "ai_messages", ["session_id", "created_at"])

    # 2. Create ai_tool_calls table
    op.create_table(
        "ai_tool_calls",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tool_name", sa.String(100), nullable=False),
        sa.Column("tool_input", postgresql.JSONB(), nullable=False),
        sa.Column("tool_output", postgresql.JSONB(), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["ai_messages.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_tool_calls_message_id", "ai_tool_calls", ["message_id"])
    op.execute("""
        CREATE INDEX ix_ai_tool_calls_status_pending
        ON ai_tool_calls (status)
        WHERE status IN ('pending', 'running')
    """)

    # 3. Create ai_tasks table
    op.create_table(
        "ai_tasks",
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
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("owner", sa.String(100), nullable=True),
        sa.Column("progress", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("blocked_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["ai_sessions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["blocked_by_id"],
            ["ai_tasks.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_tasks_session_id", "ai_tasks", ["session_id"])
    op.create_index("ix_ai_tasks_session_status", "ai_tasks", ["session_id", "status"])

    # 4. Update ai_approval_requests table with Wave 2 columns
    op.add_column(
        "ai_approval_requests",
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "ai_approval_requests",
        sa.Column(
            "description", sa.Text(), nullable=True
        ),  # Will be made NOT NULL in data migration
    )
    op.add_column(
        "ai_approval_requests",
        sa.Column("consequences", sa.Text(), nullable=True),
    )
    op.add_column(
        "ai_approval_requests",
        sa.Column("affected_entities", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "ai_approval_requests",
        sa.Column(
            "urgency",
            sa.String(20),
            server_default=sa.text("'medium'"),
            nullable=False,
        ),
    )
    op.add_column(
        "ai_approval_requests",
        sa.Column("proposed_content", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "ai_approval_requests",
        sa.Column("modified_content", postgresql.JSONB(), nullable=True),
    )

    # Add foreign key constraint for message_id
    op.create_foreign_key(
        "fk_ai_approval_requests_message_id",
        "ai_approval_requests",
        "ai_messages",
        ["message_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Update approval_status enum to add 'modified'
    op.execute("ALTER TYPE approval_status ADD VALUE IF NOT EXISTS 'modified'")

    # Create RLS policies for new tables
    _create_rls_policies()


def _create_rls_policies() -> None:
    """Create RLS policies for new AI tables."""
    # ai_messages: Access via session ownership
    op.execute("ALTER TABLE ai_messages ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE ai_messages FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY "ai_messages_session_access"
        ON ai_messages
        FOR ALL
        USING (
            session_id IN (
                SELECT id FROM ai_sessions
                WHERE user_id = current_setting('app.current_user_id', true)::uuid
            )
        )
        WITH CHECK (
            session_id IN (
                SELECT id FROM ai_sessions
                WHERE user_id = current_setting('app.current_user_id', true)::uuid
            )
        )
    """)

    # ai_tool_calls: Access via message → session ownership
    op.execute("ALTER TABLE ai_tool_calls ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE ai_tool_calls FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY "ai_tool_calls_session_access"
        ON ai_tool_calls
        FOR ALL
        USING (
            message_id IN (
                SELECT id FROM ai_messages
                WHERE session_id IN (
                    SELECT id FROM ai_sessions
                    WHERE user_id = current_setting('app.current_user_id', true)::uuid
                )
            )
        )
        WITH CHECK (
            message_id IN (
                SELECT id FROM ai_messages
                WHERE session_id IN (
                    SELECT id FROM ai_sessions
                    WHERE user_id = current_setting('app.current_user_id', true)::uuid
                )
            )
        )
    """)

    # ai_tasks: Access via session ownership
    op.execute("ALTER TABLE ai_tasks ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE ai_tasks FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY "ai_tasks_session_access"
        ON ai_tasks
        FOR ALL
        USING (
            session_id IN (
                SELECT id FROM ai_sessions
                WHERE user_id = current_setting('app.current_user_id', true)::uuid
            )
        )
        WITH CHECK (
            session_id IN (
                SELECT id FROM ai_sessions
                WHERE user_id = current_setting('app.current_user_id', true)::uuid
            )
        )
    """)


def downgrade() -> None:
    """Drop AI conversational tables."""
    # Drop RLS policies
    op.execute('DROP POLICY IF EXISTS "ai_tasks_session_access" ON ai_tasks')
    op.execute("ALTER TABLE ai_tasks DISABLE ROW LEVEL SECURITY")

    op.execute('DROP POLICY IF EXISTS "ai_tool_calls_session_access" ON ai_tool_calls')
    op.execute("ALTER TABLE ai_tool_calls DISABLE ROW LEVEL SECURITY")

    op.execute('DROP POLICY IF EXISTS "ai_messages_session_access" ON ai_messages')
    op.execute("ALTER TABLE ai_messages DISABLE ROW LEVEL SECURITY")

    # Remove columns from ai_approval_requests
    op.drop_constraint(
        "fk_ai_approval_requests_message_id",
        "ai_approval_requests",
        type_="foreignkey",
    )
    op.drop_column("ai_approval_requests", "modified_content")
    op.drop_column("ai_approval_requests", "proposed_content")
    op.drop_column("ai_approval_requests", "urgency")
    op.drop_column("ai_approval_requests", "affected_entities")
    op.drop_column("ai_approval_requests", "consequences")
    op.drop_column("ai_approval_requests", "description")
    op.drop_column("ai_approval_requests", "message_id")

    # Drop tables (order matters due to foreign keys)
    op.drop_table("ai_tasks")
    op.drop_table("ai_tool_calls")
    op.drop_table("ai_messages")
