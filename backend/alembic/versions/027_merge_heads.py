"""Merge two migration heads into single lineage.

Revision ID: 027_merge_heads
Revises: 4c330de387ff, 07c394515c6c
Create Date: 2026-02-07

Unifies two parallel merge branches:
- 4c330de387ff (022_workspace_onboarding + 024_enhanced_mcp_models)
- 07c394515c6c (022_workspace_onboarding + 026_add_role_based_skills)

Both descend from the same linear chain (017→...→026).
This merge creates a single head for Homepage Hub migrations.
"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "027_merge_heads"
down_revision: tuple[str, str] = ("4c330de387ff", "07c394515c6c")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Merge-only migration — no schema changes."""


def downgrade() -> None:
    """Merge-only migration — no schema changes."""
