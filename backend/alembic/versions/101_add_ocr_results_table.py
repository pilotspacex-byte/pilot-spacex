"""Add ocr_results table for persisted OCR extraction output.

Revision ID: 101_add_ocr_results_table
Revises: 100_add_pgmq_set_vt_wrapper
Create Date: 2026-03-23

Creates ocr_results table to store OCR extraction output independently of
chat_attachments TTL. The FK to chat_attachments uses ON DELETE SET NULL so
OCR text survives after attachment rows expire after 24 hours.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "101_add_ocr_results_table"
down_revision: str = "100_add_pgmq_set_vt_wrapper"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ocr_results",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        # ON DELETE SET NULL so OCR text survives after 24h attachment TTL cleanup
        sa.Column(
            "attachment_id",
            UUID(as_uuid=True),
            sa.ForeignKey("chat_attachments.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("extracted_text", sa.Text(), nullable=False),
        sa.Column("tables_json", JSONB(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("language", sa.String(32), nullable=True),
        sa.Column("provider_used", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_ocr_results_attachment_id",
        "ocr_results",
        ["attachment_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_ocr_results_attachment_id", table_name="ocr_results")
    op.drop_table("ocr_results")
