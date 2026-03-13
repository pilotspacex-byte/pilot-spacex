"""Add icon_emoji column to notes table.

Revision ID: 080_add_note_icon_emoji
Revises: 079_add_page_tree_columns
Create Date: 2026-03-13

Changes:
- DDL: Add icon_emoji (VARCHAR(10), nullable) to notes table
- DDL: Partial index ix_notes_icon_emoji on non-null values
  (optimises queries that filter by presence of an emoji icon)
"""

import sqlalchemy as sa
from sqlalchemy import text

from alembic import op

revision = "080_add_note_icon_emoji"
down_revision = "079_add_page_tree_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add icon_emoji column and partial index to notes table."""
    # -------------------------------------------------------------------------
    # Step 1: DDL — Add icon_emoji column
    # -------------------------------------------------------------------------
    op.add_column(
        "notes",
        sa.Column(
            "icon_emoji",
            sa.String(10),
            nullable=True,
        ),
    )

    # -------------------------------------------------------------------------
    # Step 2: DDL — Partial index on non-null values
    # Only pages with an emoji are indexed, keeping index footprint minimal.
    # -------------------------------------------------------------------------
    op.execute(
        text("CREATE INDEX ix_notes_icon_emoji ON notes (icon_emoji) WHERE icon_emoji IS NOT NULL")
    )


def downgrade() -> None:
    """Drop partial index and icon_emoji column from notes table."""
    # Drop index before column
    op.execute(text("DROP INDEX IF EXISTS ix_notes_icon_emoji"))
    op.drop_column("notes", "icon_emoji")
