"""Drop role_type unique constraint on user_role_skills.

Revision ID: 087_drop_role_type_unique_constraint
Revises: 086_fix_invitation_status_enum
Create Date: 2026-03-16

Allows users to create multiple skills with the same role_type
(especially 'custom') per workspace. The unique constraint
(user_id, workspace_id, role_type) is replaced by a non-unique index.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "087_drop_role_type_unique_constraint"
down_revision: str = "086_fix_invitation_status_enum"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop unique constraint, keep non-unique index for queries."""
    op.drop_constraint(
        "uq_user_role_skills_user_workspace_role",
        "user_role_skills",
        type_="unique",
    )


def downgrade() -> None:
    """Restore unique constraint."""
    op.create_unique_constraint(
        "uq_user_role_skills_user_workspace_role",
        "user_role_skills",
        ["user_id", "workspace_id", "role_type"],
    )
