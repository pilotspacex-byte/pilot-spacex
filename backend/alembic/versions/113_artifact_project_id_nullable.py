"""Make artifacts.project_id nullable to support AI-generated artifacts.

Phase 87.1 Plan 01 — foundation for AI file generation. AI-generated artifacts
may have no project context, so the column must accept NULL.

Schema changes:

  * Drop existing FK ``artifacts_project_id_fkey`` (was ON DELETE CASCADE).
  * Alter ``artifacts.project_id`` to ``NULL`` allowed.
  * Recreate FK with ``ON DELETE SET NULL`` so deleting a project orphans the
    artifact rather than dropping it (AI outputs survive project deletion).

The composite index ``ix_artifacts_workspace_project`` is left in place — PG
btree indexes happily accept NULL values, and queries scoping by both columns
continue to use it.

RLS: workspace_isolation policy (migration 092) does NOT reference project_id,
so cross-workspace isolation continues to hold for rows with NULL project_id.
A regression integration test asserts this in Plan 87.1-01 Task 3.

Downgrade caveat: reverse migration sets project_id NOT NULL and recreates
the FK with ON DELETE CASCADE. Operators MUST first delete (or back-fill)
any rows where ``project_id IS NULL`` (the AI-generated artifacts), otherwise
the ALTER COLUMN ... SET NOT NULL will fail.

Revision ID: 113_artifact_project_id_nullable
Revises: 112_topic_nested_hierarchy
Create Date: 2026-04-28
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "113_artifact_project_id_nullable"
down_revision: str | None = "112_topic_nested_hierarchy"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    # 1. Drop the existing FK (default SQLAlchemy name from migration 091).
    op.drop_constraint(
        "artifacts_project_id_fkey",
        "artifacts",
        type_="foreignkey",
    )

    # 2. Allow NULL on the column.
    op.alter_column(
        "artifacts",
        "project_id",
        existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
        nullable=True,
    )

    # 3. Recreate the FK with ON DELETE SET NULL (was CASCADE).
    op.create_foreign_key(
        "artifacts_project_id_fkey",
        "artifacts",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    # IMPORTANT: callers MUST delete rows where project_id IS NULL before
    # running this downgrade, otherwise SET NOT NULL will fail.
    op.drop_constraint(
        "artifacts_project_id_fkey",
        "artifacts",
        type_="foreignkey",
    )

    op.alter_column(
        "artifacts",
        "project_id",
        existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
        nullable=False,
    )

    op.create_foreign_key(
        "artifacts_project_id_fkey",
        "artifacts",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
    )
