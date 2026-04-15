"""Data foundations: source_note_id FK on issues + batch_runs + batch_run_issues tables.

Phase 73 Plan 01 — schema foundations for v2.0 Autonomous SDLC milestone.

Changes:
  - issues.source_note_id: UUID FK → notes(id) ON DELETE SET NULL (note-to-issue traceability)
  - batch_runs: workspace-scoped table for sprint batch execution tracking
  - batch_run_issues: per-issue tracking within a batch run

RLS: Both new tables have workspace isolation + service_role bypass policies.

Revision ID: 110_data_foundations_source_note_batch_runs
Revises: 109_security_hardening_rls_and_backfill
Create Date: 2026-04-15
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "110_data_foundations_source_note_batch_runs"
down_revision: str | None = "109_security_hardening_rls_and_backfill"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Apply data foundations schema changes."""

    # -------------------------------------------------------------------------
    # Part A — source_note_id on issues
    # -------------------------------------------------------------------------
    op.add_column(
        "issues",
        sa.Column(
            "source_note_id",
            UUID(as_uuid=True),
            sa.ForeignKey("notes.id", ondelete="SET NULL", name="fk_issues_source_note_id"),
            nullable=True,
        ),
    )
    op.create_index("ix_issues_source_note_id", "issues", ["source_note_id"])

    # -------------------------------------------------------------------------
    # Part B — batch_run_status enum
    # -------------------------------------------------------------------------
    op.execute(
        text(
            "CREATE TYPE batch_run_status AS ENUM "
            "('pending', 'running', 'paused', 'completed', 'failed')"
        )
    )

    # -------------------------------------------------------------------------
    # Part C — batch_run_issue_status enum
    # -------------------------------------------------------------------------
    op.execute(
        text(
            "CREATE TYPE batch_run_issue_status AS ENUM "
            "('pending', 'queued', 'running', 'completed', 'failed', 'cancelled')"
        )
    )

    # -------------------------------------------------------------------------
    # Part D — batch_runs table
    # -------------------------------------------------------------------------
    op.execute(
        text(
            """
            CREATE TABLE batch_runs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                cycle_id UUID NOT NULL REFERENCES cycles(id) ON DELETE CASCADE,
                status batch_run_status NOT NULL DEFAULT 'pending',
                started_at TIMESTAMP WITH TIME ZONE,
                completed_at TIMESTAMP WITH TIME ZONE,
                triggered_by_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                total_issues INTEGER NOT NULL DEFAULT 0,
                completed_issues INTEGER NOT NULL DEFAULT 0,
                failed_issues INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                is_deleted BOOLEAN NOT NULL DEFAULT FALSE
            )
            """
        )
    )
    op.create_index("ix_batch_runs_workspace_id", "batch_runs", ["workspace_id"])
    op.create_index("ix_batch_runs_cycle_id", "batch_runs", ["cycle_id"])
    op.create_index("ix_batch_runs_status", "batch_runs", ["status"])

    # -------------------------------------------------------------------------
    # Part E — batch_run_issues table
    # -------------------------------------------------------------------------
    op.execute(
        text(
            """
            CREATE TABLE batch_run_issues (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                batch_run_id UUID NOT NULL REFERENCES batch_runs(id) ON DELETE CASCADE,
                issue_id UUID NOT NULL REFERENCES issues(id) ON DELETE CASCADE,
                status batch_run_issue_status NOT NULL DEFAULT 'pending',
                execution_order INTEGER NOT NULL DEFAULT 0,
                worktree_path TEXT,
                pr_url TEXT,
                started_at TIMESTAMP WITH TIME ZONE,
                completed_at TIMESTAMP WITH TIME ZONE,
                error_message TEXT,
                cost_cents INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
                CONSTRAINT uq_batch_run_issues_run_issue UNIQUE (batch_run_id, issue_id)
            )
            """
        )
    )
    op.create_index("ix_batch_run_issues_batch_run_id", "batch_run_issues", ["batch_run_id"])
    op.create_index("ix_batch_run_issues_issue_id", "batch_run_issues", ["issue_id"])
    op.create_index("ix_batch_run_issues_status", "batch_run_issues", ["status"])

    # -------------------------------------------------------------------------
    # Part F — RLS policies for batch_runs
    # -------------------------------------------------------------------------
    op.execute(text("ALTER TABLE batch_runs ENABLE ROW LEVEL SECURITY"))
    op.execute(text("ALTER TABLE batch_runs FORCE ROW LEVEL SECURITY"))
    op.execute(
        text(
            """
            CREATE POLICY "batch_runs_workspace_isolation" ON batch_runs
              USING (workspace_id IN (
                SELECT wm.workspace_id FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                AND wm.role IN ('OWNER', 'ADMIN', 'MEMBER')
              ))
            """
        )
    )
    op.execute(
        text(
            """
            CREATE POLICY "batch_runs_service_role_bypass" ON batch_runs
              FOR ALL TO service_role USING (true) WITH CHECK (true)
            """
        )
    )

    # -------------------------------------------------------------------------
    # Part F — RLS policies for batch_run_issues
    # -------------------------------------------------------------------------
    op.execute(text("ALTER TABLE batch_run_issues ENABLE ROW LEVEL SECURITY"))
    op.execute(text("ALTER TABLE batch_run_issues FORCE ROW LEVEL SECURITY"))
    op.execute(
        text(
            """
            CREATE POLICY "batch_run_issues_workspace_isolation" ON batch_run_issues
              USING (workspace_id IN (
                SELECT wm.workspace_id FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                AND wm.role IN ('OWNER', 'ADMIN', 'MEMBER')
              ))
            """
        )
    )
    op.execute(
        text(
            """
            CREATE POLICY "batch_run_issues_service_role_bypass" ON batch_run_issues
              FOR ALL TO service_role USING (true) WITH CHECK (true)
            """
        )
    )


def downgrade() -> None:
    """Reverse data foundations schema changes."""

    # Drop batch_run_issues first (references batch_runs)
    op.drop_table("batch_run_issues")
    op.drop_table("batch_runs")

    # Drop enum types
    op.execute(text("DROP TYPE IF EXISTS batch_run_issue_status"))
    op.execute(text("DROP TYPE IF EXISTS batch_run_status"))

    # Drop source_note_id from issues
    op.drop_index("ix_issues_source_note_id", table_name="issues")
    op.drop_constraint("fk_issues_source_note_id", "issues", type_="foreignkey")
    op.drop_column("issues", "source_note_id")
