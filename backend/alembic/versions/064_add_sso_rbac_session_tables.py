"""Add custom_roles, workspace_sessions tables and alter workspace_members.

Revision ID: 064_add_sso_rbac_session_tables
Revises: 063_add_ci_status_and_ai_review
Create Date: 2026-03-07

Phase 1 — Identity & Access foundation:

- AUTH-05: custom_roles table for workspace-defined RBAC roles
- AUTH-06: workspace_sessions table for session tracking and force-revocation
- AUTH-05: workspace_members.custom_role_id FK for custom role assignment
- AUTH-07: workspace_members.is_active for SCIM provisioning (deactivate, not delete)

Both new tables have full RLS:
  - ENABLE ROW LEVEL SECURITY + FORCE ROW LEVEL SECURITY
  - Workspace isolation via workspace_members membership check
  - service_role bypass for worker and admin operations

Note on RLS enum case: workspace_members.role stores UPPERCASE values
('OWNER', 'ADMIN', 'MEMBER', 'GUEST') per WorkspaceRole enum definition.
The is_deleted column uses the existing server_default='false' convention.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "064_add_sso_rbac_session_tables"
down_revision: str = "063_add_ci_status_and_ai_review"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create custom_roles, workspace_sessions; alter workspace_members."""

    # ------------------------------------------------------------------
    # 1. custom_roles table
    # ------------------------------------------------------------------
    op.create_table(
        "custom_roles",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("permissions", sa.dialects.postgresql.JSONB(), nullable=True),
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
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            server_default=text("false"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "workspace_id",
            "name",
            name="uq_custom_roles_workspace_name",
        ),
    )
    op.create_index(
        "ix_custom_roles_workspace_id",
        "custom_roles",
        ["workspace_id"],
    )

    # ------------------------------------------------------------------
    # 2. workspace_sessions table
    # ------------------------------------------------------------------
    op.create_table(
        "workspace_sessions",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # SHA-256 hex digest — 64 chars
        sa.Column("session_token_hash", sa.String(64), nullable=False),
        # IPv6-safe (max 45 chars)
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=text("now()"),
            nullable=False,
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            server_default=text("false"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_workspace_sessions_token_hash",
        "workspace_sessions",
        ["session_token_hash"],
    )
    op.create_index(
        "ix_workspace_sessions_user_id",
        "workspace_sessions",
        ["user_id"],
    )
    op.create_index(
        "ix_workspace_sessions_workspace_id",
        "workspace_sessions",
        ["workspace_id"],
    )

    # ------------------------------------------------------------------
    # 3. Alter workspace_members: add custom_role_id and is_active
    # ------------------------------------------------------------------
    op.add_column(
        "workspace_members",
        sa.Column(
            "custom_role_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("custom_roles.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_workspace_members_custom_role_id",
        "workspace_members",
        ["custom_role_id"],
    )
    op.add_column(
        "workspace_members",
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=text("true"),
            nullable=False,
        ),
    )

    # ------------------------------------------------------------------
    # 4. RLS — custom_roles
    # ------------------------------------------------------------------
    op.execute(text("ALTER TABLE custom_roles ENABLE ROW LEVEL SECURITY"))
    op.execute(text("ALTER TABLE custom_roles FORCE ROW LEVEL SECURITY"))

    # Workspace members can read roles in their workspace.
    # Only OWNER/ADMIN can mutate (enforced at application layer; RLS allows all members to read).
    op.execute(
        text(
            """
            CREATE POLICY "custom_roles_workspace_member"
            ON custom_roles
            FOR ALL
            TO authenticated
            USING (
                workspace_id IN (
                    SELECT wm.workspace_id
                    FROM workspace_members wm
                    WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                      AND wm.is_deleted = false
                )
            )
            WITH CHECK (
                workspace_id IN (
                    SELECT wm.workspace_id
                    FROM workspace_members wm
                    WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                      AND wm.is_deleted = false
                )
            )
            """
        )
    )

    op.execute(
        text(
            """
            CREATE POLICY "custom_roles_service_role"
            ON custom_roles
            FOR ALL
            TO service_role
            USING (true)
            WITH CHECK (true)
            """
        )
    )

    # ------------------------------------------------------------------
    # 5. RLS — workspace_sessions
    # ------------------------------------------------------------------
    op.execute(text("ALTER TABLE workspace_sessions ENABLE ROW LEVEL SECURITY"))
    op.execute(text("ALTER TABLE workspace_sessions FORCE ROW LEVEL SECURITY"))

    # Users can only see their own sessions; admins can list via service_role.
    op.execute(
        text(
            """
            CREATE POLICY "workspace_sessions_own_rows"
            ON workspace_sessions
            FOR ALL
            TO authenticated
            USING (
                user_id = current_setting('app.current_user_id', true)::uuid
            )
            WITH CHECK (
                user_id = current_setting('app.current_user_id', true)::uuid
            )
            """
        )
    )

    op.execute(
        text(
            """
            CREATE POLICY "workspace_sessions_service_role"
            ON workspace_sessions
            FOR ALL
            TO service_role
            USING (true)
            WITH CHECK (true)
            """
        )
    )


def downgrade() -> None:
    """Reverse migration 064: drop RLS, remove columns, drop tables."""

    # ------------------------------------------------------------------
    # RLS cleanup — workspace_sessions
    # ------------------------------------------------------------------
    op.execute(
        text('DROP POLICY IF EXISTS "workspace_sessions_service_role" ON workspace_sessions')
    )
    op.execute(text('DROP POLICY IF EXISTS "workspace_sessions_own_rows" ON workspace_sessions'))

    # ------------------------------------------------------------------
    # RLS cleanup — custom_roles
    # ------------------------------------------------------------------
    op.execute(text('DROP POLICY IF EXISTS "custom_roles_service_role" ON custom_roles'))
    op.execute(text('DROP POLICY IF EXISTS "custom_roles_workspace_member" ON custom_roles'))

    # ------------------------------------------------------------------
    # Remove additions to workspace_members
    # ------------------------------------------------------------------
    op.drop_index("ix_workspace_members_custom_role_id", table_name="workspace_members")
    op.drop_column("workspace_members", "is_active")
    op.drop_column("workspace_members", "custom_role_id")

    # ------------------------------------------------------------------
    # Drop workspace_sessions
    # ------------------------------------------------------------------
    op.drop_index("ix_workspace_sessions_workspace_id", table_name="workspace_sessions")
    op.drop_index("ix_workspace_sessions_user_id", table_name="workspace_sessions")
    op.drop_index("ix_workspace_sessions_token_hash", table_name="workspace_sessions")
    op.drop_table("workspace_sessions")

    # ------------------------------------------------------------------
    # Drop custom_roles (must come after workspace_members FK is removed)
    # ------------------------------------------------------------------
    op.drop_index("ix_custom_roles_workspace_id", table_name="custom_roles")
    op.drop_table("custom_roles")
