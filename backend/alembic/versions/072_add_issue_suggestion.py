"""Add issue_suggestion_dismissals table with RLS policies.

Revision ID: 072_add_issue_suggestion
Revises: 071_add_workspace_mcp_servers
Create Date: 2026-03-10

Phase 15 — Related Issues (RELISS-04):

1. Creates issue_suggestion_dismissals table with:
   - Standard WorkspaceScopedModel columns (id, workspace_id, created_at,
     updated_at, is_deleted, deleted_at)
   - user_id UUID NOT NULL FK → users.id (CASCADE)
   - source_issue_id UUID NOT NULL FK → issues.id (CASCADE)
   - target_issue_id UUID NOT NULL FK → issues.id (CASCADE)
   - dismissed_at TIMESTAMPTZ NOT NULL DEFAULT now()
2. Adds UNIQUE constraint on (user_id, source_issue_id, target_issue_id)
   to enforce idempotent dismiss operations.
3. Adds composite indexes:
   - (workspace_id, source_issue_id) — fast suggestions-filter lookup
   - (workspace_id, user_id) — fast per-user dismissal queries
4. Enables RLS with workspace isolation policy and service_role bypass.

Downgrade reverses all changes: drops policies, indexes, and table.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "072_add_issue_suggestion"
down_revision: str = "071_add_workspace_mcp_servers"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    """Create issue_suggestion_dismissals table and RLS policies."""

    op.create_table(
        "issue_suggestion_dismissals",
        # Primary key
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
            nullable=False,
        ),
        # Workspace scoping (FK with cascade delete)
        sa.Column(
            "workspace_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        # Soft delete
        sa.Column(
            "is_deleted",
            sa.Boolean,
            server_default=text("false"),
            nullable=False,
        ),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        # Dismissal fields
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_issue_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("issues.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_issue_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("issues.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "dismissed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        # Idempotency guard — same user cannot dismiss the same suggestion twice
        sa.UniqueConstraint(
            "user_id",
            "source_issue_id",
            "target_issue_id",
            name="uq_issue_suggestion_dismissals_user_source_target",
        ),
    )

    # Composite indexes for fast lookup patterns
    op.create_index(
        "ix_issue_suggestion_dismissals_workspace_source",
        "issue_suggestion_dismissals",
        ["workspace_id", "source_issue_id"],
    )
    op.create_index(
        "ix_issue_suggestion_dismissals_workspace_user",
        "issue_suggestion_dismissals",
        ["workspace_id", "user_id"],
    )
    # Individual column indexes (implicit from mapped_column(index=True) in model)
    op.create_index(
        "ix_issue_suggestion_dismissals_user_id",
        "issue_suggestion_dismissals",
        ["user_id"],
    )
    op.create_index(
        "ix_issue_suggestion_dismissals_source_issue_id",
        "issue_suggestion_dismissals",
        ["source_issue_id"],
    )

    # Enable RLS
    op.execute(
        text("ALTER TABLE issue_suggestion_dismissals ENABLE ROW LEVEL SECURITY")
    )
    op.execute(text("ALTER TABLE issue_suggestion_dismissals FORCE ROW LEVEL SECURITY"))

    # Workspace isolation policy: users see rows in workspaces they are members of
    op.execute(
        text(
            """
            CREATE POLICY "issue_suggestion_dismissals_workspace_isolation"
            ON issue_suggestion_dismissals
            FOR ALL
            USING (
                workspace_id IN (
                    SELECT wm.workspace_id
                    FROM workspace_members wm
                    WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                    AND wm.is_deleted = false
                    AND wm.role IN ('OWNER', 'ADMIN', 'MEMBER', 'GUEST')
                )
            )
            """
        )
    )

    # Service-role bypass policy (for admin/background operations)
    op.execute(
        text(
            """
            CREATE POLICY "issue_suggestion_dismissals_service_role"
            ON issue_suggestion_dismissals
            FOR ALL
            TO service_role
            USING (true)
            WITH CHECK (true)
            """
        )
    )


def downgrade() -> None:
    """Drop RLS policies, indexes, and issue_suggestion_dismissals table."""

    # Drop RLS policies
    op.execute(
        text(
            'DROP POLICY IF EXISTS "issue_suggestion_dismissals_workspace_isolation" '
            "ON issue_suggestion_dismissals"
        )
    )
    op.execute(
        text(
            'DROP POLICY IF EXISTS "issue_suggestion_dismissals_service_role" '
            "ON issue_suggestion_dismissals"
        )
    )

    # Drop indexes
    op.drop_index(
        "ix_issue_suggestion_dismissals_source_issue_id",
        table_name="issue_suggestion_dismissals",
    )
    op.drop_index(
        "ix_issue_suggestion_dismissals_user_id",
        table_name="issue_suggestion_dismissals",
    )
    op.drop_index(
        "ix_issue_suggestion_dismissals_workspace_user",
        table_name="issue_suggestion_dismissals",
    )
    op.drop_index(
        "ix_issue_suggestion_dismissals_workspace_source",
        table_name="issue_suggestion_dismissals",
    )

    # Drop table
    op.drop_table("issue_suggestion_dismissals")
