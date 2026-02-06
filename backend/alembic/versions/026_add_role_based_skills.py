"""Add role-based skills tables and columns.

Revision ID: 026_add_role_based_skills
Revises: 025_issue_links_rls_cross_workspace
Create Date: 2026-02-06

Creates role_templates and user_role_skills tables, adds default_sdlc_role
to users, suggested_sdlc_role to workspace_invitations, seeds 8 role
templates, and extends workspace_onboardings steps with role_setup.

Source: 011-role-based-skills, data-model.md
"""

from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "026_add_role_based_skills"
down_revision: str = "025_issue_links_rls_cross_workspace"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Path to role template markdown files
TEMPLATES_DIR = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "pilot_space"
    / "ai"
    / "templates"
    / "role_templates"
)

# Template metadata matching data-model.md seed data
TEMPLATE_METADATA = [
    {
        "role_type": "business_analyst",
        "display_name": "Business Analyst",
        "description": (
            "Requirements elicitation, stakeholder alignment, "
            "and bridging business needs with technical solutions."
        ),
        "icon": "FileSearch",
        "sort_order": 1,
    },
    {
        "role_type": "product_owner",
        "display_name": "Product Owner",
        "description": (
            "Backlog prioritization, roadmap decisions, and maximizing value delivery for users."
        ),
        "icon": "Target",
        "sort_order": 2,
    },
    {
        "role_type": "developer",
        "display_name": "Developer",
        "description": (
            "Code quality, implementation patterns, testing strategy, "
            "and efficient problem-solving."
        ),
        "icon": "Code",
        "sort_order": 3,
    },
    {
        "role_type": "tester",
        "display_name": "Tester",
        "description": (
            "Test strategy, edge case discovery, acceptance criteria, "
            "and quality assurance across the SDLC."
        ),
        "icon": "TestTube",
        "sort_order": 4,
    },
    {
        "role_type": "architect",
        "display_name": "Architect",
        "description": (
            "System design, technical decisions, scalability, and well-reasoned trade-off analysis."
        ),
        "icon": "Layers",
        "sort_order": 5,
    },
    {
        "role_type": "tech_lead",
        "display_name": "Tech Lead",
        "description": (
            "Technical direction, team productivity, code quality standards, "
            "and unblocking the team."
        ),
        "icon": "GitBranch",
        "sort_order": 6,
    },
    {
        "role_type": "project_manager",
        "display_name": "Project Manager",
        "description": (
            "Delivery tracking, risk management, dependency mapping, and stakeholder coordination."
        ),
        "icon": "GanttChart",
        "sort_order": 7,
    },
    {
        "role_type": "devops",
        "display_name": "DevOps",
        "description": (
            "CI/CD pipelines, infrastructure reliability, deployment automation, "
            "and operational excellence."
        ),
        "icon": "Container",
        "sort_order": 8,
    },
]


def _load_template_content(role_type: str) -> str:
    """Load SKILL.md content from template file.

    Args:
        role_type: The role type key matching the filename.

    Returns:
        Template markdown content.

    Raises:
        FileNotFoundError: If template file is missing.
    """
    file_path = TEMPLATES_DIR / f"{role_type}.md"
    return file_path.read_text(encoding="utf-8")


def upgrade() -> None:
    """Create role-based skills tables, columns, indexes, RLS, and seed data."""
    # 1. Create role_templates table
    op.create_table(
        "role_templates",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("role_type", sa.String(50), nullable=False, unique=True),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("default_skill_content", sa.Text(), nullable=False),
        sa.Column("icon", sa.String(50), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
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

    # 2. Create user_role_skills table
    op.create_table(
        "user_role_skills",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role_type", sa.String(50), nullable=False),
        sa.Column("role_name", sa.String(100), nullable=False),
        sa.Column("skill_content", sa.Text(), nullable=False),
        sa.Column("experience_description", sa.Text(), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("template_version", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
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
            "char_length(skill_content) <= 15000", name="ck_user_role_skills_skill_content_length"
        ),
        sa.CheckConstraint(
            "char_length(role_name) <= 100", name="ck_user_role_skills_role_name_length"
        ),
    )
    op.create_index(
        "ix_user_role_skills_user_workspace", "user_role_skills", ["user_id", "workspace_id"]
    )
    op.create_index("ix_user_role_skills_workspace", "user_role_skills", ["workspace_id"])

    # 3. Add default_sdlc_role to users
    op.add_column("users", sa.Column("default_sdlc_role", sa.String(50), nullable=True))

    # 4. Add suggested_sdlc_role to workspace_invitations
    op.add_column(
        "workspace_invitations", sa.Column("suggested_sdlc_role", sa.String(50), nullable=True)
    )

    # 5. Enable RLS on both new tables
    op.execute("ALTER TABLE role_templates ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE user_role_skills ENABLE ROW LEVEL SECURITY")

    # 6. Create RLS policies per data-model.md

    # role_templates: all authenticated users can read
    op.execute("""
        CREATE POLICY "role_templates_select" ON role_templates
        FOR SELECT USING (
            current_setting('app.current_user_id', true)::uuid IS NOT NULL
        );
    """)

    # user_role_skills: users can read own + admins can read all in workspace
    op.execute("""
        CREATE POLICY "user_role_skills_select" ON user_role_skills
        FOR SELECT USING (
            user_id = current_setting('app.current_user_id', true)::uuid
            OR workspace_id IN (
                SELECT wm.workspace_id FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                AND wm.role IN ('OWNER', 'ADMIN')
                AND wm.is_deleted = false
            )
        );
    """)

    # user_role_skills: users can modify own (not guests)
    op.execute("""
        CREATE POLICY "user_role_skills_modify" ON user_role_skills
        FOR ALL USING (
            user_id = current_setting('app.current_user_id', true)::uuid
            AND workspace_id IN (
                SELECT wm.workspace_id FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                AND wm.role IN ('OWNER', 'ADMIN', 'MEMBER')
                AND wm.is_deleted = false
            )
        );
    """)

    # 7. Seed 8 role templates from template files
    role_templates_table = sa.table(
        "role_templates",
        sa.column("role_type", sa.String),
        sa.column("display_name", sa.String),
        sa.column("description", sa.Text),
        sa.column("default_skill_content", sa.Text),
        sa.column("icon", sa.String),
        sa.column("sort_order", sa.Integer),
        sa.column("version", sa.Integer),
    )

    seed_rows = []
    for meta in TEMPLATE_METADATA:
        content = _load_template_content(meta["role_type"])
        seed_rows.append(
            {
                "role_type": meta["role_type"],
                "display_name": meta["display_name"],
                "description": meta["description"],
                "default_skill_content": content,
                "icon": meta["icon"],
                "sort_order": meta["sort_order"],
                "version": 1,
            }
        )

    op.bulk_insert(role_templates_table, seed_rows)

    # 8. Update existing workspace_onboardings.steps to include role_setup
    op.execute("""
        UPDATE workspace_onboardings
        SET steps = steps || '{"role_setup": false}'::jsonb
        WHERE NOT (steps ? 'role_setup');
    """)


def downgrade() -> None:
    """Reverse all role-based skills changes."""
    # 1. Remove role_setup from workspace_onboardings.steps
    op.execute("""
        UPDATE workspace_onboardings
        SET steps = steps - 'role_setup';
    """)

    # 2. Drop RLS policies
    op.execute('DROP POLICY IF EXISTS "user_role_skills_modify" ON user_role_skills')
    op.execute('DROP POLICY IF EXISTS "user_role_skills_select" ON user_role_skills')
    op.execute('DROP POLICY IF EXISTS "role_templates_select" ON role_templates')

    # 3. Drop columns from existing tables
    op.drop_column("workspace_invitations", "suggested_sdlc_role")
    op.drop_column("users", "default_sdlc_role")

    # 4. Drop indexes and tables
    op.drop_index("ix_user_role_skills_workspace", "user_role_skills")
    op.drop_index("ix_user_role_skills_user_workspace", "user_role_skills")
    op.drop_table("user_role_skills")

    op.drop_index("ix_role_templates_sort_order", "role_templates")
    op.drop_index("ix_role_templates_role_type", "role_templates")
    op.drop_table("role_templates")
