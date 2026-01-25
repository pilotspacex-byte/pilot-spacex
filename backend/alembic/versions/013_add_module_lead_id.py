"""Add lead_id column to modules table.

Revision ID: 013_add_module_lead_id
Revises: 012_ai_configurations
Create Date: 2026-01-24

Adds the lead_id column to modules table that was missing from migration 003.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "013_add_module_lead_id"
down_revision: str | None = "012_ai_configurations"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Add lead_id column to modules table."""
    op.add_column(
        "modules",
        sa.Column(
            "lead_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    op.create_foreign_key(
        "fk_modules_lead",
        "modules",
        "users",
        ["lead_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_index("ix_modules_lead_id", "modules", ["lead_id"])


def downgrade() -> None:
    """Remove lead_id column from modules table."""
    op.drop_index("ix_modules_lead_id", table_name="modules")
    op.drop_constraint("fk_modules_lead", "modules", type_="foreignkey")
    op.drop_column("modules", "lead_id")
