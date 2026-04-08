"""Phase 70 Wave 0: memory producer opt-out toggles + PR review finding unique index.

Adds four boolean opt-out/opt-in columns to ``workspace_ai_settings`` controlling
the four Phase 70 memory producers:

    - memory_producer_agent_turn_enabled        (default TRUE  — opt-out)
    - memory_producer_user_correction_enabled   (default TRUE  — opt-out)
    - memory_producer_pr_review_enabled         (default TRUE  — opt-out)
    - memory_summarizer_enabled                 (default FALSE — opt-in)

Also creates a partial UNIQUE index on ``graph_nodes`` scoping
``pr_review_finding`` rows by (workspace_id, repo, pr_number, file_path,
line_number) so replayed PR reviews dedupe deterministically (mirrors the
agent_turn_cache index added in migration 106).

Revision ID: 107_memory_producer_toggles
Revises: 106_phase69_memory_node_types
Create Date: 2026-04-07
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "107_memory_producer_toggles"
down_revision: str | None = "106_phase69_memory_node_types"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column(
        "workspace_ai_settings",
        sa.Column(
            "memory_producer_agent_turn_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.add_column(
        "workspace_ai_settings",
        sa.Column(
            "memory_producer_user_correction_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.add_column(
        "workspace_ai_settings",
        sa.Column(
            "memory_producer_pr_review_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.add_column(
        "workspace_ai_settings",
        sa.Column(
            "memory_summarizer_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    op.execute(
        text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_graph_nodes_pr_review_finding
            ON graph_nodes (
                workspace_id,
                (properties->>'repo'),
                ((properties->>'pr_number')::int),
                (properties->>'file_path'),
                ((properties->>'line_number')::int)
            )
            WHERE node_type = 'pr_review_finding'
            """
        )
    )


def downgrade() -> None:
    op.execute(text("DROP INDEX IF EXISTS uq_graph_nodes_pr_review_finding"))
    op.drop_column("workspace_ai_settings", "memory_summarizer_enabled")
    op.drop_column("workspace_ai_settings", "memory_producer_pr_review_enabled")
    op.drop_column("workspace_ai_settings", "memory_producer_user_correction_enabled")
    op.drop_column("workspace_ai_settings", "memory_producer_agent_turn_enabled")
