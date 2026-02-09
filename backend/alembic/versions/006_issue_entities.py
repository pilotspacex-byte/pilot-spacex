"""Create Issue entities for AI Issue Creation.

Revision ID: 006_issue_entities
Revises: 005_note_entities
Create Date: 2026-01-24

Creates tables for:
- cycles: Sprint/iteration containers
- issues: Core work item entity with AI metadata
- issue_labels: Many-to-many junction table
- activities: Issue audit trail
- embeddings: Vector embeddings for similarity search

T121: Create migrations for Issue entities.
T136: Create Embedding table with HNSW index.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006_issue_entities"
down_revision: str | None = "005_note_entities"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Create Issue entities tables."""
    # Create issue_priority enum
    issue_priority = postgresql.ENUM(
        "none",
        "low",
        "medium",
        "high",
        "urgent",
        name="issue_priority",
        create_type=True,
    )
    issue_priority.create(op.get_bind(), checkfirst=True)

    # Create cycle_status enum
    cycle_status = postgresql.ENUM(
        "draft",
        "planned",
        "active",
        "completed",
        "cancelled",
        name="cycle_status",
        create_type=True,
    )
    cycle_status.create(op.get_bind(), checkfirst=True)

    # Create activity_type enum
    activity_type = postgresql.ENUM(
        "created",
        "updated",
        "deleted",
        "restored",
        "state_changed",
        "priority_changed",
        "assigned",
        "unassigned",
        "added_to_cycle",
        "removed_from_cycle",
        "added_to_module",
        "removed_from_module",
        "label_added",
        "label_removed",
        "parent_set",
        "parent_removed",
        "sub_issue_added",
        "sub_issue_removed",
        "start_date_set",
        "target_date_set",
        "estimate_set",
        "linked_to_note",
        "unlinked_from_note",
        "comment_added",
        "comment_updated",
        "comment_deleted",
        "ai_enhanced",
        "ai_suggestion_accepted",
        "ai_suggestion_rejected",
        "duplicate_detected",
        "duplicate_marked",
        name="activity_type",
        create_type=True,
    )
    activity_type.create(op.get_bind(), checkfirst=True)

    # Create embedding_type enum
    embedding_type = postgresql.ENUM(
        "issue",
        "note",
        "note_block",
        "comment",
        "code_snippet",
        name="embedding_type",
        create_type=True,
    )
    embedding_type.create(op.get_bind(), checkfirst=True)

    # Create cycles table
    op.create_table(
        "cycles",
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
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "draft",
                "planned",
                "active",
                "completed",
                "cancelled",
                name="cycle_status",
                create_type=False,
            ),
            server_default="draft",
            nullable=False,
        ),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("sequence", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("owned_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owned_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "name", name="uq_cycles_project_name"),
    )
    op.create_index("ix_cycles_workspace_id", "cycles", ["workspace_id"])
    op.create_index("ix_cycles_project_id", "cycles", ["project_id"])
    op.create_index("ix_cycles_status", "cycles", ["status"])
    op.create_index("ix_cycles_start_date", "cycles", ["start_date"])
    op.create_index("ix_cycles_end_date", "cycles", ["end_date"])
    op.create_index("ix_cycles_is_deleted", "cycles", ["is_deleted"])

    # Create issues table
    op.create_table(
        "issues",
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
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("description_html", sa.Text(), nullable=True),
        sa.Column(
            "priority",
            postgresql.ENUM(
                "none",
                "low",
                "medium",
                "high",
                "urgent",
                name="issue_priority",
                create_type=False,
            ),
            server_default="none",
            nullable=False,
        ),
        sa.Column("state_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assignee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reporter_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cycle_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("module_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("estimate_points", sa.Integer(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("ai_metadata", postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["state_id"], ["states.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assignee_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reporter_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cycle_id"], ["cycles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["module_id"], ["modules.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["parent_id"], ["issues.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "sequence_id", name="uq_issues_project_sequence"),
    )
    # Create indexes
    op.create_index("ix_issues_workspace_id", "issues", ["workspace_id"])
    op.create_index("ix_issues_project_id", "issues", ["project_id"])
    op.create_index("ix_issues_state_id", "issues", ["state_id"])
    op.create_index("ix_issues_assignee_id", "issues", ["assignee_id"])
    op.create_index("ix_issues_reporter_id", "issues", ["reporter_id"])
    op.create_index("ix_issues_cycle_id", "issues", ["cycle_id"])
    op.create_index("ix_issues_module_id", "issues", ["module_id"])
    op.create_index("ix_issues_parent_id", "issues", ["parent_id"])
    op.create_index("ix_issues_priority", "issues", ["priority"])
    op.create_index("ix_issues_is_deleted", "issues", ["is_deleted"])
    op.create_index("ix_issues_created_at", "issues", ["created_at"])
    op.create_index("ix_issues_target_date", "issues", ["target_date"])
    op.create_index("ix_issues_project_state", "issues", ["project_id", "state_id"])
    op.create_index("ix_issues_project_assignee", "issues", ["project_id", "assignee_id"])
    op.create_index("ix_issues_workspace_project", "issues", ["workspace_id", "project_id"])
    # Full-text search index on name
    op.execute("CREATE INDEX ix_issues_name_text ON issues USING gin(to_tsvector('english', name))")

    # Create issue_labels junction table
    op.create_table(
        "issue_labels",
        sa.Column(
            "issue_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "label_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["issue_id"], ["issues.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["label_id"], ["labels.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("issue_id", "label_id"),
    )
    op.create_index("ix_issue_labels_issue_id", "issue_labels", ["issue_id"])
    op.create_index("ix_issue_labels_label_id", "issue_labels", ["label_id"])

    # Create activities table
    op.create_table(
        "activities",
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
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("issue_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "activity_type",
            postgresql.ENUM(
                "created",
                "updated",
                "deleted",
                "restored",
                "state_changed",
                "priority_changed",
                "assigned",
                "unassigned",
                "added_to_cycle",
                "removed_from_cycle",
                "added_to_module",
                "removed_from_module",
                "label_added",
                "label_removed",
                "parent_set",
                "parent_removed",
                "sub_issue_added",
                "sub_issue_removed",
                "start_date_set",
                "target_date_set",
                "estimate_set",
                "linked_to_note",
                "unlinked_from_note",
                "comment_added",
                "comment_updated",
                "comment_deleted",
                "ai_enhanced",
                "ai_suggestion_accepted",
                "ai_suggestion_rejected",
                "duplicate_detected",
                "duplicate_marked",
                name="activity_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("field", sa.String(100), nullable=True),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["issue_id"], ["issues.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_activities_workspace_id", "activities", ["workspace_id"])
    op.create_index("ix_activities_issue_id", "activities", ["issue_id"])
    op.create_index("ix_activities_actor_id", "activities", ["actor_id"])
    op.create_index("ix_activities_activity_type", "activities", ["activity_type"])
    op.create_index("ix_activities_is_deleted", "activities", ["is_deleted"])
    op.create_index("ix_activities_created_at", "activities", ["created_at"])
    op.create_index("ix_activities_issue_created", "activities", ["issue_id", "created_at"])

    # Create embeddings table with pgvector
    op.create_table(
        "embeddings",
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
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "content_type",
            postgresql.ENUM(
                "issue",
                "note",
                "note_block",
                "comment",
                "code_snippet",
                name="embedding_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("content_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("content_preview", sa.Text(), nullable=True),
        sa.Column("model", sa.String(100), server_default="text-embedding-3-large", nullable=False),
        sa.Column("dimensions", sa.Integer(), server_default=sa.text("1536"), nullable=False),
        sa.Column("token_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    # Add vector column using pgvector
    op.execute("ALTER TABLE embeddings ADD COLUMN embedding vector(1536)")
    # Create indexes
    op.create_index("ix_embeddings_workspace_id", "embeddings", ["workspace_id"])
    op.create_index("ix_embeddings_content_type", "embeddings", ["content_type"])
    op.create_index("ix_embeddings_content_id", "embeddings", ["content_id"])
    op.create_index("ix_embeddings_content_hash", "embeddings", ["content_hash"])
    op.create_index("ix_embeddings_project_id", "embeddings", ["project_id"])
    op.create_index("ix_embeddings_is_deleted", "embeddings", ["is_deleted"])
    op.create_index("ix_embeddings_type_content", "embeddings", ["content_type", "content_id"])
    op.create_index("ix_embeddings_workspace_type", "embeddings", ["workspace_id", "content_type"])
    # Create HNSW index for similarity search (per T136)
    # Using cosine distance operator (<=>)
    op.execute("""
        CREATE INDEX ix_embeddings_hnsw ON embeddings
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)

    # Add FK to note_issue_links for issues
    op.create_foreign_key(
        "fk_note_issue_links_issue",
        "note_issue_links",
        "issues",
        ["issue_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Create sequence for issue identifiers per project
    op.execute("""
        CREATE OR REPLACE FUNCTION get_next_issue_sequence(p_project_id uuid)
        RETURNS integer AS $$
        DECLARE
            next_seq integer;
        BEGIN
            -- Advisory lock on project_id to prevent race conditions
            PERFORM pg_advisory_xact_lock(hashtext(p_project_id::text));

            SELECT COALESCE(MAX(sequence_id), 0) + 1
            INTO next_seq
            FROM issues
            WHERE project_id = p_project_id;
            RETURN next_seq;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create RLS policies
    _create_rls_policies()


def _create_rls_policies() -> None:
    """Create RLS policies for Issue entities."""
    # Cycles RLS
    op.execute("""
        ALTER TABLE cycles ENABLE ROW LEVEL SECURITY;
        ALTER TABLE cycles FORCE ROW LEVEL SECURITY;

        CREATE POLICY "cycles_workspace_member"
        ON cycles
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

    # Issues RLS
    op.execute("""
        ALTER TABLE issues ENABLE ROW LEVEL SECURITY;
        ALTER TABLE issues FORCE ROW LEVEL SECURITY;

        CREATE POLICY "issues_workspace_member"
        ON issues
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

    # Activities RLS
    op.execute("""
        ALTER TABLE activities ENABLE ROW LEVEL SECURITY;
        ALTER TABLE activities FORCE ROW LEVEL SECURITY;

        CREATE POLICY "activities_workspace_member"
        ON activities
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

    # Embeddings RLS
    op.execute("""
        ALTER TABLE embeddings ENABLE ROW LEVEL SECURITY;
        ALTER TABLE embeddings FORCE ROW LEVEL SECURITY;

        CREATE POLICY "embeddings_workspace_member"
        ON embeddings
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
    """Drop Issue entities tables and RLS policies."""
    # Drop RLS policies
    tables = ["embeddings", "activities", "issues", "cycles"]
    for table in tables:
        op.execute(f"""
            DROP POLICY IF EXISTS "{table}_workspace_member" ON {table};
            ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;
        """)

    # Drop FK from note_issue_links
    op.drop_constraint("fk_note_issue_links_issue", "note_issue_links", type_="foreignkey")

    # Drop sequence function
    op.execute("DROP FUNCTION IF EXISTS get_next_issue_sequence(uuid)")

    # Drop tables in reverse order
    op.execute("DROP INDEX IF EXISTS ix_embeddings_hnsw")
    op.drop_table("embeddings")
    op.drop_table("activities")
    op.drop_table("issue_labels")
    op.execute("DROP INDEX IF EXISTS ix_issues_name_text")
    op.drop_table("issues")
    op.drop_table("cycles")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS embedding_type")
    op.execute("DROP TYPE IF EXISTS activity_type")
    op.execute("DROP TYPE IF EXISTS cycle_status")
    op.execute("DROP TYPE IF EXISTS issue_priority")
