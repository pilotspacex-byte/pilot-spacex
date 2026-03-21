"""Add RLS policies for transcript_cache table.

Revision ID: 095_add_transcript_cache_rls
Revises: 094_add_transcript_cache_table
Create Date: 2026-03-21

Migration 094 created the transcript_cache table but omitted RLS policies.
This migration adds workspace isolation and service_role bypass policies
using the canonical get_workspace_rls_policy_sql() template.
"""

from collections.abc import Sequence

from sqlalchemy import text

from alembic import op
from pilot_space.infrastructure.database.rls import get_workspace_rls_policy_sql

revision: str = "095_add_transcript_cache_rls"
down_revision: str = "094_add_transcript_cache_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add RLS policies for transcript_cache."""
    op.execute(text(get_workspace_rls_policy_sql("transcript_cache")))


def downgrade() -> None:
    """Remove RLS policies from transcript_cache."""
    op.execute(text('DROP POLICY IF EXISTS "transcript_cache_service_role" ON transcript_cache'))
    op.execute(
        text('DROP POLICY IF EXISTS "transcript_cache_workspace_isolation" ON transcript_cache')
    )
    op.execute(text("ALTER TABLE transcript_cache DISABLE ROW LEVEL SECURITY"))
