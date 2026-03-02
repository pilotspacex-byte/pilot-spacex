"""Add memory engine tables.

Creates memory_entries, constitution_rules, and memory_dlq tables for the
AI memory engine (Feature 015 Sprint 2 Phase 2a).

Revision ID: 040_add_memory_engine
Revises: 039_add_skill_executions
Create Date: 2026-02-19
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision = "040_add_memory_engine"
down_revision = "039_add_skill_executions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create memory engine tables with RLS, indexes, and vector support."""
    # 1. Create enums
    # op.execute("""
    #     CREATE TYPE memory_source_type_enum AS ENUM (
    #         'intent',
    #         'skill_outcome',
    #         'user_feedback',
    #         'constitution'
    #     )
    # """)

    # op.execute("""
    #     CREATE TYPE constitution_severity_enum AS ENUM (
    #         'must',
    #         'should',
    #         'may'
    #     )
    # """)

    # 2. Create memory_entries table
    op.create_table(
        "memory_entries",
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
        sa.Column("content", sa.Text(), nullable=False),
        # embedding: vector(768) — created via raw SQL to use pgvector syntax
        sa.Column("keywords", sa.Text(), nullable=True),  # stored as tsvector via SQL
        sa.Column(
            "source_type",
            sa.Enum(
                "intent",
                "skill_outcome",
                "user_feedback",
                "constitution",
                name="memory_source_type_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("source_id", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "pinned",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        # Soft delete columns (BaseModel convention)
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # Add vector column and tsvector column via raw SQL (pgvector syntax)
    op.execute("""
        ALTER TABLE memory_entries
        ADD COLUMN embedding vector(768)
    """)

    op.execute("""
        ALTER TABLE memory_entries
        ALTER COLUMN keywords TYPE tsvector
        USING to_tsvector('english', coalesce(keywords, ''))
    """)

    # 3. Indexes for memory_entries
    op.create_index(
        "ix_memory_entries_workspace_id",
        "memory_entries",
        ["workspace_id"],
    )
    op.create_index(
        "ix_memory_entries_source_type",
        "memory_entries",
        ["source_type"],
    )
    op.create_index(
        "ix_memory_entries_pinned",
        "memory_entries",
        ["workspace_id", "pinned"],
    )
    op.create_index(
        "ix_memory_entries_expires_at",
        "memory_entries",
        ["expires_at"],
    )

    # HNSW index for embedding (cosine similarity, pgvector)
    op.execute("""
        CREATE INDEX ix_memory_entries_embedding_hnsw
        ON memory_entries
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)

    # GIN index for tsvector full-text search
    op.execute("""
        CREATE INDEX ix_memory_entries_keywords_gin
        ON memory_entries
        USING gin (keywords)
    """)

    # 4. RLS for memory_entries
    op.execute("ALTER TABLE memory_entries ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE memory_entries FORCE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY "memory_entries_workspace_isolation"
        ON memory_entries FOR ALL
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
    """)

    # 5. Create constitution_rules table
    op.create_table(
        "constitution_rules",
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
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "severity",
            sa.Enum(
                "must",
                "should",
                "may",
                name="constitution_severity_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column("source_block_id", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # Soft delete columns (BaseModel convention)
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # 6. Indexes for constitution_rules
    op.create_index(
        "ix_constitution_rules_workspace_version",
        "constitution_rules",
        ["workspace_id", "version"],
    )
    op.create_index(
        "ix_constitution_rules_workspace_active",
        "constitution_rules",
        ["workspace_id", "active"],
    )

    # 7. RLS for constitution_rules
    op.execute("ALTER TABLE constitution_rules ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE constitution_rules FORCE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY "constitution_rules_workspace_isolation"
        ON constitution_rules FOR ALL
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
    """)

    # 8. Create memory_dlq table (dead letter queue — no RLS bypass needed, service-only)
    op.create_table(
        "memory_dlq",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "attempts",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index(
        "ix_memory_dlq_workspace_id",
        "memory_dlq",
        ["workspace_id"],
    )
    op.create_index(
        "ix_memory_dlq_next_retry_at",
        "memory_dlq",
        ["next_retry_at"],
    )


def downgrade() -> None:
    """Remove memory engine tables and supporting objects."""
    # memory_dlq
    op.drop_index("ix_memory_dlq_next_retry_at", table_name="memory_dlq")
    op.drop_index("ix_memory_dlq_workspace_id", table_name="memory_dlq")
    op.drop_table("memory_dlq")

    # constitution_rules
    op.execute(
        'DROP POLICY IF EXISTS "constitution_rules_workspace_isolation" ON constitution_rules'
    )
    op.execute("ALTER TABLE constitution_rules DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_constitution_rules_workspace_active", table_name="constitution_rules")
    op.drop_index("ix_constitution_rules_workspace_version", table_name="constitution_rules")
    op.drop_table("constitution_rules")

    # memory_entries
    op.execute('DROP POLICY IF EXISTS "memory_entries_workspace_isolation" ON memory_entries')
    op.execute("ALTER TABLE memory_entries DISABLE ROW LEVEL SECURITY")
    op.execute("DROP INDEX IF EXISTS ix_memory_entries_keywords_gin")
    op.execute("DROP INDEX IF EXISTS ix_memory_entries_embedding_hnsw")
    op.drop_index("ix_memory_entries_expires_at", table_name="memory_entries")
    op.drop_index("ix_memory_entries_pinned", table_name="memory_entries")
    op.drop_index("ix_memory_entries_source_type", table_name="memory_entries")
    op.drop_index("ix_memory_entries_workspace_id", table_name="memory_entries")
    op.drop_table("memory_entries")

    # Enums
    op.execute("DROP TYPE IF EXISTS constitution_severity_enum")
    op.execute("DROP TYPE IF EXISTS memory_source_type_enum")
