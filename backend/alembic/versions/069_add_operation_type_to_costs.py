"""Add operation_type column to ai_cost_records.

Revision ID: 069_add_operation_type_to_costs
Revises: 068_add_workspace_ai_policy
Create Date: 2026-03-08

Phase 4 — AI Governance (AIGOV-06):

Adds nullable operation_type VARCHAR(100) to ai_cost_records.
Enables cost breakdown by feature/operation category.

Uses IF NOT EXISTS to be idempotent — the column may already exist in
development environments where it was added outside of alembic.

Examples of operation_type values:
  - 'ghost_text'       — inline ghost text completions
  - 'issue_extraction' — AI issue extraction from notes
  - 'pr_review'        — automated PR review
  - 'chat'             — conversational AI chat
  - 'kg_populate'      — knowledge graph population

NULL = legacy records created before AIGOV-06 was implemented.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic
revision: str = "069_add_operation_type_to_costs"
down_revision: str = "068_add_workspace_ai_policy"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Add nullable operation_type column to ai_cost_records (idempotent).

    Uses ADD COLUMN IF NOT EXISTS because the column may already exist
    in environments where it was added outside of alembic.
    """
    op.execute(
        sa.text("ALTER TABLE ai_cost_records ADD COLUMN IF NOT EXISTS operation_type VARCHAR(100)")
    )


def downgrade() -> None:
    """Remove operation_type column from ai_cost_records."""
    op.drop_column("ai_cost_records", "operation_type")
