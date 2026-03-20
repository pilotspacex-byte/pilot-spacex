"""Add partial unique index on workspace_mcp_servers(workspace_id, display_name).

Revision ID: 093_mcp_server_unique_display_name
Revises: 092_add_headers_json_column
Create Date: 2026-03-20

Enforces that no two active (non-deleted) MCP servers within the same workspace
share a display_name.  A partial index is used instead of a table-level UNIQUE
constraint so that soft-deleted rows (is_deleted = true) are excluded — allowing
a name to be re-registered after the previous server is deleted.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "093_mcp_server_unique_display_name"
down_revision: str = "092_add_headers_json_column"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    """Create partial unique index on (workspace_id, display_name) for active rows."""

    # Partial unique index — only enforced when is_deleted = false so that
    # soft-deleted rows do not block re-registration of the same name.
    op.execute(
        text(
            """
            CREATE UNIQUE INDEX uq_mcp_servers_workspace_display_name_active
            ON workspace_mcp_servers (workspace_id, display_name)
            WHERE is_deleted = false
            """
        )
    )


def downgrade() -> None:
    """Drop the partial unique index."""
    op.execute(
        text(
            "DROP INDEX IF EXISTS uq_mcp_servers_workspace_display_name_active"
        )
    )
