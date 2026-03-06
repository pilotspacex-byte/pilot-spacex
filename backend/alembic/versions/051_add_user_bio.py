"""Add bio column to users table.

Revision ID: 051_add_user_bio
Revises: 050_add_chat_cleanup_cron
Create Date: 2026-02-28

Changes:
- users.bio VARCHAR(200) NULLABLE — short bio displayed to teammates
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "051_add_user_bio"
down_revision = "050_add_chat_cleanup_cron"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("bio", sa.String(200), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "bio")
