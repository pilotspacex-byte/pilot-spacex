"""Add workspace_role_skills table with RLS policies.

Revision ID: 073_add_workspace_role_skills
Revises: 072_add_issue_suggestion
Create Date: 2026-03-10

Phase 16 — Workspace Role Skills (WRSKL-01..04):

1. Creates workspace_role_skills table with:
   - Standard WorkspaceScopedModel columns (id, workspace_id, created_at,
     updated_at, is_deleted, deleted_at)
   - role_type VARCHAR(50) NOT NULL — SDLC role identifier
   - role_name VARCHAR(100) NOT NULL — human-readable display name
   - skill_content TEXT NOT NULL (max 15000 chars) — SKILL.md markdown
   - experience_description TEXT NULL — optional AI generation input
   - is_active BOOLEAN NOT NULL DEFAULT false — approval gate (WRSKL-02)
   - created_by UUID NULL FK → users.id (SET NULL on user delete)
2. Adds partial unique index on (workspace_id, role_type) WHERE is_deleted = false
   to allow re-create after soft-delete without uniqueness violations (WRSKL-01).
3. Adds composite index on (workspace_id, is_active) for materializer hot-path.
4. Enables RLS with workspace isolation policy and service_role bypass.

Downgrade reverses all changes: drops policies, indexes, and table.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "073_add_workspace_role_skills"
down_revision: str = "072_add_issue_suggestion"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    """Create workspace_role_skills table, indexes, and RLS policies."""

    op.create_table(
        "workspace_role_skills",
        # Primary key
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
            nullable=False,
        ),
        # Workspace scoping (FK with cascade delete)
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Business fields
        sa.Column(
            "role_type",
            sa.String(50),
            nullable=False,
        ),
        sa.Column(
            "role_name",
            sa.String(100),
            nullable=False,
        ),
        sa.Column(
            "skill_content",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "experience_description",
            sa.Text(),
            nullable=True,
        ),
        # Approval gate: new skills inactive until admin activates (WRSKL-02)
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=text("false"),
            nullable=False,
        ),
        # Creator reference (nullable: SET NULL when user is deleted)
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
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
            sa.Boolean(),
            server_default=text("false"),
            nullable=False,
        ),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        # Content length guard
        sa.CheckConstraint(
            "char_length(skill_content) <= 15000",
            name="ck_workspace_role_skills_content_length",
        ),
        sa.CheckConstraint(
            "char_length(role_name) <= 100",
            name="ck_workspace_role_skills_role_name_length",
        ),
    )

    # Partial unique index: one active skill per workspace per role_type.
    # Soft-deleted rows (is_deleted = true) are excluded — allows re-create
    # after soft-delete without a uniqueness violation.
    op.execute(
        text(
            "CREATE UNIQUE INDEX uq_workspace_role_skills_workspace_role_active "
            "ON workspace_role_skills (workspace_id, role_type) WHERE is_deleted = false"
        )
    )

    # Hot-path composite index: materializer get_active_by_workspace query
    op.create_index(
        "ix_workspace_role_skills_workspace_active",
        "workspace_role_skills",
        ["workspace_id", "is_active"],
    )

    # workspace_id column index (implicit from WorkspaceScopedMixin index=True)
    op.create_index(
        "ix_workspace_role_skills_workspace_id",
        "workspace_role_skills",
        ["workspace_id"],
    )

    # Enable RLS
    op.execute(text("ALTER TABLE workspace_role_skills ENABLE ROW LEVEL SECURITY"))
    op.execute(text("ALTER TABLE workspace_role_skills FORCE ROW LEVEL SECURITY"))

    # Workspace isolation policy: authenticated users see rows in their workspace
    op.execute(
        text(
            """
            CREATE POLICY "workspace_role_skills_workspace_isolation"
            ON workspace_role_skills
            FOR ALL
            TO authenticated
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
            CREATE POLICY "workspace_role_skills_service_role"
            ON workspace_role_skills
            FOR ALL
            TO service_role
            USING (true)
            WITH CHECK (true)
            """
        )
    )


def downgrade() -> None:
    """Drop RLS policies, indexes, and workspace_role_skills table."""

    # Drop RLS policies
    op.execute(
        text(
            'DROP POLICY IF EXISTS "workspace_role_skills_service_role" ON workspace_role_skills'
        )
    )
    op.execute(
        text(
            'DROP POLICY IF EXISTS "workspace_role_skills_workspace_isolation" '
            "ON workspace_role_skills"
        )
    )

    # Drop indexes
    op.drop_index(
        "ix_workspace_role_skills_workspace_id",
        table_name="workspace_role_skills",
    )
    op.drop_index(
        "ix_workspace_role_skills_workspace_active",
        table_name="workspace_role_skills",
    )
    op.execute(
        text("DROP INDEX IF EXISTS uq_workspace_role_skills_workspace_role_active")
    )

    # Drop table
    op.drop_table("workspace_role_skills")
