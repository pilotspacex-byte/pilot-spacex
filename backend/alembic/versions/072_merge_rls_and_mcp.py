"""Merge task RLS policies branch with MCP servers branch.

Revision ID: 072_merge_rls_and_mcp
Revises: 062_split_task_rls_policies, 071_add_workspace_mcp_servers
Create Date: 2026-03-12

Merge commit that resolves the two heads that both descend from
061_add_pgmq_rpc_wrappers:

  Branch A: 062_split_task_rls_policies
      Replaces the blanket tasks RLS policy with per-operation policies
      (select / insert / update / delete / service_role).

  Branch B: 062_add_notifications_table → … → 071_add_workspace_mcp_servers
      Adds workspace_mcp_servers table and supporting enum.

No schema changes are made in this migration; all DDL lives in the two
parent revisions above.
"""

from __future__ import annotations

# revision identifiers, used by Alembic.
revision: str = "072_merge_rls_and_mcp"
down_revision: tuple[str, str] = (
    "062_split_task_rls_policies",
    "071_add_workspace_mcp_servers",
)
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """No-op — all schema changes are in the parent revisions."""


def downgrade() -> None:
    """No-op — downgrade each parent revision individually."""
