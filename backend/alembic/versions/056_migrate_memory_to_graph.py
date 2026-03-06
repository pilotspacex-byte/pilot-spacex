"""Migrate memory_entries data to graph_nodes.

Revision ID: 056_migrate_memory_to_graph
Revises: 055_add_knowledge_graph_tables
Create Date: 2026-03-03

This migration copies existing memory_entries rows to graph_nodes as typed nodes.
memory_entries table is NOT dropped — kept for rollback safety.

Migration also drops and recreates the node_type CHECK constraint on graph_nodes
to include the node types needed for migrated memory entries
(work_intent, skill_outcome, learned_pattern, constitution_rule) which were
absent from the constraint defined in migration 055.
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision: str = "056_migrate_memory_to_graph"
down_revision: str | None = "055_add_knowledge_graph_tables"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Extend node_type CHECK constraint and migrate memory_entries rows to graph_nodes."""

    # ------------------------------------------------------------------
    # Step 1: Extend the node_type CHECK constraint on graph_nodes to
    # include node types produced by the memory engine migration.
    # The constraint was created inline in the CREATE TABLE in 055, so we
    # must drop it by name and recreate it with the full value set.
    # ------------------------------------------------------------------
    op.execute(
        text(
            """
        ALTER TABLE graph_nodes
        DROP CONSTRAINT IF EXISTS graph_nodes_node_type_check
    """
        )
    )

    op.execute(
        text(
            """
        ALTER TABLE graph_nodes
        ADD CONSTRAINT graph_nodes_node_type_check
        CHECK (node_type IN (
            'issue', 'note', 'concept', 'agent', 'user',
            'workspace', 'project', 'cycle', 'label',
            'comment', 'document', 'task', 'sprint', 'epic',
            'work_intent', 'skill_outcome', 'learned_pattern',
            'constitution_rule', 'pull_request', 'code_reference',
            'decision', 'conversation_summary', 'user_preference'
        ))
    """
        )
    )

    # ------------------------------------------------------------------
    # Step 2: Copy non-deleted, non-expired memory_entries into graph_nodes.
    #
    # Mapping:
    #   source_type 'intent'          -> node_type 'work_intent'
    #   source_type 'skill_outcome'   -> node_type 'skill_outcome'
    #   source_type 'user_feedback'   -> node_type 'learned_pattern'
    #   source_type 'constitution'    -> node_type 'constitution_rule'
    #   (fallback)                    -> node_type 'skill_outcome'
    #
    # embedding is deliberately NOT migrated: memory_entries carry
    # 768-dim Gemini vectors; graph_nodes expects 1536-dim OpenAI vectors.
    # Migrated nodes will be re-embedded by the graph embedding worker.
    # ------------------------------------------------------------------
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # Only migrate if memory_entries table exists (it was created by
        # migration 040_add_memory_engine which may not be in every environment).
        table_exists = bind.execute(
            text(
                """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'memory_entries'
            )
        """
            )
        ).scalar()

        if table_exists:
            op.execute(
                text(
                    """
                INSERT INTO graph_nodes (
                    id,
                    workspace_id,
                    user_id,
                    node_type,
                    external_id,
                    label,
                    content,
                    properties,
                    embedding,
                    created_at,
                    updated_at
                )
                SELECT
                    gen_random_uuid(),
                    me.workspace_id,
                    NULL,
                    CASE me.source_type
                        WHEN 'intent'        THEN 'work_intent'
                        WHEN 'skill_outcome' THEN 'skill_outcome'
                        WHEN 'user_feedback' THEN 'learned_pattern'
                        WHEN 'constitution'  THEN 'constitution_rule'
                        ELSE                      'skill_outcome'
                    END,
                    me.source_id,
                    SUBSTR(me.content, 1, 100),
                    me.content,
                    jsonb_build_object(
                        'migrated_from', 'memory_entries',
                        'source_type',   me.source_type::text,
                        'pinned',        me.pinned
                    ),
                    NULL,
                    me.created_at,
                    COALESCE(me.updated_at, me.created_at)
                FROM memory_entries me
                WHERE
                    me.is_deleted = FALSE
                    AND (me.expires_at IS NULL OR me.expires_at > NOW())
            """
                )
            )


def downgrade() -> None:
    """Remove migrated nodes and restore original CHECK constraint."""

    # Remove all rows that were inserted by this migration
    op.execute(
        text(
            """
        DELETE FROM graph_nodes
        WHERE properties->>'migrated_from' = 'memory_entries'
    """
        )
    )

    # Restore the narrower CHECK constraint from migration 055
    op.execute(
        text(
            """
        ALTER TABLE graph_nodes
        DROP CONSTRAINT IF EXISTS graph_nodes_node_type_check
    """
        )
    )

    op.execute(
        text(
            """
        ALTER TABLE graph_nodes
        ADD CONSTRAINT graph_nodes_node_type_check
        CHECK (node_type IN (
            'issue', 'note', 'concept', 'agent', 'user',
            'workspace', 'project', 'cycle', 'label',
            'comment', 'document', 'task', 'sprint', 'epic'
        ))
    """
        )
    )
