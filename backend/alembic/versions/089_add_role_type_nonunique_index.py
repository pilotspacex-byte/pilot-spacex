"""Add non-unique index on user_role_skills(user_id, workspace_id, role_type).

Revision ID: 089_add_role_type_nonunique_index
Revises: 088_add_skill_name_to_user_skills
Create Date: 2026-03-17

Migration 087 dropped the unique constraint but forgot to create
the promised non-unique replacement index. This migration adds it.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "089_add_role_type_nonunique_index"
down_revision: str = "088_add_skill_name_to_user_skills"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create non-unique index for role_type queries."""
    op.create_index(
        "ix_user_role_skills_user_workspace_role",
        "user_role_skills",
        ["user_id", "workspace_id", "role_type"],
    )


def downgrade() -> None:
    """Drop the non-unique index."""
    op.drop_index(
        "ix_user_role_skills_user_workspace_role",
        table_name="user_role_skills",
    )
