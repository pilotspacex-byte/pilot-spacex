"""Multi-context session architecture.

Revision ID: 022_multi_context_sessions
Revises: 023_fix_invitation_rls_enum_case
Create Date: 2026-02-05

Changes:
- Drop unique constraint on (user_id, agent_name, context_id) to allow multiple sessions per context
- Add title column for auto-generated session titles
- Add index on title for search
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "022_multi_context_sessions"
down_revision: str | None = "023_fix_invitation_rls_enum_case"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply multi-context session changes."""
    # 1. Drop unique constraint (allows multiple sessions per context)
    op.drop_constraint("uq_ai_sessions_user_agent_context", "ai_sessions", type_="unique")

    # 2. Add title column for auto-generated session titles
    op.add_column(
        "ai_sessions",
        sa.Column(
            "title",
            sa.String(255),
            nullable=True,
            comment="Auto-generated title from first user message",
        ),
    )

    # 3. Add index for title search
    op.create_index("ix_ai_sessions_title", "ai_sessions", ["title"])


def downgrade() -> None:
    """Revert multi-context session changes."""
    # Drop title index
    op.drop_index("ix_ai_sessions_title", "ai_sessions")

    # Drop title column
    op.drop_column("ai_sessions", "title")

    # Recreate unique constraint
    op.create_unique_constraint(
        "uq_ai_sessions_user_agent_context",
        "ai_sessions",
        ["user_id", "agent_name", "context_id"],
    )
