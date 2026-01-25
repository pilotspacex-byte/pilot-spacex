"""Enable pgvector extension.

Revision ID: 001_enable_pgvector
Revises:
Create Date: 2026-01-23

Enables the pgvector extension for vector similarity search.
Required for AI embeddings and semantic search functionality.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_enable_pgvector"
down_revision: str | None = None
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Enable pgvector extension."""
    # Enable pgvector extension (requires superuser or proper grants)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Enable uuid-ossp for UUID generation
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')


def downgrade() -> None:
    """Disable pgvector extension."""
    # Note: Be careful - this will drop all vector columns
    op.execute("DROP EXTENSION IF EXISTS vector")
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')
