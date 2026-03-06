"""Add ci_status to integration_links and ai_review to activity_type enum.

Revision ID: 063_add_ci_status_and_ai_review
Revises: 062_add_notifications_table
Create Date: 2026-03-07

T-023: CI Check Status on Issue PR Links.
T-024: Wire PR Review Findings into Issue Activity Timeline.

Changes:
- ALTER TABLE integration_links ADD COLUMN ci_status VARCHAR(20) (nullable)
- ALTER TYPE activity_type ADD VALUE 'ai_review'
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "063_add_ci_status_and_ai_review"
down_revision = "062_add_notifications_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add ci_status column and ai_review enum value."""
    # Add ci_status to integration_links.
    op.add_column(
        "integration_links",
        sa.Column("ci_status", sa.String(20), nullable=True),
    )

    # Add ai_review to activity_type enum.
    # PostgreSQL supports IF NOT EXISTS (PG 9.6+) to make this idempotent.
    op.execute(sa.text("ALTER TYPE activity_type ADD VALUE IF NOT EXISTS 'ai_review'"))


def downgrade() -> None:
    """Remove ci_status column. Enum value removal is not supported in PostgreSQL."""
    op.drop_column("integration_links", "ci_status")
    # PostgreSQL does not support removing enum values once added.
    # The 'ai_review' enum value will remain in the DB type after downgrade.
