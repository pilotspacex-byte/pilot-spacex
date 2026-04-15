"""Add current_stage column to batch_run_issues for SSE stage tracking.

Fine-grained execution stage persisted so late-joining SSE clients can
determine the current sub-stage (cloning / implementing / creating_pr)
without replaying the full event stream.

Phase 76 Plan 01 — sprint batch implementation foundation.

Revision ID: 111_batch_run_current_stage
Revises: 110_data_foundations_source_note_batch_runs
Create Date: 2026-04-15
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "111_batch_run_current_stage"
down_revision: str | None = "110_data_foundations_source_note_batch_runs"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Add current_stage column to batch_run_issues."""
    op.add_column(
        "batch_run_issues",
        sa.Column("current_stage", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Drop current_stage column from batch_run_issues."""
    op.drop_column("batch_run_issues", "current_stage")
