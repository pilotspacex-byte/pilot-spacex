"""Add pm_block_insights table and PM block schema enhancements.

T-223: pm_block_insights — AI-generated insights for PM blocks.
  - UUID PK, workspace_id (RLS), block_id, block_type, insight_type
  - severity enum (green/yellow/red), title, analysis, references JSONB
  - suggested_actions JSONB, confidence FLOAT (0-1), dismissed BOOL
  - SoftDeleteMixin: is_deleted, deleted_at
  - Indexes: (block_id, dismissed), workspace_id, severity, is_deleted
  - RLS: workspace isolation via workspace_id + workspace_members join

T-224: issues.estimate_hours — DECIMAL(6,1) for AI time estimates.

T-225: workspace_members.weekly_available_hours — DECIMAL(5,1) DEFAULT 40
  for capacity planning.

Revision ID: 045_add_pm_block_insights
Revises: 044_add_note_templates
Create Date: 2026-02-19
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID

from alembic import op

revision = "045_add_pm_block_insights"
down_revision = "044_add_note_templates"
branch_labels = None
depends_on = None

# Enum names (must be created before table)
_BLOCK_TYPE_ENUM = "pm_block_type_enum"
_SEVERITY_ENUM = "insight_severity_enum"


def upgrade() -> None:
    # ── Enum types ──────────────────────────────────────────────────────────
    op.execute(f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = '{_BLOCK_TYPE_ENUM}') THEN
                CREATE TYPE {_BLOCK_TYPE_ENUM} AS ENUM (
                    'sprint_board',
                    'dependency_map',
                    'capacity_plan',
                    'release_notes'
                );
            END IF;
        END$$;
    """)

    op.execute(f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = '{_SEVERITY_ENUM}') THEN
                CREATE TYPE {_SEVERITY_ENUM} AS ENUM (
                    'green',
                    'yellow',
                    'red'
                );
            END IF;
        END$$;
    """)

    # ── T-223: pm_block_insights table ──────────────────────────────────────
    op.create_table(
        "pm_block_insights",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "workspace_id",
            UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("block_id", sa.String(), nullable=False),
        sa.Column(
            "block_type",
            ENUM(
                "sprint_board",
                "dependency_map",
                "capacity_plan",
                "release_notes",
                name=_BLOCK_TYPE_ENUM,
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("insight_type", sa.String(), nullable=False),
        sa.Column(
            "severity",
            ENUM(
                "green",
                "yellow",
                "red",
                name=_SEVERITY_ENUM,
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("analysis", sa.Text(), nullable=False),
        sa.Column("references", JSONB, nullable=False, server_default="[]"),
        sa.Column("suggested_actions", JSONB, nullable=False, server_default="[]"),
        sa.Column(
            "confidence",
            sa.Float(),
            nullable=False,
            # CHECK enforced below; SQLAlchemy Column doesn't support inline CHECK
        ),
        sa.Column("dismissed", sa.Boolean(), nullable=False, server_default="false"),
        # SoftDeleteMixin
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        # Confidence range constraint
        sa.CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0", name="ck_pbi_confidence_range"
        ),
    )

    # Indexes
    op.create_index(
        "idx_pbi_block_dismissed",
        "pm_block_insights",
        ["block_id", "dismissed"],
        if_not_exists=True,
    )
    op.create_index(
        "idx_pbi_workspace",
        "pm_block_insights",
        ["workspace_id"],
        if_not_exists=True,
    )
    op.create_index(
        "idx_pbi_severity",
        "pm_block_insights",
        ["severity"],
        if_not_exists=True,
    )
    op.create_index(
        "idx_pbi_is_deleted",
        "pm_block_insights",
        ["is_deleted"],
        if_not_exists=True,
    )

    # RLS: row-level security
    op.execute("ALTER TABLE pm_block_insights ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE pm_block_insights FORCE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY pm_block_insights_select ON pm_block_insights
        FOR SELECT
        USING (
            workspace_id IN (
                SELECT workspace_id FROM workspace_members
                WHERE user_id = current_setting('app.current_user_id', true)::uuid
            )
        )
    """)

    op.execute("""
        CREATE POLICY pm_block_insights_insert ON pm_block_insights
        FOR INSERT
        WITH CHECK (
            workspace_id IN (
                SELECT workspace_id FROM workspace_members
                WHERE user_id = current_setting('app.current_user_id', true)::uuid
            )
        )
    """)

    op.execute("""
        CREATE POLICY pm_block_insights_update ON pm_block_insights
        FOR UPDATE
        USING (
            workspace_id IN (
                SELECT workspace_id FROM workspace_members
                WHERE user_id = current_setting('app.current_user_id', true)::uuid
            )
        )
    """)

    op.execute("""
        CREATE POLICY pm_block_insights_delete ON pm_block_insights
        FOR DELETE
        USING (
            workspace_id IN (
                SELECT workspace_id FROM workspace_members
                WHERE user_id = current_setting('app.current_user_id', true)::uuid
                AND role IN ('OWNER', 'ADMIN')
            )
        )
    """)

    # ── T-224: issues.estimate_hours ────────────────────────────────────────
    op.add_column(
        "issues",
        sa.Column("estimate_hours", sa.Numeric(6, 1), nullable=True),
    )

    # ── T-225: workspace_members.weekly_available_hours ──────────────────
    op.add_column(
        "workspace_members",
        sa.Column(
            "weekly_available_hours",
            sa.Numeric(5, 1),
            nullable=True,
            server_default="40",
        ),
    )


def downgrade() -> None:
    op.drop_column("workspace_members", "weekly_available_hours")
    op.drop_column("issues", "estimate_hours")

    op.execute("DROP TABLE IF EXISTS pm_block_insights CASCADE")

    op.execute(f"DROP TYPE IF EXISTS {_SEVERITY_ENUM}")
    op.execute(f"DROP TYPE IF EXISTS {_BLOCK_TYPE_ENUM}")
