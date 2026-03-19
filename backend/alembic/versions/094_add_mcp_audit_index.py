"""Add partial index for MCP tool audit log queries.

Revision ID: 094_add_mcp_audit_index
Revises: 093_add_mcp_approval_mode
Create Date: 2026-03-20

Phase 34 — MCPOB-01:
Adds a partial index on audit_log(workspace_id, created_at)
WHERE action = 'ai.mcp_tool_call' to accelerate dashboard queries
without full-table JSONB extraction scans.

The index name ix_audit_log_mcp_tool_calls matches the name checked
in success criteria.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "094_add_mcp_audit_index"
down_revision: str = "093_add_mcp_approval_mode"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add partial index on audit_log for MCP tool call rows."""
    op.create_index(
        "ix_audit_log_mcp_tool_calls",
        "audit_log",
        ["workspace_id", "created_at"],
        postgresql_where=sa.text("action = 'ai.mcp_tool_call'"),
    )


def downgrade() -> None:
    """Drop the MCP tool audit log partial index."""
    op.drop_index("ix_audit_log_mcp_tool_calls", table_name="audit_log")
