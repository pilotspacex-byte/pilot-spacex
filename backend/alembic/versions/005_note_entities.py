"""Create Note entities for Note-First workflow.

Revision ID: 005_note_entities
Revises: 004_rls_policies
Create Date: 2026-01-24

Creates tables for:
- templates: Reusable document structures
- notes: Primary collaborative documents
- note_annotations: AI suggestions in right margin
- threaded_discussions: Discussion threads on notes
- discussion_comments: Individual comments in threads
- note_issue_links: Relationships between notes and issues
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005_note_entities"
down_revision: str | None = "004_rls_policies"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Create Note entities tables."""
    # Create annotation_type enum
    annotation_type = postgresql.ENUM(
        "suggestion",
        "warning",
        "issue_candidate",
        "info",
        name="annotation_type",
        create_type=True,
    )
    annotation_type.create(op.get_bind(), checkfirst=True)

    # Create annotation_status enum
    annotation_status = postgresql.ENUM(
        "pending",
        "accepted",
        "rejected",
        "dismissed",
        name="annotation_status",
        create_type=True,
    )
    annotation_status.create(op.get_bind(), checkfirst=True)

    # Create discussion_status enum
    discussion_status = postgresql.ENUM(
        "open",
        "resolved",
        name="discussion_status",
        create_type=True,
    )
    discussion_status.create(op.get_bind(), checkfirst=True)

    # Create note_link_type enum
    note_link_type = postgresql.ENUM(
        "extracted",
        "referenced",
        "related",
        name="note_link_type",
        create_type=True,
    )
    note_link_type.create(op.get_bind(), checkfirst=True)

    # Create templates table
    op.create_table(
        "templates",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "content", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_templates_workspace_id", "templates", ["workspace_id"])
    op.create_index("ix_templates_category", "templates", ["category"])
    op.create_index("ix_templates_is_default", "templates", ["is_default"])
    op.create_index("ix_templates_is_deleted", "templates", ["is_deleted"])
    op.create_index("ix_templates_name", "templates", ["name"])

    # Create notes table
    op.create_table(
        "notes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column(
            "content", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("word_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("reading_time_mins", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("is_pinned", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["template_id"], ["templates.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notes_workspace_id", "notes", ["workspace_id"])
    op.create_index("ix_notes_project_id", "notes", ["project_id"])
    op.create_index("ix_notes_workspace_project", "notes", ["workspace_id", "project_id"])
    op.create_index("ix_notes_owner_id", "notes", ["owner_id"])
    op.create_index("ix_notes_template_id", "notes", ["template_id"])
    op.create_index("ix_notes_is_pinned", "notes", ["is_pinned"])
    op.create_index("ix_notes_is_deleted", "notes", ["is_deleted"])
    op.create_index("ix_notes_created_at", "notes", ["created_at"])
    # Full-text search index on title
    op.execute("CREATE INDEX ix_notes_title_text ON notes USING gin(to_tsvector('english', title))")

    # Create note_annotations table
    op.create_table(
        "note_annotations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("note_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("block_id", sa.String(100), nullable=False),
        sa.Column(
            "type",
            postgresql.ENUM(
                "suggestion",
                "warning",
                "issue_candidate",
                "info",
                name="annotation_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), server_default=sa.text("0.5"), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "pending",
                "accepted",
                "rejected",
                "dismissed",
                name="annotation_status",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("ai_metadata", postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["note_id"], ["notes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_note_annotations_workspace_id", "note_annotations", ["workspace_id"])
    op.create_index("ix_note_annotations_note_id", "note_annotations", ["note_id"])
    op.create_index("ix_note_annotations_block_id", "note_annotations", ["block_id"])
    op.create_index("ix_note_annotations_type", "note_annotations", ["type"])
    op.create_index("ix_note_annotations_status", "note_annotations", ["status"])
    op.create_index("ix_note_annotations_confidence", "note_annotations", ["confidence"])
    op.create_index("ix_note_annotations_is_deleted", "note_annotations", ["is_deleted"])
    op.create_index("ix_note_annotations_note_block", "note_annotations", ["note_id", "block_id"])

    # Create threaded_discussions table
    op.create_table(
        "threaded_discussions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("note_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("block_id", sa.String(100), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM("open", "resolved", name="discussion_status", create_type=False),
            nullable=False,
        ),
        sa.Column("resolved_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["note_id"], ["notes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resolved_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_threaded_discussions_workspace_id", "threaded_discussions", ["workspace_id"]
    )
    op.create_index("ix_threaded_discussions_note_id", "threaded_discussions", ["note_id"])
    op.create_index("ix_threaded_discussions_block_id", "threaded_discussions", ["block_id"])
    op.create_index("ix_threaded_discussions_status", "threaded_discussions", ["status"])
    op.create_index(
        "ix_threaded_discussions_resolved_by_id", "threaded_discussions", ["resolved_by_id"]
    )
    op.create_index("ix_threaded_discussions_is_deleted", "threaded_discussions", ["is_deleted"])
    op.create_index(
        "ix_threaded_discussions_note_block", "threaded_discussions", ["note_id", "block_id"]
    )

    # Create discussion_comments table
    op.create_table(
        "discussion_comments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("discussion_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_ai_generated", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["discussion_id"], ["threaded_discussions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_discussion_comments_workspace_id", "discussion_comments", ["workspace_id"])
    op.create_index(
        "ix_discussion_comments_discussion_id", "discussion_comments", ["discussion_id"]
    )
    op.create_index("ix_discussion_comments_author_id", "discussion_comments", ["author_id"])
    op.create_index(
        "ix_discussion_comments_is_ai_generated", "discussion_comments", ["is_ai_generated"]
    )
    op.create_index("ix_discussion_comments_is_deleted", "discussion_comments", ["is_deleted"])
    op.create_index("ix_discussion_comments_created_at", "discussion_comments", ["created_at"])

    # Create note_issue_links table
    op.create_table(
        "note_issue_links",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("note_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("issue_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "link_type",
            postgresql.ENUM(
                "extracted", "referenced", "related", name="note_link_type", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("block_id", sa.String(100), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["note_id"], ["notes.id"], ondelete="CASCADE"),
        # Note: issue_id FK will be added when Issue model is created
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "note_id", "issue_id", "link_type", name="uq_note_issue_links_note_issue_type"
        ),
    )
    op.create_index("ix_note_issue_links_workspace_id", "note_issue_links", ["workspace_id"])
    op.create_index("ix_note_issue_links_note_id", "note_issue_links", ["note_id"])
    op.create_index("ix_note_issue_links_issue_id", "note_issue_links", ["issue_id"])
    op.create_index("ix_note_issue_links_link_type", "note_issue_links", ["link_type"])
    op.create_index("ix_note_issue_links_is_deleted", "note_issue_links", ["is_deleted"])

    # Add RLS policies for new tables
    _create_rls_policies()


def _create_rls_policies() -> None:
    """Create RLS policies for Note entities."""
    # Templates RLS
    op.execute("""
        ALTER TABLE templates ENABLE ROW LEVEL SECURITY;
        ALTER TABLE templates FORCE ROW LEVEL SECURITY;

        CREATE POLICY "templates_workspace_member"
        ON templates
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

    # Notes RLS
    op.execute("""
        ALTER TABLE notes ENABLE ROW LEVEL SECURITY;
        ALTER TABLE notes FORCE ROW LEVEL SECURITY;

        CREATE POLICY "notes_workspace_member"
        ON notes
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

    # Note annotations RLS
    op.execute("""
        ALTER TABLE note_annotations ENABLE ROW LEVEL SECURITY;
        ALTER TABLE note_annotations FORCE ROW LEVEL SECURITY;

        CREATE POLICY "note_annotations_workspace_member"
        ON note_annotations
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

    # Threaded discussions RLS
    op.execute("""
        ALTER TABLE threaded_discussions ENABLE ROW LEVEL SECURITY;
        ALTER TABLE threaded_discussions FORCE ROW LEVEL SECURITY;

        CREATE POLICY "threaded_discussions_workspace_member"
        ON threaded_discussions
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

    # Discussion comments RLS
    op.execute("""
        ALTER TABLE discussion_comments ENABLE ROW LEVEL SECURITY;
        ALTER TABLE discussion_comments FORCE ROW LEVEL SECURITY;

        CREATE POLICY "discussion_comments_workspace_member"
        ON discussion_comments
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

    # Note issue links RLS
    op.execute("""
        ALTER TABLE note_issue_links ENABLE ROW LEVEL SECURITY;
        ALTER TABLE note_issue_links FORCE ROW LEVEL SECURITY;

        CREATE POLICY "note_issue_links_workspace_member"
        ON note_issue_links
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
    """Drop Note entities tables and RLS policies."""
    # Drop RLS policies
    tables = [
        "note_issue_links",
        "discussion_comments",
        "threaded_discussions",
        "note_annotations",
        "notes",
        "templates",
    ]

    for table in tables:
        op.execute(f"""
            DROP POLICY IF EXISTS "{table}_workspace_member" ON {table};
            ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;
        """)

    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table("note_issue_links")
    op.drop_table("discussion_comments")
    op.drop_table("threaded_discussions")
    op.drop_table("note_annotations")
    # Drop full-text index first
    op.execute("DROP INDEX IF EXISTS ix_notes_title_text")
    op.drop_table("notes")
    op.drop_table("templates")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS note_link_type")
    op.execute("DROP TYPE IF EXISTS discussion_status")
    op.execute("DROP TYPE IF EXISTS annotation_status")
    op.execute("DROP TYPE IF EXISTS annotation_type")
