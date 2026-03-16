"""Add workspace_ai_policy table.

Revision ID: 068_add_workspace_ai_policy
Revises: 067_workspace_encryption_quota
Create Date: 2026-03-08

Phase 4 — AI Governance (AIGOV-01):

workspace_ai_policy table:
  - Stores per-role x per-action-type approval policy overrides
  - Absence of a row means fall back to hardcoded ApprovalLevel defaults (DD-003)
  - RLS: OWNER + ADMIN can read; OWNER only can write
  - service_role bypass for backend service operations

RLS Design:
  - READ: workspace_members with role IN ('OWNER', 'ADMIN')
  - WRITE (ALL): workspace_members with role = 'OWNER'
  - service_role: full bypass
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic
revision: str = "068_add_workspace_ai_policy"
down_revision: str = "067_workspace_encryption_quota"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Create workspace_ai_policy table with RLS."""

    # ------------------------------------------------------------------
    # Step 1: CREATE TABLE workspace_ai_policy
    # ------------------------------------------------------------------
    op.create_table(
        "workspace_ai_policy",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "role",
            sa.String(20),
            nullable=False,
        ),
        sa.Column(
            "action_type",
            sa.String(100),
            nullable=False,
        ),
        sa.Column(
            "requires_approval",
            sa.Boolean,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=text("now()"),
            nullable=False,
        ),
        # SoftDeleteMixin columns (from WorkspaceScopedModel -> BaseModel)
        sa.Column(
            "is_deleted",
            sa.Boolean,
            nullable=False,
            server_default=text("false"),
        ),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # Composite index for efficient per-workspace-role lookups
    op.create_index(
        "ix_workspace_ai_policy_workspace_role",
        "workspace_ai_policy",
        ["workspace_id", "role"],
    )

    # Unique constraint: one policy row per (workspace, role, action_type)
    op.create_unique_constraint(
        "uq_workspace_ai_policy_workspace_role_action",
        "workspace_ai_policy",
        ["workspace_id", "role", "action_type"],
    )

    # ------------------------------------------------------------------
    # Step 2: Enable RLS
    # ------------------------------------------------------------------
    op.execute(text("ALTER TABLE workspace_ai_policy ENABLE ROW LEVEL SECURITY"))
    op.execute(text("ALTER TABLE workspace_ai_policy FORCE ROW LEVEL SECURITY"))

    # READ: OWNER and ADMIN can view policy rows
    op.execute(
        text(
            """
            CREATE POLICY "workspace_ai_policy_read_workspace_members"
            ON workspace_ai_policy FOR SELECT
            USING (
                workspace_id IN (
                    SELECT wm.workspace_id FROM workspace_members wm
                    WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                    AND wm.role IN ('OWNER', 'ADMIN')
                    AND wm.is_deleted = false
                )
            )
        """
        )
    )

    # WRITE: OWNER only can create/update/delete policy rows
    op.execute(
        text(
            """
            CREATE POLICY "workspace_ai_policy_write_owner_only"
            ON workspace_ai_policy FOR ALL
            USING (
                workspace_id IN (
                    SELECT wm.workspace_id FROM workspace_members wm
                    WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                    AND wm.role = 'OWNER'
                    AND wm.is_deleted = false
                )
            )
        """
        )
    )

    # service_role bypass — backend service operations bypass RLS
    op.execute(
        text(
            """
            CREATE POLICY "workspace_ai_policy_service_role_bypass"
            ON workspace_ai_policy FOR ALL
            TO service_role
            USING (true)
            WITH CHECK (true)
        """
        )
    )


def downgrade() -> None:
    """Drop workspace_ai_policy table and all associated objects."""

    op.execute(
        text(
            'DROP POLICY IF EXISTS "workspace_ai_policy_service_role_bypass" ON workspace_ai_policy'
        )
    )
    op.execute(
        text(
            'DROP POLICY IF EXISTS "workspace_ai_policy_write_owner_only" ON workspace_ai_policy'
        )
    )
    op.execute(
        text(
            'DROP POLICY IF EXISTS "workspace_ai_policy_read_workspace_members" '
            "ON workspace_ai_policy"
        )
    )
    op.drop_table("workspace_ai_policy")
