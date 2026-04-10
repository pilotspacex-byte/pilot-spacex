"""Extend graph_nodes node_type for Phase 69 memory substrate.

Phase 69 Decision Point 1 locks the substrate as ``graph_nodes`` (the
older ``memory_entries`` table is deprecated). This migration adds the
three new node_type values required by the memory pipeline (MEM-01):

    - agent_turn         : one turn in an AI session (user + assistant)
    - user_correction    : explicit user correction of an AI output
    - pr_review_finding  : a single finding from a PR review

It also creates two supporting indexes:

    - ``ix_graph_nodes_properties_gin`` — GIN over ``properties`` JSONB
      so membership lookups (``properties @> '{...}'``) are fast.
    - ``uq_graph_nodes_agent_turn_cache`` — partial UNIQUE on
      ``(workspace_id, (properties->>'session_id'),
      (properties->>'turn_index')::int)`` WHERE ``node_type='agent_turn'``
      so replayed agent turns dedupe deterministically.

Note: ``graph_nodes.node_type`` is enforced via a CHECK constraint
(not a Postgres ENUM type; see migration 096). Extending it therefore
means dropping and re-creating the CHECK constraint.

Revision ID: 106_phase69_memory_node_types
Revises: 105_workspace_tool_permissions
Create Date: 2026-04-07
"""

from __future__ import annotations

from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "106_phase69_memory_node_types"
down_revision: str | None = "105_workspace_tool_permissions"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


# Full value list = previous (from migration 096) + 3 new Phase 69 types.
_PHASE69_NODE_TYPES = (
    "'issue', 'note', 'note_chunk', 'concept', 'agent', 'user', "
    "'workspace', 'project', 'cycle', 'label', "
    "'comment', 'document', 'document_chunk', 'task', 'sprint', 'epic', "
    "'work_intent', 'skill_outcome', 'learned_pattern', "
    "'constitution_rule', 'pull_request', 'branch', 'code_reference', "
    "'decision', 'conversation_summary', 'user_preference', "
    # Phase 69 additions:
    "'agent_turn', 'user_correction', 'pr_review_finding'"
)

_PRE_PHASE69_NODE_TYPES = (
    "'issue', 'note', 'note_chunk', 'concept', 'agent', 'user', "
    "'workspace', 'project', 'cycle', 'label', "
    "'comment', 'document', 'task', 'sprint', 'epic', "
    "'work_intent', 'skill_outcome', 'learned_pattern', "
    "'constitution_rule', 'pull_request', 'branch', 'code_reference', "
    "'decision', 'conversation_summary', 'user_preference'"
)


def upgrade() -> None:
    # 1. Replace the node_type CHECK constraint to include Phase 69 values.
    op.execute(
        text("ALTER TABLE graph_nodes DROP CONSTRAINT IF EXISTS graph_nodes_node_type_check")
    )
    op.execute(
        text(
            f"""
            ALTER TABLE graph_nodes
            ADD CONSTRAINT graph_nodes_node_type_check
            CHECK (node_type IN ({_PHASE69_NODE_TYPES}))
            """
        )
    )

    # 2. GIN index over JSONB properties for cheap membership queries.
    op.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS ix_graph_nodes_properties_gin
            ON graph_nodes
            USING GIN (properties)
            """
        )
    )

    # 3. Partial UNIQUE index scoping agent_turn dedup to
    #    (workspace_id, session_id, turn_index).
    op.execute(
        text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_graph_nodes_agent_turn_cache
            ON graph_nodes (
                workspace_id,
                (properties->>'session_id'),
                ((properties->>'turn_index')::int)
            )
            WHERE node_type = 'agent_turn'
            """
        )
    )


def downgrade() -> None:
    op.execute(text("DROP INDEX IF EXISTS uq_graph_nodes_agent_turn_cache"))
    op.execute(text("DROP INDEX IF EXISTS ix_graph_nodes_properties_gin"))

    # Revert CHECK constraint to the pre-Phase 69 value set. This will
    # fail if any rows with the new node_type values already exist —
    # that is intentional: downgrade must not silently drop data.
    op.execute(
        text("ALTER TABLE graph_nodes DROP CONSTRAINT IF EXISTS graph_nodes_node_type_check")
    )
    op.execute(
        text(
            f"""
            ALTER TABLE graph_nodes
            ADD CONSTRAINT graph_nodes_node_type_check
            CHECK (node_type IN ({_PRE_PHASE69_NODE_TYPES}))
            """
        )
    )
