"""Create Integration entities for GitHub/Slack integration.

Revision ID: 009_integration_entities
Revises: 006_issue_entities
Create Date: 2026-01-24

Creates tables for:
- integrations: OAuth tokens and settings for GitHub/Slack
- integration_links: Links between issues and commits/PRs/branches

T174: Create migration for Integration entities.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "009_integration_entities"
down_revision: str | None = "006_issue_entities"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Create Integration entities tables."""
    # Create integration_provider enum
    integration_provider = postgresql.ENUM(
        "github",
        "slack",
        name="integration_provider",
        create_type=True,
    )
    integration_provider.create(op.get_bind(), checkfirst=True)

    # Create integration_link_type enum
    integration_link_type = postgresql.ENUM(
        "commit",
        "pull_request",
        "branch",
        "mention",
        name="integration_link_type",
        create_type=True,
    )
    integration_link_type.create(op.get_bind(), checkfirst=True)

    # Create integrations table
    op.create_table(
        "integrations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
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
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "provider",
            postgresql.ENUM(
                "github",
                "slack",
                name="integration_provider",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.String(50), nullable=True),
        sa.Column("external_account_id", sa.String(255), nullable=True),
        sa.Column("external_account_name", sa.String(255), nullable=True),
        sa.Column("settings", postgresql.JSONB(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column("installed_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["installed_by_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "provider",
            name="uq_integrations_workspace_provider",
        ),
    )
    op.create_index("ix_integrations_workspace_id", "integrations", ["workspace_id"])
    op.create_index("ix_integrations_provider", "integrations", ["provider"])
    op.create_index("ix_integrations_is_active", "integrations", ["is_active"])
    op.create_index("ix_integrations_is_deleted", "integrations", ["is_deleted"])
    op.create_index(
        "ix_integrations_external_account_id",
        "integrations",
        ["external_account_id"],
    )

    # Create integration_links table
    op.create_table(
        "integration_links",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
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
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("integration_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("issue_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "link_type",
            postgresql.ENUM(
                "commit",
                "pull_request",
                "branch",
                "mention",
                name="integration_link_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("external_url", sa.String(2048), nullable=True),
        sa.Column("title", sa.String(512), nullable=True),
        sa.Column("author_name", sa.String(255), nullable=True),
        sa.Column("author_avatar_url", sa.String(2048), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["integration_id"],
            ["integrations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["issue_id"],
            ["issues.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "integration_id",
            "issue_id",
            "link_type",
            "external_id",
            name="uq_integration_links_unique_link",
        ),
    )
    op.create_index(
        "ix_integration_links_workspace_id",
        "integration_links",
        ["workspace_id"],
    )
    op.create_index(
        "ix_integration_links_integration_id",
        "integration_links",
        ["integration_id"],
    )
    op.create_index(
        "ix_integration_links_issue_id",
        "integration_links",
        ["issue_id"],
    )
    op.create_index(
        "ix_integration_links_link_type",
        "integration_links",
        ["link_type"],
    )
    op.create_index(
        "ix_integration_links_external_id",
        "integration_links",
        ["external_id"],
    )
    op.create_index(
        "ix_integration_links_is_deleted",
        "integration_links",
        ["is_deleted"],
    )
    op.create_index(
        "ix_integration_links_integration_type",
        "integration_links",
        ["integration_id", "link_type"],
    )

    # Create RLS policies
    _create_rls_policies()


def _create_rls_policies() -> None:
    """Create RLS policies for Integration entities."""
    # Integrations RLS
    op.execute("""
        ALTER TABLE integrations ENABLE ROW LEVEL SECURITY;
        ALTER TABLE integrations FORCE ROW LEVEL SECURITY;

        CREATE POLICY "integrations_workspace_member"
        ON integrations
        FOR ALL
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
        );
    """)

    # Integration Links RLS
    op.execute("""
        ALTER TABLE integration_links ENABLE ROW LEVEL SECURITY;
        ALTER TABLE integration_links FORCE ROW LEVEL SECURITY;

        CREATE POLICY "integration_links_workspace_member"
        ON integration_links
        FOR ALL
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
        );
    """)


def downgrade() -> None:
    """Drop Integration entities tables and RLS policies."""
    # Drop RLS policies
    tables = ["integration_links", "integrations"]
    for table in tables:
        op.execute(f"""
            DROP POLICY IF EXISTS "{table}_workspace_member" ON {table};
            ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;
        """)

    # Drop tables in reverse order
    op.drop_table("integration_links")
    op.drop_table("integrations")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS integration_link_type")
    op.execute("DROP TYPE IF EXISTS integration_provider")
