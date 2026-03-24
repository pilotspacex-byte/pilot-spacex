"""Add note_chunk and branch to graph_nodes node_type check constraint.

The KgPopulateHandler creates NOTE_CHUNK nodes when chunking long notes
and issue descriptions, and BRANCH nodes for GitHub integration. Both
types were defined in the domain model (graph_node.py NodeType) but
missing from the database check constraint, causing IntegrityError on
insert.

Revision ID: 096_add_note_chunk_node_type
Revises: 22403cf6e40a
Create Date: 2026-03-22
"""

from sqlalchemy import text

from alembic import op

revision = "096_add_note_chunk_node_type"
down_revision = "22403cf6e40a"  # pragma: allowlist secret
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        text("""
        ALTER TABLE graph_nodes
        DROP CONSTRAINT IF EXISTS graph_nodes_node_type_check
    """)
    )
    op.execute(
        text("""
        ALTER TABLE graph_nodes
        ADD CONSTRAINT graph_nodes_node_type_check
        CHECK (node_type IN (
            'issue', 'note', 'note_chunk', 'concept', 'agent', 'user',
            'workspace', 'project', 'cycle', 'label',
            'comment', 'document', 'task', 'sprint', 'epic',
            'work_intent', 'skill_outcome', 'learned_pattern',
            'constitution_rule', 'pull_request', 'branch', 'code_reference',
            'decision', 'conversation_summary', 'user_preference'
        ))
    """)
    )


def downgrade() -> None:
    op.execute(
        text("""
        ALTER TABLE graph_nodes
        DROP CONSTRAINT IF EXISTS graph_nodes_node_type_check
    """)
    )
    op.execute(
        text("""
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
    """)
    )
