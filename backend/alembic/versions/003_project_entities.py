"""Create Project, State, Label, Module tables.

Revision ID: 003_project_entities
Revises: 002_core_entities
Create Date: 2026-01-23

Creates project-related tables for organizing issues and workflow.
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003_project_entities"
down_revision: str | None = "002_core_entities"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Create project entity tables."""
    # Create projects table
    op.create_table(
        "projects",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("identifier", sa.String(10), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("icon", sa.String(50), nullable=True),
        sa.Column("settings", JSONB, nullable=True),
        sa.Column("lead_id", UUID(as_uuid=True), nullable=True),
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
            onupdate=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("is_deleted", sa.Boolean, server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
            name="fk_projects_workspace",
        ),
        sa.ForeignKeyConstraint(
            ["lead_id"], ["users.id"], ondelete="SET NULL", name="fk_projects_lead"
        ),
        sa.UniqueConstraint("workspace_id", "identifier", name="uq_projects_workspace_identifier"),
    )
    op.create_index("ix_projects_workspace_id", "projects", ["workspace_id"])
    op.create_index("ix_projects_identifier", "projects", ["identifier"])
    op.create_index("ix_projects_lead_id", "projects", ["lead_id"])
    op.create_index("ix_projects_is_deleted", "projects", ["is_deleted"])

    # Create state_group enum type using raw SQL for async compatibility
    op.execute("CREATE TYPE state_group AS ENUM ('unstarted', 'started', 'completed', 'cancelled')")

    # Create states table
    op.create_table(
        "states",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("color", sa.String(20), nullable=False, server_default="#6b7280"),
        sa.Column(
            "group",
            ENUM(
                "unstarted",
                "started",
                "completed",
                "cancelled",
                name="state_group",
                create_type=False,
            ),
            nullable=False,
            server_default="unstarted",
        ),
        sa.Column("sequence", sa.Integer, nullable=False, server_default="0"),
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
            onupdate=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("is_deleted", sa.Boolean, server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
            name="fk_states_workspace",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
            name="fk_states_project",
        ),
        sa.UniqueConstraint(
            "workspace_id", "project_id", "name", name="uq_states_workspace_project_name"
        ),
    )
    op.create_index("ix_states_workspace_id", "states", ["workspace_id"])
    op.create_index("ix_states_project_id", "states", ["project_id"])
    op.create_index("ix_states_group", "states", ["group"])
    op.create_index("ix_states_sequence", "states", ["sequence"])
    op.create_index("ix_states_is_deleted", "states", ["is_deleted"])

    # Create labels table
    op.create_table(
        "labels",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("color", sa.String(20), nullable=False, server_default="#6b7280"),
        sa.Column("description", sa.Text, nullable=True),
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
            onupdate=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("is_deleted", sa.Boolean, server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
            name="fk_labels_workspace",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
            name="fk_labels_project",
        ),
        sa.UniqueConstraint(
            "workspace_id", "project_id", "name", name="uq_labels_workspace_project_name"
        ),
    )
    op.create_index("ix_labels_workspace_id", "labels", ["workspace_id"])
    op.create_index("ix_labels_project_id", "labels", ["project_id"])
    op.create_index("ix_labels_is_deleted", "labels", ["is_deleted"])

    # Create module_status enum type using raw SQL for async compatibility
    op.execute(
        "CREATE TYPE module_status AS ENUM ('planned', 'in_progress', 'paused', 'completed', 'cancelled')"
    )

    # Create modules table
    op.create_table(
        "modules",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "status",
            ENUM(
                "planned",
                "in_progress",
                "paused",
                "completed",
                "cancelled",
                name="module_status",
                create_type=False,
            ),
            nullable=False,
            server_default="planned",
        ),
        sa.Column("target_date", sa.Date, nullable=True),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
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
            onupdate=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("is_deleted", sa.Boolean, server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
            name="fk_modules_workspace",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
            name="fk_modules_project",
        ),
    )
    op.create_index("ix_modules_workspace_id", "modules", ["workspace_id"])
    op.create_index("ix_modules_project_id", "modules", ["project_id"])
    op.create_index("ix_modules_status", "modules", ["status"])
    op.create_index("ix_modules_is_deleted", "modules", ["is_deleted"])


def downgrade() -> None:
    """Drop project entity tables."""
    op.drop_table("modules")
    op.execute("DROP TYPE IF EXISTS module_status")
    op.drop_table("labels")
    op.drop_table("states")
    op.execute("DROP TYPE IF EXISTS state_group")
    op.drop_table("projects")
