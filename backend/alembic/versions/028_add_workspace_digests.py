"""Add workspace_digests table for Homepage Hub AI digest.

Revision ID: 028_add_workspace_digests
Revises: 027_merge_heads
Create Date: 2026-02-07

Stores hourly AI-generated workspace insights and actionable suggestions.
Each digest contains JSONB suggestions array categorised by type
(stale_issues, unlinked_notes, review_needed, etc.).

Source: specs/012-homepage-note, plan.md Phase 0.1
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "028_add_workspace_digests"
down_revision: str = "027_merge_heads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create workspace_digests table with index."""
    op.create_table(
        "workspace_digests",
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
            "generated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "generated_by",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'scheduled'"),
        ),
        sa.Column(
            "suggestions",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "model_used",
            sa.String(50),
            nullable=True,
        ),
        sa.Column(
            "token_usage",
            postgresql.JSONB(),
            nullable=True,
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
        "ix_workspace_digests_workspace_generated",
        "workspace_digests",
        ["workspace_id", "generated_at"],
    )


def downgrade() -> None:
    """Drop workspace_digests table."""
    op.drop_index("ix_workspace_digests_workspace_generated", "workspace_digests")
    op.drop_table("workspace_digests")
