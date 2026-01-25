"""Create ai_configurations table for LLM provider settings.

Revision ID: 012_ai_configurations
Revises: 011_performance_indexes
Create Date: 2026-01-24

Creates table for:
- ai_configurations: Workspace-level LLM provider settings (BYOK)
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "012_ai_configurations"
down_revision: str | None = "011_performance_indexes"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Create ai_configurations table with RLS policies."""
    # Create llm_provider enum type
    op.execute("CREATE TYPE llm_provider AS ENUM ('anthropic', 'openai', 'google')")

    # Create ai_configurations table
    op.create_table(
        "ai_configurations",
        # Base model columns
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
        # Workspace scoped
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Provider configuration
        sa.Column(
            "provider",
            postgresql.ENUM(
                "anthropic", "openai", "google", name="llm_provider", create_type=False
            ),
            nullable=False,
        ),
        sa.Column(
            "api_key_encrypted",
            sa.String(512),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        # Provider-specific settings
        sa.Column(
            "settings",
            postgresql.JSONB(),
            nullable=True,
        ),
        # Usage limits
        sa.Column(
            "usage_limits",
            postgresql.JSONB(),
            nullable=True,
        ),
        # Foreign keys
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
        ),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "provider", name="uq_ai_config_workspace_provider"),
    )

    # Create indexes
    op.create_index("ix_ai_configurations_workspace_id", "ai_configurations", ["workspace_id"])
    op.create_index(
        "ix_ai_configurations_workspace_provider", "ai_configurations", ["workspace_id", "provider"]
    )
    op.create_index("ix_ai_configurations_is_deleted", "ai_configurations", ["is_deleted"])

    # Create RLS policies
    _create_rls_policies()


def _create_rls_policies() -> None:
    """Create RLS policies for ai_configurations entity."""
    op.execute("ALTER TABLE ai_configurations ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE ai_configurations FORCE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY "ai_configurations_workspace_member"
        ON ai_configurations
        FOR SELECT
        USING (
            workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                AND wm.is_deleted = false
            )
        )
    """)

    # Only admins/owners can modify AI configurations
    op.execute("""
        CREATE POLICY "ai_configurations_admin_modify"
        ON ai_configurations
        FOR ALL
        USING (
            workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                AND wm.role IN ('OWNER', 'ADMIN')
                AND wm.is_deleted = false
            )
        )
        WITH CHECK (
            workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                AND wm.role IN ('OWNER', 'ADMIN')
                AND wm.is_deleted = false
            )
        )
    """)


def downgrade() -> None:
    """Drop ai_configurations table and RLS policies."""
    # Drop RLS policies
    op.execute('DROP POLICY IF EXISTS "ai_configurations_admin_modify" ON ai_configurations')
    op.execute('DROP POLICY IF EXISTS "ai_configurations_workspace_member" ON ai_configurations')
    op.execute("ALTER TABLE ai_configurations DISABLE ROW LEVEL SECURITY")

    # Drop table
    op.drop_table("ai_configurations")

    # Drop enum type
    op.execute("DROP TYPE IF EXISTS llm_provider")
