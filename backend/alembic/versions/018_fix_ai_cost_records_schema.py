"""Fix ai_cost_records schema - add missing columns.

Revision ID: 018_fix_ai_cost_records
Revises: 017_ai_sessions
Create Date: 2026-01-26 16:50:00.000000

Adds missing columns to ai_cost_records table:
- updated_at (TimestampMixin requirement)
- is_deleted (SoftDeleteMixin requirement)
- deleted_at (SoftDeleteMixin requirement)

Also adds missing indexes for the model.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# Revision identifiers, used by Alembic.
revision: str = "018_fix_ai_cost_records"
down_revision: str | None = "017_ai_sessions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply migration."""
    # Use raw SQL with IF NOT EXISTS for idempotent column additions
    # (updated_at may already exist from manual fix)
    conn = op.get_bind()
    conn.execute(
        sa.text("""
            ALTER TABLE ai_cost_records
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        """)
    )
    conn.execute(
        sa.text("""
            ALTER TABLE ai_cost_records
            ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE
        """)
    )
    conn.execute(
        sa.text("""
            ALTER TABLE ai_cost_records
            ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE
        """)
    )

    # Add missing indexes defined in the model (IF NOT EXISTS via raw SQL)
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_ai_cost_records_created_at "
            "ON ai_cost_records (created_at)"
        )
    )
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_ai_cost_records_provider ON ai_cost_records (provider)"
        )
    )
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_ai_cost_records_user_id ON ai_cost_records (user_id)"
        )
    )
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_ai_cost_records_workspace_id "
            "ON ai_cost_records (workspace_id)"
        )
    )
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_ai_cost_records_agent_name "
            "ON ai_cost_records (agent_name)"
        )
    )
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_ai_cost_records_workspace_created "
            "ON ai_cost_records (workspace_id, created_at)"
        )
    )
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_ai_cost_records_user_created "
            "ON ai_cost_records (user_id, created_at)"
        )
    )


def downgrade() -> None:
    """Revert migration."""
    # Drop indexes
    op.drop_index("ix_ai_cost_records_user_created", table_name="ai_cost_records")
    op.drop_index("ix_ai_cost_records_workspace_created", table_name="ai_cost_records")
    op.drop_index("ix_ai_cost_records_agent_name", table_name="ai_cost_records")
    op.drop_index("ix_ai_cost_records_workspace_id", table_name="ai_cost_records")
    op.drop_index("ix_ai_cost_records_user_id", table_name="ai_cost_records")
    op.drop_index("ix_ai_cost_records_provider", table_name="ai_cost_records")
    op.drop_index("ix_ai_cost_records_created_at", table_name="ai_cost_records")

    # Drop columns
    op.drop_column("ai_cost_records", "deleted_at")
    op.drop_column("ai_cost_records", "is_deleted")
    op.drop_column("ai_cost_records", "updated_at")
