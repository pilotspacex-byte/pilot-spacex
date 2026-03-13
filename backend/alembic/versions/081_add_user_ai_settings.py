"""Add ai_settings JSONB column to users table.

Revision ID: 081_add_user_ai_settings
Revises: 080_add_note_icon_emoji
Create Date: 2026-03-13

Changes:
- DDL: Add ai_settings (JSONB, nullable) to users table
  Stores per-user AI model overrides and base_url configuration.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "081_add_user_ai_settings"
down_revision: str = "080_add_note_icon_emoji"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Add ai_settings JSONB column to users table."""
    op.add_column(
        "users",
        sa.Column("ai_settings", postgresql.JSONB, nullable=True),
    )


def downgrade() -> None:
    """Remove ai_settings column from users table."""
    op.drop_column("users", "ai_settings")
