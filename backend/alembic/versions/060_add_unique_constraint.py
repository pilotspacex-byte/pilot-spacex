"""Add UNIQUE partial index on graph_nodes(workspace_id, content_hash).

Revision ID: 060_add_unique_constraint
Revises: 059_add_graph_nodes_content_hash
Create Date: 2026-03-05

Adds a unique partial index on (workspace_id, content_hash) WHERE
content_hash IS NOT NULL, making content-hash dedup race-condition-safe.
Concurrent inserts for the same (workspace, hash) pair will trigger an
IntegrityError that KnowledgeGraphRepository catches and resolves via
rollback + re-query.
"""

from __future__ import annotations

from alembic import op

revision = "060_add_unique_constraint"
down_revision = "059_add_graph_nodes_content_hash"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE UNIQUE INDEX uq_graph_nodes_workspace_content_hash "
        "ON graph_nodes(workspace_id, content_hash) "
        "WHERE content_hash IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_graph_nodes_workspace_content_hash")
