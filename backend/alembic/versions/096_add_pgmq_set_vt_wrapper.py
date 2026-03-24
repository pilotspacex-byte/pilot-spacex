"""Add public wrapper function for pgmq.set_vt (visibility timeout).

Revision ID: 096_add_pgmq_set_vt_wrapper
Revises: 22403cf6e40a
Create Date: 2026-03-24

The nack(requeue=True) operation needs pgmq.set_vt to reschedule message
visibility for retry.  Migration 061 created wrappers for 8 pgmq functions
but omitted set_vt.  This adds the missing wrapper.

pgmq.set_vt(queue_name, msg_id, vt) updates the visibility timeout of a
message, making it invisible for vt seconds before it becomes available for
re-delivery.  Returns the updated message record.
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "096_add_pgmq_set_vt_wrapper"
down_revision = "22403cf6e40a"  # pragma: allowlist secret
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        text(
            """
CREATE OR REPLACE FUNCTION public.pgmq_set_vt(
    queue_name TEXT,
    msg_id     BIGINT,
    vt         INT
)
RETURNS SETOF pgmq.message_record
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY SELECT * FROM pgmq.set_vt(queue_name, msg_id, vt);
END;
$$;
"""
        )
    )


def downgrade() -> None:
    op.execute(text("DROP FUNCTION IF EXISTS public.pgmq_set_vt(TEXT, BIGINT, INT);"))
