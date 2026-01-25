"""Create User, Workspace, WorkspaceMember tables.

Revision ID: 002_core_entities
Revises: 001_enable_pgvector
Create Date: 2026-01-23

Creates the foundational user and workspace tables for multi-tenant isolation.
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_core_entities"
down_revision: str | None = "001_enable_pgvector"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Create core entity tables."""
    # Create users table
    op.create_table(
        "users",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("avatar_url", sa.Text, nullable=True),
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
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_is_deleted", "users", ["is_deleted"])

    # Create workspaces table
    op.create_table(
        "workspaces",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("settings", JSONB, nullable=True),
        sa.Column("owner_id", UUID(as_uuid=True), nullable=True),
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
            ["owner_id"], ["users.id"], ondelete="SET NULL", name="fk_workspaces_owner"
        ),
    )
    op.create_index("ix_workspaces_slug", "workspaces", ["slug"])
    op.create_index("ix_workspaces_owner_id", "workspaces", ["owner_id"])
    op.create_index("ix_workspaces_is_deleted", "workspaces", ["is_deleted"])

    # Create workspace_members table
    op.create_table(
        "workspace_members",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "role",
            sa.Enum("OWNER", "ADMIN", "MEMBER", "GUEST", name="workspace_role"),
            nullable=False,
            server_default="MEMBER",
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
            onupdate=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("is_deleted", sa.Boolean, server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
            name="fk_workspace_members_workspace",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
            name="fk_workspace_members_user",
        ),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_workspace_members_workspace_user"),
    )
    op.create_index("ix_workspace_members_workspace_id", "workspace_members", ["workspace_id"])
    op.create_index("ix_workspace_members_user_id", "workspace_members", ["user_id"])
    op.create_index("ix_workspace_members_role", "workspace_members", ["role"])
    op.create_index("ix_workspace_members_is_deleted", "workspace_members", ["is_deleted"])


def downgrade() -> None:
    """Drop core entity tables."""
    op.drop_table("workspace_members")
    op.execute("DROP TYPE IF EXISTS workspace_role")
    op.drop_table("workspaces")
    op.drop_table("users")
