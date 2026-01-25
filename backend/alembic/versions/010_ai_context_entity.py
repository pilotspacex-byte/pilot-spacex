"""Create AIContext entity for AI-aggregated issue context.

Revision ID: 010_ai_context_entity
Revises: 009_integration_entities
Create Date: 2026-01-24

Creates table for:
- ai_contexts: AI-aggregated context for issues

T202: Create migration for AIContext entity.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "010_ai_context_entity"
down_revision: str | None = "009_integration_entities"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Create AIContext table with RLS policies."""
    # Create ai_contexts table
    op.create_table(
        "ai_contexts",
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
        # One-to-one with issue
        sa.Column("issue_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Structured content
        sa.Column(
            "content",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        # Claude Code prompt
        sa.Column("claude_code_prompt", sa.Text(), nullable=True),
        # Related items (denormalized for performance)
        sa.Column(
            "related_issues",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "related_notes",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "related_pages",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        # Code references
        sa.Column(
            "code_references",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        # Tasks checklist
        sa.Column(
            "tasks_checklist",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        # Conversation history
        sa.Column(
            "conversation_history",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        # Timestamps
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_refined_at", sa.DateTime(timezone=True), nullable=True),
        # Version for optimistic locking
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        # Foreign keys
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["issue_id"],
            ["issues.id"],
            ondelete="CASCADE",
        ),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("issue_id", name="uq_ai_contexts_issue_id"),
    )

    # Create indexes
    op.create_index("ix_ai_contexts_workspace_id", "ai_contexts", ["workspace_id"])
    op.create_index("ix_ai_contexts_issue_id", "ai_contexts", ["issue_id"])
    op.create_index("ix_ai_contexts_generated_at", "ai_contexts", ["generated_at"])
    op.create_index("ix_ai_contexts_is_deleted", "ai_contexts", ["is_deleted"])

    # Create GIN indexes for JSONB columns for efficient querying
    op.execute("""
        CREATE INDEX ix_ai_contexts_content_gin ON ai_contexts USING GIN (content);
        CREATE INDEX ix_ai_contexts_related_issues_gin ON ai_contexts USING GIN (related_issues);
        CREATE INDEX ix_ai_contexts_tasks_checklist_gin ON ai_contexts USING GIN (tasks_checklist);
    """)

    # Create RLS policies
    _create_rls_policies()


def _create_rls_policies() -> None:
    """Create RLS policies for AIContext entity."""
    op.execute("""
        ALTER TABLE ai_contexts ENABLE ROW LEVEL SECURITY;
        ALTER TABLE ai_contexts FORCE ROW LEVEL SECURITY;

        CREATE POLICY "ai_contexts_workspace_member"
        ON ai_contexts
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
    """Drop AIContext table and RLS policies."""
    # Drop RLS policies
    op.execute("""
        DROP POLICY IF EXISTS "ai_contexts_workspace_member" ON ai_contexts;
        ALTER TABLE ai_contexts DISABLE ROW LEVEL SECURITY;
    """)

    # Drop GIN indexes
    op.execute("""
        DROP INDEX IF EXISTS ix_ai_contexts_content_gin;
        DROP INDEX IF EXISTS ix_ai_contexts_related_issues_gin;
        DROP INDEX IF EXISTS ix_ai_contexts_tasks_checklist_gin;
    """)

    # Drop table (indexes are dropped automatically)
    op.drop_table("ai_contexts")
