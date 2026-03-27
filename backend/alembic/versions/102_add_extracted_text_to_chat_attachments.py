"""Add extracted_text column to chat_attachments.

Revision ID: 102_add_extracted_text_to_chat_attachments
Revises: 101_add_ocr_results_table
Create Date: 2026-03-23

Adds a nullable TEXT column to cache extracted markdown text from Office
documents (DOCX, XLSX, PPTX). Populated by AttachmentContentService at
content-block build time; avoids re-extracting the same file on repeat calls.

Feature: 020 — Office Document Extraction (Phase 41)
Requirements: OFFICE-04
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "102_add_extracted_text_to_chat_attachments"
down_revision: str = "101_add_ocr_results_table"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    """Add nullable extracted_text column for Office document extraction cache."""
    op.add_column(
        "chat_attachments",
        sa.Column("extracted_text", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Remove extracted_text column."""
    op.drop_column("chat_attachments", "extracted_text")
