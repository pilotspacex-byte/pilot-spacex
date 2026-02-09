"""Add source_chat_session_id to notes table.

Revision ID: 030_add_notes_source_chat_session
Revises: 029_add_digest_dismissals
Create Date: 2026-02-07

Links notes to the AI chat session that originated them (Homepage Hub
Compact ChatView "Create note from chat" flow). References the existing
ai_sessions table.

Source: specs/012-homepage-note, plan.md Phase 0.3
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "030_add_notes_source_chat"
down_revision: str = "029_add_digest_dismissals"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add source_chat_session_id FK column to notes."""
    op.add_column(
        "notes",
        sa.Column(
            "source_chat_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ai_sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_notes_source_chat_session_id",
        "notes",
        ["source_chat_session_id"],
    )


def downgrade() -> None:
    """Remove source_chat_session_id from notes."""
    op.drop_index("ix_notes_source_chat_session_id", "notes")
    op.drop_column("notes", "source_chat_session_id")
