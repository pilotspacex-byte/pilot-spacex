"""Add graph_nodes and graph_edges tables for knowledge graph.

Revision ID: 055_add_knowledge_graph_tables
Revises: 054_add_pilot_api_keys
Create Date: 2026-03-03

Replaces the flat memory_entries model with a typed, connected graph of nodes
and edges. graph_nodes stores semantic entities (issues, notes, concepts, agents)
with optional 1536-dim OpenAI embeddings. graph_edges stores typed relationships
between nodes with a directional weight.

Both tables are RLS-protected using workspace_id. graph_edges denormalises
workspace_id from the source node so RLS policies can filter on one column
without a join, preserving query performance at scale.

HNSW index on embedding uses vector_cosine_ops. Created non-concurrently inside
the migration transaction; rebuild CONCURRENTLY on live databases post-deploy.
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision: str = "055_add_knowledge_graph_tables"
down_revision: str | None = "054_add_pilot_api_keys"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Create graph_nodes and graph_edges tables with RLS and indexes."""

    # ------------------------------------------------------------------
    # graph_nodes
    # ------------------------------------------------------------------
    op.execute(
        text(
            """
        CREATE TABLE graph_nodes (
            id              UUID        NOT NULL DEFAULT gen_random_uuid(),
            workspace_id    UUID        NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            user_id         UUID                 REFERENCES users(id) ON DELETE SET NULL,
            node_type       VARCHAR(50) NOT NULL,
            external_id     UUID,
            label           VARCHAR(500) NOT NULL,
            content         TEXT         NOT NULL DEFAULT '',
            properties      JSONB        NOT NULL DEFAULT '{}',
            embedding       vector(1536),
            created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
            is_deleted      BOOLEAN      NOT NULL DEFAULT false,
            deleted_at      TIMESTAMPTZ,
            CONSTRAINT pk_graph_nodes PRIMARY KEY (id),
            CONSTRAINT graph_nodes_node_type_check CHECK (node_type IN (
                'issue', 'note', 'concept', 'agent', 'user',
                'workspace', 'project', 'cycle', 'label',
                'comment', 'document', 'task', 'sprint', 'epic'
            ))
        )
    """
        )
    )

    # ------------------------------------------------------------------
    # graph_edges
    # ------------------------------------------------------------------
    op.execute(
        text(
            """
        CREATE TABLE graph_edges (
            id              UUID        NOT NULL DEFAULT gen_random_uuid(),
            source_id       UUID        NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
            target_id       UUID        NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
            workspace_id    UUID        NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            edge_type       VARCHAR(50) NOT NULL CHECK (edge_type IN (
                                'relates_to', 'blocks', 'blocked_by', 'duplicates',
                                'parent_of', 'child_of', 'mentions', 'assigned_to',
                                'created_by', 'labeled_with', 'part_of', 'links_to',
                                'summarises', 'referenced_by'
                            )),
            properties      JSONB        NOT NULL DEFAULT '{}',
            weight          FLOAT        NOT NULL DEFAULT 0.5
                                CHECK (weight >= 0.0 AND weight <= 1.0),
            created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
            CONSTRAINT pk_graph_edges PRIMARY KEY (id),
            CONSTRAINT chk_graph_edges_no_self_loop
                CHECK (source_id != target_id),
            CONSTRAINT uq_graph_edges_source_target_type
                UNIQUE (source_id, target_id, edge_type)
        )
    """
        )
    )

    # ------------------------------------------------------------------
    # graph_nodes indexes
    # ------------------------------------------------------------------

    # B-tree: filtered traversals by type within a workspace
    op.execute(
        text(
            "CREATE INDEX ix_graph_nodes_workspace_type ON graph_nodes (workspace_id, node_type)"
        )
    )

    # B-tree: recency queries
    op.execute(
        text(
            "CREATE INDEX ix_graph_nodes_workspace_created "
            "ON graph_nodes (workspace_id, created_at DESC)"
        )
    )

    # B-tree: find node by original entity id
    op.execute(
        text(
            "CREATE INDEX ix_graph_nodes_workspace_external "
            "ON graph_nodes (workspace_id, external_id)"
        )
    )

    # B-tree: user-scoped nodes (partial — only rows where user_id IS NOT NULL)
    op.execute(
        text(
            "CREATE INDEX ix_graph_nodes_user_id ON graph_nodes (user_id) WHERE user_id IS NOT NULL"
        )
    )

    # GIN: property queries
    op.execute(
        text(
            "CREATE INDEX ix_graph_nodes_properties ON graph_nodes USING gin (properties)"
        )
    )

    # HNSW cosine index — created inside the transaction (non-CONCURRENT).
    # CREATE INDEX CONCURRENTLY cannot run inside a transaction block.
    # On live databases, rebuild this index CONCURRENTLY after migration:
    #   DROP INDEX ix_graph_nodes_embedding;
    #   CREATE INDEX CONCURRENTLY ix_graph_nodes_embedding
    #     ON graph_nodes USING hnsw (embedding vector_cosine_ops)
    #     WHERE embedding IS NOT NULL;
    op.execute(
        text(
            "CREATE INDEX ix_graph_nodes_embedding "
            "ON graph_nodes USING hnsw (embedding vector_cosine_ops) "
            "WHERE embedding IS NOT NULL"
        )
    )

    # B-tree: recency pruning queries on updated_at (used by _prioritize_nodes)
    op.execute(
        text(
            "CREATE INDEX ix_graph_nodes_workspace_updated "
            "ON graph_nodes (workspace_id, updated_at DESC)"
        )
    )

    # ------------------------------------------------------------------
    # graph_edges indexes
    # ------------------------------------------------------------------
    op.execute(text("CREATE INDEX ix_graph_edges_source_id ON graph_edges (source_id)"))
    op.execute(text("CREATE INDEX ix_graph_edges_target_id ON graph_edges (target_id)"))
    op.execute(
        text(
            "CREATE INDEX ix_graph_edges_workspace_type ON graph_edges (workspace_id, edge_type)"
        )
    )
    # Composite indexes for BFS edge-type filtering (source/target + edge_type together)
    op.execute(
        text(
            "CREATE INDEX ix_graph_edges_source_type ON graph_edges (source_id, edge_type)"
        )
    )
    op.execute(
        text(
            "CREATE INDEX ix_graph_edges_target_type ON graph_edges (target_id, edge_type)"
        )
    )

    # ------------------------------------------------------------------
    # RLS — graph_nodes  (standard workspace isolation policy)
    # ------------------------------------------------------------------
    op.execute(
        text(
            """
        ALTER TABLE graph_nodes ENABLE ROW LEVEL SECURITY;
        ALTER TABLE graph_nodes FORCE ROW LEVEL SECURITY;
    """
        )
    )

    op.execute(
        text(
            """
        CREATE POLICY "graph_nodes_workspace_isolation"
        ON graph_nodes
        FOR ALL
        TO authenticated
        USING (
            workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                  AND wm.is_deleted = false
            )
        )
    """
        )
    )

    op.execute(
        text(
            """
        CREATE POLICY "graph_nodes_service_role"
        ON graph_nodes
        FOR ALL
        TO service_role
        USING (true)
        WITH CHECK (true)
    """
        )
    )

    # ------------------------------------------------------------------
    # RLS — graph_edges  (workspace_id denormalised on edges for fast checks)
    # ------------------------------------------------------------------
    op.execute(
        text(
            """
        ALTER TABLE graph_edges ENABLE ROW LEVEL SECURITY;
        ALTER TABLE graph_edges FORCE ROW LEVEL SECURITY;
    """
        )
    )

    op.execute(
        text(
            """
        CREATE POLICY "graph_edges_workspace_member"
        ON graph_edges
        FOR ALL
        TO authenticated
        USING (
            workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                  AND wm.is_deleted = false
            )
        )
    """
        )
    )

    op.execute(
        text(
            """
        CREATE POLICY "graph_edges_service_role"
        ON graph_edges
        FOR ALL
        TO service_role
        USING (true)
        WITH CHECK (true)
    """
        )
    )


def downgrade() -> None:
    """Drop graph_edges then graph_nodes (FK ordering)."""
    # Drop edges first — FK references graph_nodes
    op.execute(text("DROP TABLE IF EXISTS graph_edges CASCADE"))
    op.execute(text("DROP TABLE IF EXISTS graph_nodes CASCADE"))
