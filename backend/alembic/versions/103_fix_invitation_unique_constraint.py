"""Replace full unique constraint with partial unique index on workspace_invitations.

Revision ID: 103_fix_invitation_unique_constraint
Revises: 102_add_extracted_text_to_chat_attachments
Create Date: 2026-03-26

The existing UniqueConstraint(workspace_id, email) blocks re-inviting users
whose previous invitation was cancelled or expired. Replace with a partial
unique index that only applies to PENDING invitations.

This migration is irreversible: once re-invitations create multiple rows per
(workspace_id, email), the old full unique constraint cannot be safely restored.
"""

from __future__ import annotations

from sqlalchemy import text

from alembic import op

revision = "103_fix_invitation_unique_constraint"
down_revision = "102_add_extracted_text_to_chat_attachments"
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
            WHERE status = 'PENDING' AND is_deleted = false
            """
        )
    )


def downgrade() -> None:
    msg = (
        "Migration 103 is irreversible: re-invitations may have created "
        "duplicate (workspace_id, email) rows that violate the old full "
        "unique constraint."
    )
    raise NotImplementedError(msg)
