"""Add skill_templates and user_skills tables with data migration.

Revision ID: 077_add_skill_templates
Revises: 076_add_previous_encrypted_key
Create Date: 2026-03-11

Phase 20 — Skill Template Catalog (P20-01..P20-03):

1. Creates skill_templates table with:
   - Standard WorkspaceScopedModel columns
   - name, description, skill_content, icon, sort_order
   - source VARCHAR(20) NOT NULL ('built_in' | 'workspace' | 'custom')
   - role_type VARCHAR(50) NULL (optional lineage)
   - is_active BOOLEAN NOT NULL DEFAULT true
   - created_by UUID NULL FK -> users.id (SET NULL)
   - Partial unique index on (workspace_id, name) WHERE is_deleted = false
   - Composite indexes on (workspace_id, source) and (workspace_id, is_active)
   - RLS policies: workspace isolation + service_role bypass

2. Creates user_skills table with:
   - Standard WorkspaceScopedModel columns
   - user_id UUID NOT NULL FK -> users.id (CASCADE)
   - template_id UUID NULL FK -> skill_templates.id (SET NULL)
   - skill_content, experience_description, is_active
   - Partial unique index on (user_id, workspace_id, template_id) WHERE is_deleted = false
   - Composite indexes on (user_id, workspace_id) and (workspace_id)
   - RLS policies: workspace isolation + service_role bypass

3. Data migration (raw SQL):
   - RoleTemplate rows -> skill_templates (source='built_in', per workspace)
   - WorkspaceRoleSkill rows -> skill_templates (source='workspace')
   - UserRoleSkill rows -> user_skills (template_id linked via LEFT JOIN)

4. Old tables are NOT dropped (additive migration).

Downgrade: drops user_skills then skill_templates (policies, indexes, tables).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "077_add_skill_templates"
down_revision: str = "076_add_previous_encrypted_key"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    """Create skill_templates + user_skills tables, indexes, RLS, and migrate data."""

    # -----------------------------------------------------------------------
    # 1. Create skill_templates table
    # -----------------------------------------------------------------------
    op.create_table(
        "skill_templates",
        # Primary key
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
            nullable=False,
        ),
        # Workspace scoping
        sa.Column(
            "workspace_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Business fields
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("skill_content", sa.Text(), nullable=False),
        sa.Column(
            "icon",
            sa.String(50),
            server_default=text("'Wand2'"),
            nullable=False,
        ),
        sa.Column(
            "sort_order",
            sa.Integer(),
            server_default=text("0"),
            nullable=False,
        ),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("role_type", sa.String(50), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            sa.dialects.postgresql.UUID(as_uuid=True),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        # Check constraints
        sa.CheckConstraint(
            "length(skill_content) <= 15000",
            name="ck_skill_templates_content_length",
        ),
        sa.CheckConstraint(
            "length(name) <= 100",
            name="ck_skill_templates_name_length",
        ),
    )

    # Partial unique index: one template per name per workspace (excluding deleted)
    op.execute(
        text(
            "CREATE UNIQUE INDEX uq_skill_templates_workspace_name "
            "ON skill_templates (workspace_id, name) WHERE is_deleted = false"
        )
    )

    # Composite indexes
    op.create_index(
        "ix_skill_templates_workspace_source",
        "skill_templates",
        ["workspace_id", "source"],
    )
    op.create_index(
        "ix_skill_templates_workspace_active",
        "skill_templates",
        ["workspace_id", "is_active"],
    )
    op.create_index(
        "ix_skill_templates_workspace_id",
        "skill_templates",
        ["workspace_id"],
    )

    # RLS policies for skill_templates
    op.execute(text("ALTER TABLE skill_templates ENABLE ROW LEVEL SECURITY"))
    op.execute(text("ALTER TABLE skill_templates FORCE ROW LEVEL SECURITY"))
    op.execute(
        text(
            """
            CREATE POLICY "skill_templates_workspace_isolation"
            ON skill_templates
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
            CREATE POLICY "skill_templates_service_role"
            ON skill_templates
            FOR ALL
            TO service_role
            USING (true)
            WITH CHECK (true)
            """
        )
    )

    # -----------------------------------------------------------------------
    # 2. Create user_skills table
    # -----------------------------------------------------------------------
    op.create_table(
        "user_skills",
        # Primary key
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
            nullable=False,
        ),
        # User reference
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Workspace scoping
        sa.Column(
            "workspace_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Template reference (nullable: custom skills or deleted templates)
        sa.Column(
            "template_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("skill_templates.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Business fields
        sa.Column("skill_content", sa.Text(), nullable=False),
        sa.Column("experience_description", sa.Text(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=text("true"),
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
            sa.Boolean(),
            server_default=text("false"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        # Check constraint
        sa.CheckConstraint(
            "length(skill_content) <= 15000",
            name="ck_user_skills_content_length",
        ),
    )

    # Partial unique index: one skill per template per user per workspace (excluding deleted)
    op.execute(
        text(
            "CREATE UNIQUE INDEX uq_user_skills_user_workspace_template "
            "ON user_skills (user_id, workspace_id, template_id) WHERE is_deleted = false"
        )
    )

    # Composite indexes
    op.create_index(
        "ix_user_skills_user_workspace",
        "user_skills",
        ["user_id", "workspace_id"],
    )
    op.create_index(
        "ix_user_skills_workspace",
        "user_skills",
        ["workspace_id"],
    )

    # RLS policies for user_skills
    op.execute(text("ALTER TABLE user_skills ENABLE ROW LEVEL SECURITY"))
    op.execute(text("ALTER TABLE user_skills FORCE ROW LEVEL SECURITY"))
    op.execute(
        text(
            """
            CREATE POLICY "user_skills_workspace_isolation"
            ON user_skills
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
            CREATE POLICY "user_skills_service_role"
            ON user_skills
            FOR ALL
            TO service_role
            USING (true)
            WITH CHECK (true)
            """
        )
    )

    # -----------------------------------------------------------------------
    # 3. Data migration: copy existing role-based data to new tables
    # -----------------------------------------------------------------------

    # 3a. Copy RoleTemplate rows to skill_templates per workspace (source='built_in')
    # For each distinct workspace, insert a copy of each role_template.
    op.execute(
        text(
            """
            INSERT INTO skill_templates (
                id, workspace_id, name, description, skill_content,
                icon, sort_order, source, role_type, is_active, created_by,
                created_at, updated_at, is_deleted
            )
            SELECT
                gen_random_uuid(),
                wm.workspace_id,
                rt.display_name,
                rt.description,
                rt.default_skill_content,
                rt.icon,
                rt.sort_order,
                'built_in',
                rt.role_type,
                true,
                NULL,
                rt.created_at,
                rt.updated_at,
                false
            FROM role_templates rt
            CROSS JOIN (SELECT DISTINCT workspace_id FROM workspace_members) wm
            WHERE rt.is_deleted = false
            """
        )
    )

    # 3b. Copy WorkspaceRoleSkill rows to skill_templates (source='workspace')
    op.execute(
        text(
            """
            INSERT INTO skill_templates (
                id, workspace_id, name, description, skill_content,
                icon, sort_order, source, role_type, is_active, created_by,
                created_at, updated_at, is_deleted, deleted_at
            )
            SELECT
                gen_random_uuid(),
                wrs.workspace_id,
                wrs.role_name,
                'Workspace skill for ' || wrs.role_type,
                wrs.skill_content,
                'Wand2',
                100,
                'workspace',
                wrs.role_type,
                wrs.is_active,
                wrs.created_by,
                wrs.created_at,
                wrs.updated_at,
                wrs.is_deleted,
                wrs.deleted_at
            FROM workspace_role_skills wrs
            """
        )
    )

    # 3c. Copy UserRoleSkill rows to user_skills with template_id linked
    # via LEFT JOIN on (workspace_id, role_type, source='built_in')
    op.execute(
        text(
            """
            INSERT INTO user_skills (
                id, user_id, workspace_id, template_id, skill_content,
                experience_description, is_active,
                created_at, updated_at, is_deleted, deleted_at
            )
            SELECT
                gen_random_uuid(),
                urs.user_id,
                urs.workspace_id,
                st.id,
                urs.skill_content,
                urs.experience_description,
                true,
                urs.created_at,
                urs.updated_at,
                urs.is_deleted,
                urs.deleted_at
            FROM user_role_skills urs
            LEFT JOIN skill_templates st
                ON st.workspace_id = urs.workspace_id
                AND st.role_type = urs.role_type
                AND st.source = 'built_in'
                AND st.is_deleted = false
            """
        )
    )


def downgrade() -> None:
    """Drop user_skills and skill_templates tables with RLS policies."""

    # Drop user_skills RLS policies
    op.execute(text('DROP POLICY IF EXISTS "user_skills_service_role" ON user_skills'))
    op.execute(
        text('DROP POLICY IF EXISTS "user_skills_workspace_isolation" ON user_skills')
    )

    # Drop user_skills indexes
    op.execute(text("DROP INDEX IF EXISTS uq_user_skills_user_workspace_template"))
    op.drop_index("ix_user_skills_user_workspace", table_name="user_skills")
    op.drop_index("ix_user_skills_workspace", table_name="user_skills")

    # Drop user_skills table
    op.drop_table("user_skills")

    # Drop skill_templates RLS policies
    op.execute(
        text('DROP POLICY IF EXISTS "skill_templates_service_role" ON skill_templates')
    )
    op.execute(
        text(
            'DROP POLICY IF EXISTS "skill_templates_workspace_isolation" ON skill_templates'
        )
    )

    # Drop skill_templates indexes
    op.execute(text("DROP INDEX IF EXISTS uq_skill_templates_workspace_name"))
    op.drop_index("ix_skill_templates_workspace_id", table_name="skill_templates")
    op.drop_index("ix_skill_templates_workspace_active", table_name="skill_templates")
    op.drop_index("ix_skill_templates_workspace_source", table_name="skill_templates")

    # Drop skill_templates table
    op.drop_table("skill_templates")
