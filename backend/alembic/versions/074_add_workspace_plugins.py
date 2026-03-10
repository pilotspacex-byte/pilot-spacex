"""Add workspace_plugins and workspace_github_credentials tables with RLS.

Revision ID: 074_add_workspace_plugins
Revises: 073_add_workspace_role_skills
Create Date: 2026-03-10

Phase 19 -- Skill Registry and Plugin System (SKRG-01..05):

1. Creates workspace_plugins table with:
   - Standard WorkspaceScopedModel columns (id, workspace_id, created_at,
     updated_at, is_deleted, deleted_at)
   - repo_url, repo_owner, repo_name, skill_name -- plugin identity
   - display_name, description, skill_content, references (JSONB) -- content
   - installed_sha -- git commit SHA at install time
   - is_active BOOLEAN NOT NULL DEFAULT true
   - installed_by UUID NULL FK -> users.id (SET NULL on user delete)
2. Creates workspace_github_credentials table with:
   - pat_encrypted VARCHAR(1024) NOT NULL -- Fernet-encrypted PAT
   - created_by UUID NULL FK -> users.id (SET NULL on user delete)
3. Adds partial unique index on (workspace_id, repo_owner, repo_name, skill_name)
   WHERE is_deleted = false to prevent duplicate installs.
4. Adds composite index on (workspace_id, is_active) for materializer hot-path.
5. Enables RLS with workspace isolation policy and service_role bypass on both tables.

Downgrade reverses all changes: drops policies, indexes, and tables.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "074_add_workspace_plugins"
down_revision: str = "073_add_workspace_role_skills"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    """Create workspace_plugins and workspace_github_credentials tables."""

    # ---- workspace_plugins ----
    op.create_table(
        "workspace_plugins",
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
        # Plugin identity
        sa.Column("repo_url", sa.String(512), nullable=False),
        sa.Column("repo_owner", sa.String(128), nullable=False),
        sa.Column("repo_name", sa.String(128), nullable=False),
        sa.Column("skill_name", sa.String(128), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        # Content
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("skill_content", sa.Text(), nullable=False),
        sa.Column(
            "references",
            postgresql.JSONB(),
            server_default=text("'[]'::jsonb"),
            nullable=False,
        ),
        # Install metadata
        sa.Column("installed_sha", sa.String(40), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=text("true"),
            nullable=False,
        ),
        sa.Column(
            "installed_by",
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
    )

    # Partial unique index: one skill per repo per workspace (non-deleted only)
    op.execute(
        text(
            "CREATE UNIQUE INDEX uq_workspace_plugins_workspace_skill "
            "ON workspace_plugins (workspace_id, repo_owner, repo_name, skill_name) "
            "WHERE is_deleted = false"
        )
    )

    # Hot-path composite index: materializer get_active_by_workspace query
    op.create_index(
        "ix_workspace_plugins_workspace_active",
        "workspace_plugins",
        ["workspace_id", "is_active"],
    )

    # workspace_id column index
    op.create_index(
        "ix_workspace_plugins_workspace_id",
        "workspace_plugins",
        ["workspace_id"],
    )

    # Enable RLS
    op.execute(text("ALTER TABLE workspace_plugins ENABLE ROW LEVEL SECURITY"))
    op.execute(text("ALTER TABLE workspace_plugins FORCE ROW LEVEL SECURITY"))

    # Workspace isolation policy
    op.execute(
        text(
            """
            CREATE POLICY "workspace_plugins_workspace_isolation"
            ON workspace_plugins
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

    # Service-role bypass policy
    op.execute(
        text(
            """
            CREATE POLICY "workspace_plugins_service_role"
            ON workspace_plugins
            FOR ALL
            TO service_role
            USING (true)
            WITH CHECK (true)
            """
        )
    )

    # ---- workspace_github_credentials ----
    op.create_table(
        "workspace_github_credentials",
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
        # Encrypted PAT
        sa.Column("pat_encrypted", sa.String(1024), nullable=False),
        # Creator reference
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
    )

    # workspace_id column index
    op.create_index(
        "ix_workspace_github_credentials_workspace_id",
        "workspace_github_credentials",
        ["workspace_id"],
    )

    # Enable RLS
    op.execute(text("ALTER TABLE workspace_github_credentials ENABLE ROW LEVEL SECURITY"))
    op.execute(text("ALTER TABLE workspace_github_credentials FORCE ROW LEVEL SECURITY"))

    # Workspace isolation policy
    op.execute(
        text(
            """
            CREATE POLICY "workspace_github_credentials_workspace_isolation"
            ON workspace_github_credentials
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

    # Service-role bypass policy
    op.execute(
        text(
            """
            CREATE POLICY "workspace_github_credentials_service_role"
            ON workspace_github_credentials
            FOR ALL
            TO service_role
            USING (true)
            WITH CHECK (true)
            """
        )
    )


def downgrade() -> None:
    """Drop RLS policies, indexes, and tables."""

    # ---- workspace_github_credentials ----
    op.execute(
        text(
            'DROP POLICY IF EXISTS "workspace_github_credentials_service_role" '
            "ON workspace_github_credentials"
        )
    )
    op.execute(
        text(
            'DROP POLICY IF EXISTS "workspace_github_credentials_workspace_isolation" '
            "ON workspace_github_credentials"
        )
    )
    op.drop_index(
        "ix_workspace_github_credentials_workspace_id",
        table_name="workspace_github_credentials",
    )
    op.drop_table("workspace_github_credentials")

    # ---- workspace_plugins ----
    op.execute(text('DROP POLICY IF EXISTS "workspace_plugins_service_role" ON workspace_plugins'))
    op.execute(
        text('DROP POLICY IF EXISTS "workspace_plugins_workspace_isolation" ON workspace_plugins')
    )
    op.drop_index(
        "ix_workspace_plugins_workspace_id",
        table_name="workspace_plugins",
    )
    op.drop_index(
        "ix_workspace_plugins_workspace_active",
        table_name="workspace_plugins",
    )
    op.execute(text("DROP INDEX IF EXISTS uq_workspace_plugins_workspace_skill"))
    op.drop_table("workspace_plugins")
