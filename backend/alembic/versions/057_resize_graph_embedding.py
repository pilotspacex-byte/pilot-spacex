"""Resize graph_nodes embedding column from vector(1536) to vector(768).

Revision ID: 057_resize_graph_embedding
Revises: 056_migrate_memory_to_graph
Create Date: 2026-03-03

Motivation: the initial schema used 1536-dim (OpenAI text-embedding-3-large).
The project now uses nomic-embed-text-v2-moe via Ollama (768-dim) as the
local/dev embedding provider.  Changing the column dimension also aligns with
the existing memory_entries.embedding column (768-dim Gemini embeddings).

Steps:
  1. Drop the HNSW index (it is dimension-specific).
  2. Alter the column type to vector(768).
  3. Re-create the HNSW index at the new dimension.

Existing rows with non-NULL embeddings are cleared (set to NULL) so that the
graph embedding worker can re-embed them at the new dimension.  In a fresh dev
environment graph_nodes.embedding is always NULL, so this is a no-op.
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision: str = "057_resize_graph_embedding"
down_revision: str | None = "056_migrate_memory_to_graph"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None

_NEW_DIMS = 768
_OLD_DIMS = 1536


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return  # SQLite test env uses Text fallback — no-op

    # 1. Drop dimension-specific HNSW index
    op.execute(text("DROP INDEX IF EXISTS ix_graph_nodes_embedding"))

    # 2. Null-out any rows with stale 1536-dim embeddings so they get re-embedded
    op.execute(
        text("UPDATE graph_nodes SET embedding = NULL WHERE embedding IS NOT NULL")
    )

    # 3. Change column type from vector(1536) → vector(768)
    op.execute(
        text(
            f"ALTER TABLE graph_nodes "
            f"ALTER COLUMN embedding TYPE vector({_NEW_DIMS}) "
            f"USING embedding::text::vector({_NEW_DIMS})"
        )
    )

    # 4. Re-create HNSW index at new dimension
    op.execute(
        text(
            "CREATE INDEX ix_graph_nodes_embedding "
            "ON graph_nodes USING hnsw (embedding vector_cosine_ops) "
            "WHERE embedding IS NOT NULL"
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(text("DROP INDEX IF EXISTS ix_graph_nodes_embedding"))
    op.execute(
        text("UPDATE graph_nodes SET embedding = NULL WHERE embedding IS NOT NULL")
    )
    op.execute(
        text(
            f"ALTER TABLE graph_nodes "
            f"ALTER COLUMN embedding TYPE vector({_OLD_DIMS}) "
            f"USING embedding::text::vector({_OLD_DIMS})"
        )
    )
    op.execute(
        text(
            "CREATE INDEX ix_graph_nodes_embedding "
            "ON graph_nodes USING hnsw (embedding vector_cosine_ops) "
            "WHERE embedding IS NOT NULL"
        )
    )
