"""Normalize workspace_members.role to UPPERCASE for RLS policy consistency.

Revision ID: 066_fix_rls_enum_case
Revises: 065_add_audit_log_table
Create Date: 2026-03-08

Phase 3 — Multi-Tenant Isolation prerequisite:

- TENANT-01: RLS policies on workspace_members compare role against UPPERCASE strings
  ('OWNER', 'ADMIN', 'MEMBER', 'GUEST') but historical data may have been inserted
  with lowercase values, causing RLS to treat members as having no role and making
  their rows invisible under RLS enforcement.
- This migration normalizes all existing role values to UPPERCASE so RLS policies
  evaluate correctly and isolation tests produce accurate results.

Known bug documented in STATE.md:
  RLS enum case mismatch (UPPERCASE in policies vs lowercase in some migrations)
  must be resolved before Phase 3 isolation verification.

Downgrade note:
  Enum case normalization is non-reversible without tracking original values.
  RLS policies always expected UPPERCASE, so reverting to lowercase would break
  isolation. downgrade() is intentionally a no-op.
"""

from __future__ import annotations

from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic
revision: str = "066_fix_rls_enum_case"
down_revision: str = "065_add_audit_log_table"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Normalize workspace_members.role values to UPPERCASE.

    RLS SELECT/INSERT/UPDATE policies use UPPERCASE role values:
      (role = 'OWNER' OR role = 'ADMIN')
    Any row with lowercase role (e.g. 'owner', 'admin') is invisible under
    RLS enforcement, causing false-pass results in cross-workspace isolation tests.

    After this migration:
      SELECT DISTINCT role FROM workspace_members;
      -- Returns: OWNER, ADMIN, MEMBER, GUEST only (no lowercase variants)
    """
    op.execute(
        text("""
            UPDATE workspace_members
            SET role = UPPER(role::text)::workspace_role
            WHERE role::text != UPPER(role::text);
        """)
    )


def downgrade() -> None:
    """No-op: enum case normalization is not reversible.

    RLS policies always required UPPERCASE values. Reverting to lowercase
    would break multi-tenant isolation. Data stays UPPERCASE.
    """
