"""merge migration heads

Revision ID: 4c330de387ff
Revises: 022_workspace_onboarding, 024_enhanced_mcp_models
Create Date: 2026-02-07 12:58:43.071534
"""

from collections.abc import Sequence

# Revision identifiers, used by Alembic.
revision: str = "4c330de387ff"
down_revision: str | None = ("022_workspace_onboarding", "024_enhanced_mcp_models")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply migration."""


def downgrade() -> None:
    """Revert migration."""
