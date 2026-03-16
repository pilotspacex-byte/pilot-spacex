"""Rename invitation_status enum values from lowercase to UPPERCASE.

Revision ID: 086_fix_invitation_status_enum
Revises: 072_merge_rls_and_mcp
Create Date: 2026-03-16

Migration 022_workspace_invitations created the invitation_status enum with
lowercase values ('pending', 'accepted', 'expired', 'cancelled').  Business
logic and ORM models require UPPERCASE values ('PENDING', 'ACCEPTED',
'EXPIRED', 'CANCELLED') for consistency with workspace_role and other enums.

This migration renames each value in-place using ALTER TYPE … RENAME VALUE
and updates the column server_default so new rows also receive the correct
casing.  No data migration is required — PostgreSQL renames enum labels
without touching stored row data.

Existing RLS policies in 022 and 023 compare against 'OWNER'/'ADMIN' for the
workspace_role enum (which was always UPPERCASE); this migration only affects
invitation_status.
"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "086_fix_invitation_status_enum"
down_revision: str = "085_fix_084_downgrade_safety"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Rename invitation_status enum labels to UPPERCASE and fix server_default."""
    # Rename each enum value in-place — no row rewrites needed.
    op.execute("ALTER TYPE invitation_status RENAME VALUE 'pending'   TO 'PENDING'")
    op.execute("ALTER TYPE invitation_status RENAME VALUE 'accepted'  TO 'ACCEPTED'")
    op.execute("ALTER TYPE invitation_status RENAME VALUE 'expired'   TO 'EXPIRED'")
    op.execute("ALTER TYPE invitation_status RENAME VALUE 'cancelled' TO 'CANCELLED'")

    # Update the column server_default to match the new casing.
    op.execute(
        "ALTER TABLE workspace_invitations "
        "ALTER COLUMN status SET DEFAULT 'PENDING'::invitation_status"
    )


def downgrade() -> None:
    """Rename invitation_status enum labels back to lowercase."""
    # Rename each enum value back to lowercase first, so the label 'pending'
    # exists before the column default references it.
    op.execute("ALTER TYPE invitation_status RENAME VALUE 'PENDING'   TO 'pending'")
    op.execute("ALTER TYPE invitation_status RENAME VALUE 'ACCEPTED'  TO 'accepted'")
    op.execute("ALTER TYPE invitation_status RENAME VALUE 'EXPIRED'   TO 'expired'")
    op.execute("ALTER TYPE invitation_status RENAME VALUE 'CANCELLED' TO 'cancelled'")

    # Restore server_default after the lowercase labels exist.
    op.execute(
        "ALTER TABLE workspace_invitations "
        "ALTER COLUMN status SET DEFAULT 'pending'::invitation_status"
    )
