"""Replace full unique constraint with partial unique index on workspace_invitations.

Revision ID: 101_fix_invitation_unique_constraint
Revises: 100_add_pgmq_set_vt_wrapper
Create Date: 2026-03-26

The existing UniqueConstraint(workspace_id, email) blocks re-inviting users
whose previous invitation was cancelled or expired. Replace with a partial
unique index that only applies to PENDING invitations.
"""

from __future__ import annotations

from sqlalchemy import text

from alembic import op

revision = "101_fix_invitation_unique_constraint"
down_revision = "100_add_pgmq_set_vt_wrapper"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_workspace_invitations_pending",
        "workspace_invitations",
        type_="unique",
    )
    op.execute(
        text(
            """
            CREATE UNIQUE INDEX uq_workspace_invitations_pending
            ON workspace_invitations (workspace_id, email)
            WHERE status = 'pending' AND is_deleted = false
            """
        )
    )


def downgrade() -> None:
    op.execute(
        text("DROP INDEX IF EXISTS uq_workspace_invitations_pending")
    )
    op.create_unique_constraint(
        "uq_workspace_invitations_pending",
        "workspace_invitations",
        ["workspace_id", "email"],
    )
