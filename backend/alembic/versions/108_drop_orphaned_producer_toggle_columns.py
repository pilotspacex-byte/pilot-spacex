"""Drop orphaned producer toggle columns from workspace_ai_settings.

Migration 107 added four boolean columns to ``workspace_ai_settings``
for Phase 70 producer opt-out toggles. However, the runtime code
stores these flags in ``workspaces.settings`` (JSONB) instead — the
columns are never read or written. This migration drops them if they exist.

Note: ``workspace_ai_settings`` table may not exist (SEC-05). All
operations wrapped in try/except.

Revision ID: 108_drop_orphaned_producer_toggle_columns
Revises: 107_memory_producer_toggles
Create Date: 2026-04-08
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "108_drop_orphaned_producer_toggle_columns"
down_revision: str | None = "107_memory_producer_toggles"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None

_TABLE = "workspace_ai_settings"
_COLUMNS = [
    "memory_producer_agent_turn_enabled",
    "memory_producer_user_correction_enabled",
    "memory_producer_pr_review_enabled",
    "memory_summarizer_enabled",
]


def upgrade() -> None:
    try:
        for col in _COLUMNS:
            op.drop_column(_TABLE, col)
    except Exception:
        # Table does not exist — columns were never created.
        pass


def downgrade() -> None:
    """Re-add the columns (inverse of upgrade)."""
    try:
        op.add_column(
            _TABLE,
            sa.Column(
                "memory_producer_agent_turn_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            ),
        )
        op.add_column(
            _TABLE,
            sa.Column(
                "memory_producer_user_correction_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            ),
        )
        op.add_column(
            _TABLE,
            sa.Column(
                "memory_producer_pr_review_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            ),
        )
        op.add_column(
            _TABLE,
            sa.Column(
                "memory_summarizer_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )
    except Exception:
        pass
