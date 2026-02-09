"""Add digest_dismissals table for Homepage Hub.

Revision ID: 029_add_digest_dismissals
Revises: 028_add_workspace_digests
Create Date: 2026-02-07

Tracks per-user dismissals of AI digest suggestions so dismissed items
are not shown again. Each row records which suggestion (by category,
entity_id, entity_type) a user dismissed and when.

Source: specs/012-homepage-note, plan.md Phase 0.2
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "029_add_digest_dismissals"
down_revision: str = "028_add_workspace_digests"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create digest_dismissals table with index."""
    op.create_table(
        "digest_dismissals",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "suggestion_category",
            sa.String(30),
            nullable=False,
        ),
        sa.Column(
            "entity_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "entity_type",
            sa.String(20),
            nullable=False,
        ),
        sa.Column(
            "dismissed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_digest_dismissals_user_entity",
        "digest_dismissals",
        ["workspace_id", "user_id", "entity_id"],
    )


def downgrade() -> None:
    """Drop digest_dismissals table."""
    op.drop_index("ix_digest_dismissals_user_entity", "digest_dismissals")
    op.drop_table("digest_dismissals")
