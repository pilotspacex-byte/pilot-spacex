"""Fix digest_dismissals entity_id nullable + add unique constraint.

Revision ID: 033_fix_dismissals_nullable_and_constraints
Revises: 032_add_digest_cron_job
Create Date: 2026-02-07

Fixes:
- ARCH-C1: entity_id and entity_type are now nullable for workspace-wide
  suggestions that don't reference a specific entity.
- BE-H3: Adds unique constraint on (workspace_id, user_id, entity_id,
  suggestion_category) to prevent duplicate dismissals from concurrent
  requests.
- BE-M1: Replaces the existing index with one that includes
  suggestion_category for faster dismissal filtering.

Source: PR #9 Devil's Advocate Review
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "033_fix_dismissals_nullable_and_constraints"
down_revision: str = "032_add_digest_cron_job"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Make entity_id/entity_type nullable and add unique constraint."""
    # ARCH-C1: Make entity_id and entity_type nullable
    op.alter_column(
        "digest_dismissals",
        "entity_id",
        existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.alter_column(
        "digest_dismissals",
        "entity_type",
        existing_type=sa.String(20),
        nullable=True,
    )

    # BE-M1: Drop old index and create new one with suggestion_category
    op.drop_index("ix_digest_dismissals_user_entity", "digest_dismissals")
    op.create_index(
        "ix_digest_dismissals_user_entity",
        "digest_dismissals",
        ["workspace_id", "user_id", "entity_id", "suggestion_category"],
    )

    # BE-H3: Add unique constraint to prevent duplicate dismissals
    op.create_unique_constraint(
        "uq_digest_dismissals_user_suggestion",
        "digest_dismissals",
        ["workspace_id", "user_id", "entity_id", "suggestion_category"],
    )

    # BE-C1: Add unique partial index to prevent duplicate concurrent digests
    op.execute(
        """
        CREATE UNIQUE INDEX ix_workspace_digests_recent_unique
        ON workspace_digests (workspace_id)
        WHERE generated_at >= NOW() - INTERVAL '30 minutes'
        AND is_deleted = false;
        """
    )


def downgrade() -> None:
    """Revert nullable changes and constraints."""
    op.execute("DROP INDEX IF EXISTS ix_workspace_digests_recent_unique;")
    op.drop_constraint("uq_digest_dismissals_user_suggestion", "digest_dismissals", type_="unique")
    op.drop_index("ix_digest_dismissals_user_entity", "digest_dismissals")
    op.create_index(
        "ix_digest_dismissals_user_entity",
        "digest_dismissals",
        ["workspace_id", "user_id", "entity_id"],
    )
    op.alter_column(
        "digest_dismissals",
        "entity_type",
        existing_type=sa.String(20),
        nullable=False,
    )
    op.alter_column(
        "digest_dismissals",
        "entity_id",
        existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
        nullable=False,
    )
