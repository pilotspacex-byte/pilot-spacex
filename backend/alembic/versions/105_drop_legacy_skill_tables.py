"""Drop legacy skill tables after migrating data to skill_templates/user_skills.

Revision ID: 105_drop_legacy_skill_tables
Revises: 104_add_marketplace_tables
Create Date: 2026-03-29

Phase 57 -- Skill Consolidation (CON-01):

Migrates data from legacy tables to the unified skill system:
1. workspace_role_skills -> skill_templates (INSERT ON CONFLICT DO NOTHING)
2. user_role_skills -> user_skills (via matched skill_templates)
3. Drops user_role_skills, workspace_role_skills, role_templates

Downgrade recreates empty tables with original schemas and RLS policies.
Data migration is NOT reversed -- only table structure is restored.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "105_drop_legacy_skill_tables"
down_revision: str = "104_add_marketplace_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Migrate legacy skill data to unified tables, then drop legacy tables."""

    # ------------------------------------------------------------------
    # Step 1: Migrate workspace_role_skills -> skill_templates
    # ------------------------------------------------------------------
    # Maps: role_name -> name, role_type || ' workspace skill' -> description,
    # skill_content -> skill_content, source='workspace', is_active preserved.
    # ON CONFLICT (workspace_id, name) DO NOTHING skips duplicates.
    op.execute(
        text(
            """
            INSERT INTO skill_templates (
                id, workspace_id, name, description, skill_content,
                icon, sort_order, source, role_type, is_active,
                created_by, is_deleted, deleted_at, created_at, updated_at
            )
            SELECT
                gen_random_uuid(),
                wrs.workspace_id,
                wrs.role_name,
                wrs.role_type || ' workspace skill',
                wrs.skill_content,
                'Wand2',
                0,
                'workspace',
                wrs.role_type,
                wrs.is_active,
                wrs.created_by,
                wrs.is_deleted,
                wrs.deleted_at,
                wrs.created_at,
                wrs.updated_at
            FROM workspace_role_skills wrs
            ON CONFLICT (workspace_id, name)
            WHERE is_deleted = false
            DO NOTHING
            """
        )
    )

    # ------------------------------------------------------------------
    # Step 2: Migrate user_role_skills -> user_skills
    # ------------------------------------------------------------------
    # For each user_role_skill, find the matching skill_template by
    # workspace_id + role_name (name). If no match exists, the row is
    # inserted with template_id = NULL.
    # ON CONFLICT DO NOTHING skips duplicates.
    op.execute(
        text(
            """
            INSERT INTO user_skills (
                id, user_id, workspace_id, template_id,
                skill_content, experience_description, skill_name,
                tags, usage, is_active,
                is_deleted, deleted_at, created_at, updated_at
            )
            SELECT
                gen_random_uuid(),
                urs.user_id,
                urs.workspace_id,
                st.id,
                urs.skill_content,
                urs.experience_description,
                urs.role_name,
                urs.tags,
                urs.usage,
                CASE WHEN urs.is_primary THEN true ELSE false END,
                urs.is_deleted,
                urs.deleted_at,
                urs.created_at,
                urs.updated_at
            FROM user_role_skills urs
            LEFT JOIN skill_templates st
                ON st.workspace_id = urs.workspace_id
                AND st.name = urs.role_name
                AND st.is_deleted = false
            ON CONFLICT DO NOTHING
            """
        )
    )

    # ------------------------------------------------------------------
    # Step 3: Drop legacy tables in dependency order
    # ------------------------------------------------------------------
    # user_role_skills depends on users/workspaces (no FK to other legacy tables)
    # workspace_role_skills depends on workspaces/users
    # role_templates has no FK dependencies from other tables

    # Drop RLS policies first (required before DROP TABLE on PG with RLS enabled)
    op.execute(text('DROP POLICY IF EXISTS "user_role_skills_select" ON user_role_skills'))
    op.execute(text('DROP POLICY IF EXISTS "user_role_skills_modify" ON user_role_skills'))
    op.execute(
        text(
            'DROP POLICY IF EXISTS "workspace_role_skills_workspace_isolation" '
            "ON workspace_role_skills"
        )
    )
    op.execute(
        text('DROP POLICY IF EXISTS "workspace_role_skills_service_role" ON workspace_role_skills')
    )
    op.execute(text('DROP POLICY IF EXISTS "role_templates_select" ON role_templates'))

    op.drop_table("user_role_skills")
    op.drop_table("workspace_role_skills")
    op.drop_table("role_templates")


def downgrade() -> None:
    """Recreate legacy skill tables with original schemas and RLS policies.

    NOTE: Data migration is NOT reversed. Tables are recreated empty.
    """

    # ------------------------------------------------------------------
    # 1. Recreate role_templates table
    # ------------------------------------------------------------------
    op.create_table(
        "role_templates",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("role_type", sa.String(50), nullable=False, unique=True),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("default_skill_content", sa.Text(), nullable=False),
        sa.Column("icon", sa.String(50), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default=text("1")),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_role_templates_role_type", "role_templates", ["role_type"], unique=True)
    op.create_index("ix_role_templates_sort_order", "role_templates", ["sort_order"])

    # RLS for role_templates
    op.execute(text("ALTER TABLE role_templates ENABLE ROW LEVEL SECURITY"))
    op.execute(
        text(
            """
            CREATE POLICY "role_templates_select" ON role_templates
            FOR SELECT USING (
                current_setting('app.current_user_id', true)::uuid IS NOT NULL
            )
            """
        )
    )

    # ------------------------------------------------------------------
    # 2. Recreate workspace_role_skills table
    # ------------------------------------------------------------------
    op.create_table(
        "workspace_role_skills",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role_type", sa.String(50), nullable=False),
        sa.Column("role_name", sa.String(100), nullable=False),
        sa.Column("skill_content", sa.Text(), nullable=False),
        sa.Column("experience_description", sa.Text(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=False, server_default=text("'[]'")),
        sa.Column("usage", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=text("false"), nullable=False),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("is_deleted", sa.Boolean(), server_default=text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "char_length(skill_content) <= 15000",
            name="ck_workspace_role_skills_content_length",
        ),
        sa.CheckConstraint(
            "char_length(role_name) <= 100",
            name="ck_workspace_role_skills_role_name_length",
        ),
    )
    op.execute(
        text(
            "CREATE UNIQUE INDEX uq_workspace_role_skills_workspace_role_active "
            "ON workspace_role_skills (workspace_id, role_type) WHERE is_deleted = false"
        )
    )
    op.create_index(
        "ix_workspace_role_skills_workspace_active",
        "workspace_role_skills",
        ["workspace_id", "is_active"],
    )
    op.create_index(
        "ix_workspace_role_skills_workspace_id",
        "workspace_role_skills",
        ["workspace_id"],
    )

    # RLS for workspace_role_skills
    op.execute(text("ALTER TABLE workspace_role_skills ENABLE ROW LEVEL SECURITY"))
    op.execute(text("ALTER TABLE workspace_role_skills FORCE ROW LEVEL SECURITY"))
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

    # ------------------------------------------------------------------
    # 3. Recreate user_role_skills table
    # ------------------------------------------------------------------
    op.create_table(
        "user_role_skills",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role_type", sa.String(50), nullable=False),
        sa.Column("role_name", sa.String(100), nullable=False),
        sa.Column("skill_content", sa.Text(), nullable=False),
        sa.Column("experience_description", sa.Text(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=False, server_default=text("'[]'")),
        sa.Column("usage", sa.Text(), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=text("false")),
        sa.Column("template_version", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "user_id", "workspace_id", "role_type", name="uq_user_role_skills_user_workspace_role"
        ),
        sa.CheckConstraint(
            "char_length(skill_content) <= 15000",
            name="ck_user_role_skills_skill_content_length",
        ),
        sa.CheckConstraint(
            "char_length(role_name) <= 100",
            name="ck_user_role_skills_role_name_length",
        ),
    )
    op.create_index(
        "ix_user_role_skills_user_workspace",
        "user_role_skills",
        ["user_id", "workspace_id"],
    )
    op.create_index(
        "ix_user_role_skills_workspace",
        "user_role_skills",
        ["workspace_id"],
    )

    # RLS for user_role_skills
    op.execute(text("ALTER TABLE user_role_skills ENABLE ROW LEVEL SECURITY"))
    op.execute(
        text(
            """
            CREATE POLICY "user_role_skills_select" ON user_role_skills
            FOR SELECT USING (
                user_id = current_setting('app.current_user_id', true)::uuid
                OR workspace_id IN (
                    SELECT wm.workspace_id FROM workspace_members wm
                    WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                    AND wm.role IN ('OWNER', 'ADMIN')
                    AND wm.is_deleted = false
                )
            )
            """
        )
    )
    op.execute(
        text(
            """
            CREATE POLICY "user_role_skills_modify" ON user_role_skills
            FOR ALL USING (
                user_id = current_setting('app.current_user_id', true)::uuid
                AND workspace_id IN (
                    SELECT wm.workspace_id FROM workspace_members wm
                    WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                    AND wm.role IN ('OWNER', 'ADMIN', 'MEMBER')
                    AND wm.is_deleted = false
                )
            )
            """
        )
    )
