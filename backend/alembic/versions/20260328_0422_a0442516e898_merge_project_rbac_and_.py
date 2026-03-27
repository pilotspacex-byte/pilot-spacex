"""merge_project_rbac_and_invitation_constraint

Revision ID: a0442516e898
Revises: 100_project_rbac_schema, 103_fix_invitation_unique_constraint
Create Date: 2026-03-28 04:22:08.869452
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


# Revision identifiers, used by Alembic.
revision: str = "a0442516e898"
down_revision: str | None = ("100_project_rbac_schema", "103_fix_invitation_unique_constraint")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply migration."""
    pass


def downgrade() -> None:
    """Revert migration."""
    pass
