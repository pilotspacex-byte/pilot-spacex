"""Enhanced MCP tool models: IssueLink, discussion/comment extensions.

Revision ID: 024_enhanced_mcp_models
Revises: 022_multi_context_sessions, 023_fix_invitation_rls_enum_case
Create Date: 2026-02-06

Merges two branch heads and adds:
- issue_link_type enum + issue_links table (AD-005)
- threaded_discussions: note_id nullable, target_type/target_id columns
- discussion_comments: reactions (JSONB), edited_at columns
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "024_enhanced_mcp_models"
down_revision: tuple[str, ...] = (
    "022_multi_context_sessions",
    "023_fix_invitation_rls_enum_case",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add IssueLink table and extend discussion/comment models."""
    # 1. Create issue_link_type enum
    issue_link_type = postgresql.ENUM(
        "blocks",
        "blocked_by",
        "duplicates",
        "related",
        name="issue_link_type",
        create_type=False,
    )
    issue_link_type.create(op.get_bind(), checkfirst=True)

    # 2. Create issue_links table
    op.create_table(
        "issue_links",
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
        sa.Column("source_issue_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_issue_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "link_type",
            issue_link_type,
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_issue_id"], ["issues.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_issue_id"], ["issues.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_issue_id",
            "target_issue_id",
            "link_type",
            name="uq_issue_links_source_target_type",
        ),
        sa.CheckConstraint(
            "source_issue_id != target_issue_id",
            name="ck_issue_links_no_self",
        ),
    )
    op.create_index("ix_issue_links_source", "issue_links", ["source_issue_id"])
    op.create_index("ix_issue_links_target", "issue_links", ["target_issue_id"])
    op.create_index("ix_issue_links_workspace_type", "issue_links", ["workspace_id", "link_type"])
    op.create_index("ix_issue_links_workspace_id", "issue_links", ["workspace_id"])

    # 3. Enable RLS on issue_links
    op.execute("""
        ALTER TABLE issue_links ENABLE ROW LEVEL SECURITY;
        ALTER TABLE issue_links FORCE ROW LEVEL SECURITY;

        CREATE POLICY "issue_links_workspace_member"
        ON issue_links
        FOR ALL
        USING (
            workspace_id IN (
                SELECT wm.workspace_id FROM workspace_members wm
                WHERE wm.user_id = auth.uid()
            )
        );
    """)

    # 4. Alter threaded_discussions: make note_id nullable
    op.alter_column(
        "threaded_discussions",
        "note_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )

    # 5. Add target_type and target_id columns to threaded_discussions
    op.add_column(
        "threaded_discussions",
        sa.Column(
            "target_type",
            sa.String(20),
            nullable=False,
            server_default="note",
        ),
    )
    op.add_column(
        "threaded_discussions",
        sa.Column(
            "target_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    # 6. Add CHECK constraint for target_type/target_id integrity
    op.create_check_constraint(
        "ck_threaded_discussions_target_integrity",
        "threaded_discussions",
        "(target_type = 'note' AND note_id IS NOT NULL) OR "
        "(target_type != 'note' AND target_id IS NOT NULL)",
    )

    # 7. Add reactions and edited_at columns to discussion_comments
    op.add_column(
        "discussion_comments",
        sa.Column("reactions", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "discussion_comments",
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Remove IssueLink table and revert discussion/comment extensions."""
    # Remove discussion_comments extensions
    op.drop_column("discussion_comments", "edited_at")
    op.drop_column("discussion_comments", "reactions")

    # Remove threaded_discussions extensions
    op.drop_constraint("ck_threaded_discussions_target_integrity", "threaded_discussions")
    op.drop_column("threaded_discussions", "target_id")
    op.drop_column("threaded_discussions", "target_type")

    # Remove non-note discussions before reverting NOT NULL constraint
    op.execute("DELETE FROM threaded_discussions WHERE note_id IS NULL")

    op.alter_column(
        "threaded_discussions",
        "note_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )

    # Drop RLS policy and issue_links table
    op.execute('DROP POLICY IF EXISTS "issue_links_workspace_member" ON issue_links')
    op.drop_index("ix_issue_links_workspace_id", table_name="issue_links")
    op.drop_index("ix_issue_links_workspace_type", table_name="issue_links")
    op.drop_index("ix_issue_links_target", table_name="issue_links")
    op.drop_index("ix_issue_links_source", table_name="issue_links")
    op.drop_table("issue_links")

    # Drop enum
    postgresql.ENUM(name="issue_link_type").drop(op.get_bind(), checkfirst=True)
