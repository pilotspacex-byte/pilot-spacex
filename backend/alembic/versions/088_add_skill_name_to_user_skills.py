"""Add skill_name column to user_skills table.

Revision ID: 088_add_skill_name_to_user_skills
Revises: 087_drop_role_type_unique_constraint
Create Date: 2026-03-17

Stores the user-visible name for a skill (AI-suggested or user-edited).
Nullable so existing rows are unaffected.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "088_add_skill_name_to_user_skills"
down_revision: str = "087_drop_role_type_unique_constraint"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add skill_name column."""
    op.add_column("user_skills", sa.Column("skill_name", sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove skill_name column."""
    op.drop_column("user_skills", "skill_name")
