"""Add partial index on workspace_members for RLS subquery performance.

Every RLS policy executes:
    SELECT workspace_id FROM workspace_members
    WHERE user_id = current_setting('app.current_user_id')::uuid
    AND is_deleted = false

This runs per-row on every query against RLS-protected tables. Without
a partial index on user_id (filtered to is_deleted = false), each check
triggers a full table scan on workspace_members.

Revision ID: 095_add_workspace_members_rls_index
Revises: 094_add_artifacts_rls_with_check
Create Date: 2026-03-20
"""

from collections.abc import Sequence

from alembic import op

revision: str = "095_add_workspace_members_rls_index"
down_revision: str = "094_add_artifacts_rls_with_check"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Composite partial index for RLS subquery: covers (user_id, is_deleted)
    # with predicate WHERE is_deleted = false. Also INCLUDE workspace_id
    # so the RLS subquery can be satisfied from the index alone (index-only scan).
    op.create_index(
        "ix_workspace_members_user_active_ws",
        "workspace_members",
        ["user_id"],
        postgresql_where="is_deleted = false",
        postgresql_include=["workspace_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_workspace_members_user_active_ws",
        table_name="workspace_members",
    )
