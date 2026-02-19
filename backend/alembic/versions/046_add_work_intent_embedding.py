"""Add embedding column to work_intents for pgvector dedup.

C-8: Replace O(N²) Python cosine similarity with pgvector HNSW index query.
Adds a 768-dim vector column and HNSW index to work_intents for fast
approximate nearest-neighbour deduplication.

Revision ID: 046_add_work_intent_embedding
Revises: 045_add_pm_block_insights
Create Date: 2026-02-19
"""

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]

from alembic import op

# revision identifiers, used by Alembic.
revision = "046_add_work_intent_embedding"
down_revision = "045_add_pm_block_insights"
branch_labels = None
depends_on = None

_VECTOR_DIM = 768


def upgrade() -> None:
    """Add embedding column and HNSW index to work_intents."""
    op.add_column(
        "work_intents",
        sa.Column(
            "embedding",
            Vector(_VECTOR_DIM),
            nullable=True,
            comment="768-dim Gemini embedding for pgvector dedup (HNSW)",
        ),
    )
    # HNSW index for cosine distance — matches the existing embedding strategy
    op.execute(
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_work_intents_embedding_hnsw
        ON work_intents
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        WHERE embedding IS NOT NULL AND is_deleted = FALSE
        """
    )


def downgrade() -> None:
    """Remove embedding column and HNSW index from work_intents."""
    op.execute("DROP INDEX IF EXISTS ix_work_intents_embedding_hnsw")
    op.drop_column("work_intents", "embedding")
