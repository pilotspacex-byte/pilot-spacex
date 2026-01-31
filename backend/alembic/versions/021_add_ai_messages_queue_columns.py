"""Add queue-related columns to ai_messages table.

Revision ID: 021_ai_msg_queue_cols
Revises: 020_create_ai_conv
Create Date: 2026-01-30

Adds columns for queue-based conversation processing:
- job_id: Links message to queue job
- token_usage: Token count and model info
- tool_calls: Tool call summaries
- processing_time_ms: Wall-clock processing time
- completed_at: Processing completion timestamp

All columns nullable for safe additive-only migration.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "021_ai_msg_queue_cols"
down_revision: str | None = "020_create_ai_conv"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Add queue columns to ai_messages."""
    op.add_column(
        "ai_messages",
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "ai_messages",
        sa.Column("token_usage", postgresql.JSONB, nullable=True),
    )
    op.add_column(
        "ai_messages",
        sa.Column("tool_calls", postgresql.JSONB, nullable=True),
    )
    op.add_column(
        "ai_messages",
        sa.Column("processing_time_ms", sa.Integer, nullable=True),
    )
    op.add_column(
        "ai_messages",
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Unique index on job_id for quick lookup
    op.create_index(
        "ix_ai_messages_job_id",
        "ai_messages",
        ["job_id"],
        unique=True,
        postgresql_where=sa.text("job_id IS NOT NULL"),
    )

    # Partial index for active (incomplete) messages per session
    op.create_index(
        "ix_ai_messages_session_active",
        "ai_messages",
        ["session_id"],
        postgresql_where=sa.text("completed_at IS NULL"),
    )


def downgrade() -> None:
    """Remove queue columns from ai_messages."""
    op.drop_index("ix_ai_messages_session_active", table_name="ai_messages")
    op.drop_index("ix_ai_messages_job_id", table_name="ai_messages")
    op.drop_column("ai_messages", "completed_at")
    op.drop_column("ai_messages", "processing_time_ms")
    op.drop_column("ai_messages", "tool_calls")
    op.drop_column("ai_messages", "token_usage")
    op.drop_column("ai_messages", "job_id")
