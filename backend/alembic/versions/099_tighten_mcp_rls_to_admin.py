"""Tighten workspace_mcp_servers RLS: restrict SELECT to admin/owner roles only.

Revision ID: 097_tighten_mcp_rls_to_admin
Revises: 096_mcp_settings_redevelopment
Create Date: 2026-03-23

Security fix: The original "workspace_mcp_servers_workspace_isolation" policy
(migration 071) allows ANY workspace member — including GUEST and MEMBER roles —
to SELECT rows. This exposes the presence of MCP server configurations (and any
associated column data returned by the RLS-filtered query, including column flags)
to all workspace members.

This migration replaces the ALL-operations policy with two separate policies:
- SELECT: restricted to workspace members with role IN ('owner', 'admin')
- INSERT/UPDATE/DELETE: restricted to workspace members with role IN ('owner', 'admin')
  (no change in practice — write operations already required admin in application code)

The service_role bypass policy is preserved unchanged.

Downgrade: restores the original permissive FOR ALL policy.
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "099_tighten_mcp_rls_to_admin"
down_revision = "098_mcp_settings_redevelopment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Replace permissive workspace isolation policy with admin/owner-only access."""

    # Drop the original permissive FOR ALL policy
    op.execute(
        text(
            'DROP POLICY IF EXISTS "workspace_mcp_servers_workspace_isolation" '
            "ON workspace_mcp_servers"
        )
    )

    # New SELECT policy: only workspace admins and owners may read MCP server rows.
    # This prevents GUEST and MEMBER roles from enumerating MCP server configurations
    # and any associated metadata (auth type flags, URLs, etc.).
    op.execute(
        text(
            """
            CREATE POLICY "workspace_mcp_servers_admin_select"
            ON workspace_mcp_servers
            FOR SELECT
            USING (
                workspace_id IN (
                    SELECT wm.workspace_id
                    FROM workspace_members wm
                    WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                      AND wm.is_deleted = false
                      AND wm.role IN ('OWNER', 'ADMIN')
                )
            )
            """
        )
    )

    # New INSERT/UPDATE/DELETE policy: restricted to admin/owner roles.
    op.execute(
        text(
            """
            CREATE POLICY "workspace_mcp_servers_admin_write"
            ON workspace_mcp_servers
            FOR ALL
            USING (
                workspace_id IN (
                    SELECT wm.workspace_id
                    FROM workspace_members wm
                    WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                      AND wm.is_deleted = false
                      AND wm.role IN ('OWNER', 'ADMIN')
                )
            )
            WITH CHECK (
                workspace_id IN (
                    SELECT wm.workspace_id
                    FROM workspace_members wm
                    WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                      AND wm.is_deleted = false
                      AND wm.role IN ('OWNER', 'ADMIN')
                )
            )
            """
        )
    )


def downgrade() -> None:
    """Restore the original permissive workspace isolation policy."""

    # Drop the tightened policies
    op.execute(
        text(
            'DROP POLICY IF EXISTS "workspace_mcp_servers_admin_select" '
            "ON workspace_mcp_servers"
        )
    )
    op.execute(
        text(
            'DROP POLICY IF EXISTS "workspace_mcp_servers_admin_write" '
            "ON workspace_mcp_servers"
        )
    )

    # Restore original permissive FOR ALL policy (any workspace member)
    op.execute(
        text(
            """
            CREATE POLICY "workspace_mcp_servers_workspace_isolation"
            ON workspace_mcp_servers
            FOR ALL
            USING (
                workspace_id IN (
                    SELECT wm.workspace_id
                    FROM workspace_members wm
                    WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                    AND wm.is_deleted = false
                )
            )
            """
        )
    )
