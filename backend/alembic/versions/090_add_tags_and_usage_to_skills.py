"""Add tags and usage columns to skill tables.

Revision ID: 090_add_tags_and_usage_to_skills
Revises: 089_add_role_type_idx
Create Date: 2026-03-18

Adds tags (JSON array) and usage (Text) to user_skills, user_role_skills,
and workspace_role_skills tables.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "090_add_tags_and_usage_to_skills"
down_revision: str = "089_add_role_type_idx"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = ["user_skills", "user_role_skills", "workspace_role_skills"]


def upgrade() -> None:
    """Add tags and usage columns to all three skill tables."""
    for table in _TABLES:
        op.add_column(
            table,
            sa.Column(
                "tags",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'[]'"),
            ),
        )
        op.add_column(
            table,
            sa.Column(
                "usage",
                sa.Text(),
                nullable=True,
            ),
        )


def downgrade() -> None:
    """Drop tags and usage columns from all three skill tables."""
    for table in _TABLES:
        op.drop_column(table, "usage")
        op.drop_column(table, "tags")
