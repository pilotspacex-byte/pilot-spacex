"""Security hardening: audit log RLS + migration chain documentation.

SEC-02: Tighten ``tool_permission_audit_log`` RLS policy from ``FOR ALL``
to ``FOR INSERT`` only.  Audit logs are append-only — UPDATE and DELETE
must be blocked for non-service roles.

Migration chain notes (SEC-01, SEC-05):
- Migration 107 added four boolean columns to ``workspace_ai_settings``
  for producer opt-out toggles.  Phase 70 decision moved these flags
  into ``workspaces.settings`` (JSONB) instead.
- Migration 108 dropped those orphaned columns.
- Chain: 106 -> 107 -> 108 -> 109 (single head verified).
- The 107 columns are no-ops at runtime — they were added then removed
  within the same release cycle.

Revision ID: 109_security_hardening_rls_and_backfill
Revises: 108_drop_orphaned_producer_toggle_columns
Create Date: 2026-04-09
"""

from __future__ import annotations

from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "109_security_hardening_rls_and_backfill"
down_revision: str | None = "108_drop_orphaned_producer_toggle_columns"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    # SEC-02: Replace FOR ALL with FOR INSERT on audit log.
    # Audit logs must be append-only — no UPDATE or DELETE for non-service roles.
    op.execute(
        text(
            'DROP POLICY IF EXISTS "tool_permission_audit_log_admin_write" '
            "ON tool_permission_audit_log"
        )
    )

    op.execute(
        text("""
        CREATE POLICY "tool_permission_audit_log_admin_insert"
        ON tool_permission_audit_log
        FOR INSERT
        WITH CHECK (
            workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                  AND wm.role IN ('OWNER', 'ADMIN')
                  AND wm.is_deleted = false
            )
        )
        """)
    )


def downgrade() -> None:
    # Restore original FOR ALL policy from migration 105.
    op.execute(
        text(
            'DROP POLICY IF EXISTS "tool_permission_audit_log_admin_insert" '
            "ON tool_permission_audit_log"
        )
    )

    op.execute(
        text("""
        CREATE POLICY "tool_permission_audit_log_admin_write"
        ON tool_permission_audit_log
        FOR ALL
        USING (
            workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                  AND wm.role IN ('OWNER', 'ADMIN')
                  AND wm.is_deleted = false
            )
        )
        WITH CHECK (
            workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                  AND wm.role IN ('OWNER', 'ADMIN')
                  AND wm.is_deleted = false
            )
        )
        """)
    )
