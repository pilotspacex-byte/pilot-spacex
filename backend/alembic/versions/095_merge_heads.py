"""merge_heads_095

Revision ID: 22403cf6e40a
Revises: 095_add_transcript_cache_rls, 095_add_workspace_members_rls_index
Create Date: 2026-03-21 17:51:18.267456
"""

from collections.abc import Sequence

# Revision identifiers, used by Alembic.
revision: str = "22403cf6e40a"  # pragma: allowlist secret
down_revision: str | None = ("095_add_transcript_cache_rls", "095_add_workspace_members_rls_index")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply migration."""


def downgrade() -> None:
    """Revert migration."""