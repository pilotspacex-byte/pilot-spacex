"""Add service_role bypass policy for pilot_api_keys.

Revision ID: 054_add_pilot_api_keys
Revises: 053_fix_pilot_api_keys_rls
Create Date: 2026-03-01

Every other table in the codebase has a service_role bypass policy so that
background jobs, admin tooling, and migrations running under the service_role
database role can manage rows without being blocked by RLS.

Migration 052 created the table and migration 053 split the policies, but
both omitted the service_role bypass. This migration adds it.

Without this policy, service_role operations (emergency key revocation,
bulk expiry cleanup, admin audit tooling) silently return no rows or fail
with RLS violations.
"""

from __future__ import annotations

from alembic import op

revision: str = "054_add_pilot_api_keys"
down_revision: str | None = "053_fix_pilot_api_keys_rls"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Add service_role bypass policy for admin/background operations."""
    op.execute(
        """
        CREATE POLICY "pilot_api_keys_service_role"
        ON pilot_api_keys
        FOR ALL
        TO service_role
        USING (true)
        WITH CHECK (true)
    """
    )


def downgrade() -> None:
    """Remove service_role bypass policy."""
    op.execute('DROP POLICY IF EXISTS "pilot_api_keys_service_role" ON pilot_api_keys')
