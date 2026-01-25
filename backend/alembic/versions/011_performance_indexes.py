"""Add performance indexes for common query patterns.

Revision ID: 011_performance_indexes
Revises: 010_ai_context_entity
Create Date: 2026-01-24

T335: Database Query Optimization
- Add composite indexes for common query patterns
- Add full-text search indexes
- Optimize for list views with <100ms response time
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "011_performance_indexes"
down_revision: str | None = "010_ai_context_entity"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Add performance indexes for common query patterns."""
    # =========================================================================
    # Issues Table Indexes
    # =========================================================================

    # Composite index for workspace + state filtering (common query pattern)
    op.create_index(
        "ix_issues_workspace_state",
        "issues",
        ["workspace_id", "state_id"],
        postgresql_where=sa.text("is_deleted = false"),
    )

    # Composite index for project + created_at (list views sorted by date)
    op.create_index(
        "ix_issues_project_created",
        "issues",
        ["project_id", "created_at"],
        postgresql_where=sa.text("is_deleted = false"),
    )

    # Composite index for workspace + assignee (my issues view)
    op.create_index(
        "ix_issues_workspace_assignee",
        "issues",
        ["workspace_id", "assignee_id"],
        postgresql_where=sa.text("is_deleted = false AND assignee_id IS NOT NULL"),
    )

    # Composite index for cycle planning view
    op.create_index(
        "ix_issues_cycle_state",
        "issues",
        ["cycle_id", "state_id"],
        postgresql_where=sa.text("is_deleted = false AND cycle_id IS NOT NULL"),
    )

    # Composite index for module grouping
    op.create_index(
        "ix_issues_module_state",
        "issues",
        ["module_id", "state_id"],
        postgresql_where=sa.text("is_deleted = false AND module_id IS NOT NULL"),
    )

    # Composite index for priority filtering
    op.create_index(
        "ix_issues_workspace_priority",
        "issues",
        ["workspace_id", "priority"],
        postgresql_where=sa.text("is_deleted = false"),
    )

    # Composite index for date-based filtering
    op.create_index(
        "ix_issues_workspace_target_date",
        "issues",
        ["workspace_id", "target_date"],
        postgresql_where=sa.text("is_deleted = false AND target_date IS NOT NULL"),
    )

    # =========================================================================
    # Notes Table Indexes
    # =========================================================================

    # Composite index for workspace + pinned (pinned notes sidebar)
    op.create_index(
        "ix_notes_workspace_pinned",
        "notes",
        ["workspace_id", "is_pinned"],
        postgresql_where=sa.text("is_deleted = false"),
    )

    # Composite index for project notes list
    op.create_index(
        "ix_notes_project_updated",
        "notes",
        ["project_id", "updated_at"],
        postgresql_where=sa.text("is_deleted = false"),
    )

    # Composite index for owner's notes
    op.create_index(
        "ix_notes_workspace_owner",
        "notes",
        ["workspace_id", "owner_id"],
        postgresql_where=sa.text("is_deleted = false"),
    )

    # Full-text search index on title
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_notes_title_search
        ON notes USING gin(to_tsvector('english', title))
        WHERE is_deleted = false
    """)

    # =========================================================================
    # Activities Table Indexes
    # =========================================================================

    # Composite index for entity timeline (issue activity feed)
    op.create_index(
        "ix_activities_issue_type_created",
        "activities",
        ["issue_id", "activity_type", "created_at"],
        postgresql_where=sa.text("is_deleted = false"),
    )

    # Composite index for user activity feed
    op.create_index(
        "ix_activities_actor_created",
        "activities",
        ["actor_id", "created_at"],
        postgresql_where=sa.text("is_deleted = false"),
    )

    # =========================================================================
    # Annotations Table Indexes
    # =========================================================================

    # Index for note annotations panel
    op.create_index(
        "ix_note_annotations_note_created",
        "note_annotations",
        ["note_id", "created_at"],
        postgresql_where=sa.text("is_deleted = false"),
    )

    # Index for pending annotations
    op.create_index(
        "ix_note_annotations_note_pending",
        "note_annotations",
        ["note_id"],
        postgresql_where=sa.text("is_deleted = false AND status = 'pending'"),
    )

    # =========================================================================
    # Cycles Table Indexes
    # =========================================================================

    # Composite index for project cycles list
    op.create_index(
        "ix_cycles_project_status",
        "cycles",
        ["project_id", "status"],
        postgresql_where=sa.text("is_deleted = false"),
    )

    # Index for active cycles
    op.create_index(
        "ix_cycles_workspace_active",
        "cycles",
        ["workspace_id"],
        postgresql_where=sa.text("is_deleted = false AND status = 'active'"),
    )

    # =========================================================================
    # Embeddings Table Indexes (if not exists from migration 006)
    # =========================================================================

    # Composite index for workspace + content type searches
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_embeddings_workspace_type_active
        ON embeddings (workspace_id, content_type)
        WHERE is_deleted = false
    """)

    # =========================================================================
    # Workspace Members Table Indexes
    # =========================================================================

    # Index for user's workspaces (login/workspace selection)
    op.create_index(
        "ix_workspace_members_user_active",
        "workspace_members",
        ["user_id"],
        postgresql_where=sa.text("is_deleted = false"),
    )

    # =========================================================================
    # Projects Table Indexes
    # =========================================================================

    # Composite index for workspace projects list
    op.create_index(
        "ix_projects_workspace_created",
        "projects",
        ["workspace_id", "created_at"],
        postgresql_where=sa.text("is_deleted = false"),
    )

    # =========================================================================
    # Labels Table Indexes
    # =========================================================================

    # Composite index for project labels
    op.create_index(
        "ix_labels_project_name",
        "labels",
        ["project_id", "name"],
        postgresql_where=sa.text("is_deleted = false"),
    )

    # =========================================================================
    # Create Function for Query Explain Analysis
    # =========================================================================

    op.execute("""
        CREATE OR REPLACE FUNCTION explain_analyze_query(query_text text)
        RETURNS TABLE(query_plan text) AS $$
        BEGIN
            RETURN QUERY EXECUTE 'EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) ' || query_text;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;

        COMMENT ON FUNCTION explain_analyze_query IS 'Execute EXPLAIN ANALYZE on a query for performance debugging';
    """)

    # =========================================================================
    # Create Statistics Tables for Monitoring
    # =========================================================================

    op.execute("""
        CREATE TABLE IF NOT EXISTS query_performance_log (
            id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
            query_signature text NOT NULL,
            execution_time_ms double precision NOT NULL,
            rows_affected integer,
            called_at timestamp with time zone DEFAULT now(),
            caller_info jsonb
        );

        CREATE INDEX ix_query_perf_signature ON query_performance_log (query_signature);
        CREATE INDEX ix_query_perf_time ON query_performance_log (called_at);

        COMMENT ON TABLE query_performance_log IS 'Log slow queries for performance analysis';
    """)

    # =========================================================================
    # Update Table Statistics for Query Planner
    # =========================================================================

    # Analyze tables to update statistics for query optimizer
    op.execute("ANALYZE issues")
    op.execute("ANALYZE notes")
    op.execute("ANALYZE activities")
    op.execute("ANALYZE cycles")
    op.execute("ANALYZE embeddings")
    op.execute("ANALYZE workspace_members")
    op.execute("ANALYZE projects")
    op.execute("ANALYZE labels")


def downgrade() -> None:
    """Remove performance indexes."""
    # Drop query performance log
    op.execute("DROP TABLE IF EXISTS query_performance_log")
    op.execute("DROP FUNCTION IF EXISTS explain_analyze_query")

    # Drop labels indexes
    op.drop_index("ix_labels_project_name", table_name="labels")

    # Drop projects indexes
    op.drop_index("ix_projects_workspace_created", table_name="projects")

    # Drop workspace members indexes
    op.drop_index("ix_workspace_members_user_active", table_name="workspace_members")

    # Drop embeddings indexes (if we created them)
    op.execute("DROP INDEX IF EXISTS ix_embeddings_workspace_type_active")

    # Drop cycles indexes
    op.drop_index("ix_cycles_workspace_active", table_name="cycles")
    op.drop_index("ix_cycles_project_status", table_name="cycles")

    # Drop annotations indexes
    op.drop_index("ix_note_annotations_note_pending", table_name="note_annotations")
    op.drop_index("ix_note_annotations_note_created", table_name="note_annotations")

    # Drop activities indexes
    op.drop_index("ix_activities_actor_created", table_name="activities")
    op.drop_index("ix_activities_issue_type_created", table_name="activities")

    # Drop notes indexes
    op.execute("DROP INDEX IF EXISTS ix_notes_title_search")
    op.drop_index("ix_notes_workspace_owner", table_name="notes")
    op.drop_index("ix_notes_project_updated", table_name="notes")
    op.drop_index("ix_notes_workspace_pinned", table_name="notes")

    # Drop issues indexes
    op.drop_index("ix_issues_workspace_target_date", table_name="issues")
    op.drop_index("ix_issues_workspace_priority", table_name="issues")
    op.drop_index("ix_issues_module_state", table_name="issues")
    op.drop_index("ix_issues_cycle_state", table_name="issues")
    op.drop_index("ix_issues_workspace_assignee", table_name="issues")
    op.drop_index("ix_issues_project_created", table_name="issues")
    op.drop_index("ix_issues_workspace_state", table_name="issues")
