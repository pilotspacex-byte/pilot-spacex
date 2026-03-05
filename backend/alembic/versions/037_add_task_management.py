"""Add task management tables and enhance issues.

Creates the tasks table for issue-scoped task management with AI support.
Adds acceptance_criteria (JSONB) and technical_requirements (Text) to issues.
Includes RLS policies and indexes for workspace isolation.

Revision ID: 037_add_task_management
Revises: 036_fix_ai_sessions_rls_enum
Create Date: 2026-02-14
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision = "037_add_task_management"
down_revision = "036_fix_ai_sessions_rls_enum"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add task management infrastructure."""
    # 1. Enhance issues table
    op.add_column("issues", sa.Column("acceptance_criteria", sa.JSON(), nullable=True))
    op.add_column(
        "issues", sa.Column("technical_requirements", sa.Text(), nullable=True)
    )

    # 2. Create tasks table (sa.Enum will auto-create task_status_enum type)
    op.create_table(
        "tasks",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "workspace_id",
            UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "issue_id",
            UUID(as_uuid=True),
            sa.ForeignKey("issues.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("acceptance_criteria", sa.JSON(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("todo", "in_progress", "done", name="task_status_enum"),
            nullable=False,
            server_default="todo",
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated_hours", sa.Numeric(5, 1), nullable=True),
        sa.Column("code_references", sa.JSON(), nullable=True),
        sa.Column("ai_prompt", sa.Text(), nullable=True),
        sa.Column("ai_generated", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("dependency_ids", sa.JSON(), nullable=True),
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
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 4. Indexes
    op.create_index("ix_tasks_issue_id", "tasks", ["issue_id"])
    op.create_index("ix_tasks_workspace_id", "tasks", ["workspace_id"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_issue_sort", "tasks", ["issue_id", "sort_order"])
    op.create_index("ix_tasks_is_deleted", "tasks", ["is_deleted"])

    # 5. RLS
    op.execute("ALTER TABLE tasks ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE tasks FORCE ROW LEVEL SECURITY")

    op.execute(
        """
        CREATE POLICY "tasks_workspace_isolation"
        ON tasks FOR ALL
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
        )
    """
    )


def downgrade() -> None:
    """Remove task management infrastructure."""
    op.execute('DROP POLICY IF EXISTS "tasks_workspace_isolation" ON tasks')
    op.execute("ALTER TABLE tasks DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_tasks_is_deleted", table_name="tasks")
    op.drop_index("ix_tasks_issue_sort", table_name="tasks")
    op.drop_index("ix_tasks_status", table_name="tasks")
    op.drop_index("ix_tasks_workspace_id", table_name="tasks")
    op.drop_index("ix_tasks_issue_id", table_name="tasks")
    op.drop_table("tasks")
    op.execute("DROP TYPE IF EXISTS task_status_enum")
    op.drop_column("issues", "technical_requirements")
    op.drop_column("issues", "acceptance_criteria")
