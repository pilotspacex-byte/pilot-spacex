"""Add approval_mode column to workspace_mcp_servers.

Revision ID: 093_add_mcp_approval_mode
Revises: 092_add_oauth_refresh_token
Create Date: 2026-03-20

Phase 33 — Remote MCP Approval (MCPA-02):

Adds approval_mode VARCHAR(16) NOT NULL DEFAULT 'auto_approve' with a CHECK
constraint limiting values to ('auto_approve', 'require_approval').

Existing rows receive 'auto_approve' as the server default, preserving the
current auto-execute behaviour.

Downgrade drops the CHECK constraint first, then the column.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "093_add_mcp_approval_mode"
down_revision: str = "092_add_oauth_refresh_token"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add approval_mode column with CHECK constraint."""
    op.add_column(
        "workspace_mcp_servers",
        sa.Column(
            "approval_mode",
            sa.String(16),
            nullable=False,
            server_default="auto_approve",
        ),
    )
    op.create_check_constraint(
        "ck_mcp_server_approval_mode",
        "workspace_mcp_servers",
        "approval_mode IN ('auto_approve', 'require_approval')",
    )


def downgrade() -> None:
    """Drop CHECK constraint then approval_mode column."""
    op.drop_constraint(
        "ck_mcp_server_approval_mode",
        "workspace_mcp_servers",
        type_="check",
    )
    op.drop_column("workspace_mcp_servers", "approval_mode")
