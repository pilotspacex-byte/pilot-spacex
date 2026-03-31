"""Add project RBAC schema, RLS policies, invitation changes.

Merged from migrations 100–104:
  - 100_project_rbac_schema: project_members table; is_archived/archived_at on projects;
    last_active_project_id on workspace_members; project_assignments on workspace_invitations.
  - 101_project_rbac_rls: RLS policies for project_members.
  - 102_workspace_invitation_supabase: supabase_invite_sent_at on workspace_invitations.
  - 103_project_members_add_deleted_at: deleted_at column on project_members.
  - 104_invitation_status_revoked: 'revoked' value added to invitation_status enum.

Revision ID: 104_invitation_status_revoked
Revises: 103_fix_invitation_unique_constraint
Create Date: 2026-03-28
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "100_project_rbac_schema"
down_revision: str | None = "103_fix_invitation_unique_constraint"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    # ── 1. Create project_members table ──────────────────────────────────────
    op.create_table(
        "project_members",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "assigned_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_project_members_project_id", "project_members", ["project_id"])
    op.create_index("ix_project_members_user_id", "project_members", ["user_id"])
    op.create_index("ix_project_members_is_active", "project_members", ["is_active"])
    # Partial unique index: only one active membership per (project, user) — allows re-assignment after soft-delete
    op.create_index(
        "uq_project_members_project_user_active",
        "project_members",
        ["project_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )

    # ── 2. projects: add is_archived / archived_at ────────────────────────────
    op.add_column(
        "projects",
        sa.Column(
            "is_archived",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "projects",
        sa.Column(
            "archived_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_index("ix_projects_is_archived", "projects", ["is_archived"])

    # ── 3. workspace_members: add last_active_project_id ─────────────────────
    op.add_column(
        "workspace_members",
        sa.Column(
            "last_active_project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_workspace_members_last_active_project_id",
        "workspace_members",
        ["last_active_project_id"],
    )

    # ── 4. workspace_invitations: add project_assignments JSONB ───────────────
    op.add_column(
        "workspace_invitations",
        sa.Column(
            "project_assignments",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )

    # ── 5. RLS policies for project_members ──────────────────────────────────
    op.execute("ALTER TABLE project_members ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE project_members FORCE ROW LEVEL SECURITY")

    op.execute(
        """
        CREATE POLICY "project_members_select"
        ON project_members
        FOR SELECT
        USING (
            project_id IN (
                SELECT p.id
                FROM projects p
                INNER JOIN workspace_members wm
                    ON wm.workspace_id = p.workspace_id
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                  AND wm.is_deleted = false
                  AND wm.is_active = true
                  AND p.is_deleted = false
            )
        )
    """
    )

    op.execute(
        """
        CREATE POLICY "project_members_insert"
        ON project_members
        FOR INSERT
        WITH CHECK (
            project_id IN (
                SELECT p.id
                FROM projects p
                INNER JOIN workspace_members wm
                    ON wm.workspace_id = p.workspace_id
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                  AND wm.role IN ('ADMIN', 'OWNER')
                  AND wm.is_deleted = false
                  AND wm.is_active = true
                  AND p.is_deleted = false
            )
        )
    """
    )

    op.execute(
        """
        CREATE POLICY "project_members_update"
        ON project_members
        FOR UPDATE
        USING (
            project_id IN (
                SELECT p.id
                FROM projects p
                INNER JOIN workspace_members wm
                    ON wm.workspace_id = p.workspace_id
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                  AND wm.role IN ('ADMIN', 'OWNER')
                  AND wm.is_deleted = false
                  AND wm.is_active = true
                  AND p.is_deleted = false
            )
        )
        WITH CHECK (
            project_id IN (
                SELECT p.id
                FROM projects p
                INNER JOIN workspace_members wm
                    ON wm.workspace_id = p.workspace_id
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                  AND wm.role IN ('ADMIN', 'OWNER')
                  AND wm.is_deleted = false
                  AND wm.is_active = true
                  AND p.is_deleted = false
            )
        )
    """
    )

    op.execute(
        """
        CREATE POLICY "project_members_delete"
        ON project_members
        FOR DELETE
        USING (
            project_id IN (
                SELECT p.id
                FROM projects p
                INNER JOIN workspace_members wm
                    ON wm.workspace_id = p.workspace_id
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                  AND wm.role IN ('ADMIN', 'OWNER')
                  AND wm.is_deleted = false
                  AND wm.is_active = true
                  AND p.is_deleted = false
            )
        )
    """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_project_members_project_user_active
        ON project_members (project_id, user_id)
        WHERE is_active = true AND is_deleted = false
    """
    )

    # ── 6. workspace_invitations: add supabase_invite_sent_at ────────────────
    op.add_column(
        "workspace_invitations",
        sa.Column(
            "supabase_invite_sent_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment="Set when Supabase inviteUserByEmail() is called; prevents duplicate magic links on retry",
        ),
    )

    # ── 7. invitation_status enum: add 'revoked' value ───────────────────────
    op.execute("ALTER TYPE invitation_status ADD VALUE IF NOT EXISTS 'revoked'")


def downgrade() -> None:
    # Revert enum (data migration only; PostgreSQL cannot DROP enum values)
    op.execute(
        "UPDATE workspace_invitations SET status = 'cancelled' WHERE status = 'revoked'"
    )

    # Remove supabase_invite_sent_at
    op.drop_column("workspace_invitations", "supabase_invite_sent_at")

    # Remove RLS policies and disable RLS
    op.execute("DROP INDEX IF EXISTS ix_project_members_project_user_active")
    op.execute('DROP POLICY IF EXISTS "project_members_delete" ON project_members')
    op.execute('DROP POLICY IF EXISTS "project_members_update" ON project_members')
    op.execute('DROP POLICY IF EXISTS "project_members_insert" ON project_members')
    op.execute('DROP POLICY IF EXISTS "project_members_select" ON project_members')
    op.execute("ALTER TABLE project_members DISABLE ROW LEVEL SECURITY")

    # Remove columns added to existing tables
    op.drop_column("workspace_invitations", "project_assignments")

    op.drop_index(
        "ix_workspace_members_last_active_project_id",
        table_name="workspace_members",
    )
    op.drop_column("workspace_members", "last_active_project_id")

    op.drop_index("ix_projects_is_archived", table_name="projects")
    op.drop_column("projects", "archived_at")
    op.drop_column("projects", "is_archived")

    # Drop project_members table
    op.drop_index("uq_project_members_project_user_active", table_name="project_members")
    op.drop_index("ix_project_members_is_active", table_name="project_members")
    op.drop_index("ix_project_members_user_id", table_name="project_members")
    op.drop_index("ix_project_members_project_id", table_name="project_members")
    op.drop_table("project_members")
