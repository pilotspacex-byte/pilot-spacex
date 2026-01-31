"""Extend annotation_type enum with new values.

Revision ID: 019_annotation_enum
Revises: 20260126_1650_018_fix_ai_cost_records_schema
Create Date: 2026-01-26

Adds new annotation type values to support AI agent output:
- question: Clarification needed
- insight: Additional context
- reference: Related content link
"""

from alembic import op

# revision identifiers, used by Alembic
revision = "019_annotation_enum"
down_revision = "018_fix_ai_cost_records"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add new values to annotation_type enum."""
    # PostgreSQL ALTER TYPE to add new enum values
    op.execute("ALTER TYPE annotation_type ADD VALUE IF NOT EXISTS 'question'")
    op.execute("ALTER TYPE annotation_type ADD VALUE IF NOT EXISTS 'insight'")
    op.execute("ALTER TYPE annotation_type ADD VALUE IF NOT EXISTS 'reference'")


def downgrade() -> None:
    """Cannot remove enum values in PostgreSQL.

    PostgreSQL does not support removing values from an enum type.
    The values will remain but won't be used if application code doesn't use them.
    """
