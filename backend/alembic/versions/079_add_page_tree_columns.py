"""Add page tree columns to notes table, migrate existing data, replace RLS policies.

Revision ID: 079_add_page_tree_columns
Revises: 078_fix_rls_policies
Create Date: 2026-03-12

Changes:
- DDL: Add parent_id (UUID nullable), depth (INTEGER NOT NULL default 0),
  position (INTEGER NOT NULL default 0) to notes table
- DDL: Self-referencing FK fk_notes_parent_id (parent_id -> notes.id, ON DELETE SET NULL)
- DDL: CHECK constraints chk_notes_depth_range and chk_notes_no_self_parent
- DDL: 4 indexes for tree queries and personal page RLS
- DML: Classify existing project notes (project_id IS NOT NULL) with sequential positions
- DML: Classify existing personal notes (project_id IS NULL) with sequential positions
- RLS: Atomically replace notes_workspace_member with notes_project_page_policy +
  notes_personal_page_policy + notes_service_role
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

revision = "079_add_page_tree_columns"
down_revision = "078_fix_rls_policies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add page tree columns, migrate data, and replace RLS policies."""
    # -------------------------------------------------------------------------
    # Step 1: DDL — Add tree columns
    # -------------------------------------------------------------------------
    op.add_column(
        "notes",
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "notes",
        sa.Column(
            "depth",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "notes",
        sa.Column(
            "position",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )

    # -------------------------------------------------------------------------
    # Step 2: DDL — Self-referencing FK
    # Added after add_column to avoid inline FK on self-referencing table
    # -------------------------------------------------------------------------
    op.create_foreign_key(
        "fk_notes_parent_id",
        "notes",
        "notes",
        ["parent_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # -------------------------------------------------------------------------
    # Step 3: DDL — CHECK constraints via op.execute(text(...))
    # Per project convention: use op.execute(text(...)) not op.create_check_constraint()
    # -------------------------------------------------------------------------
    op.execute(
        text(
            "ALTER TABLE notes ADD CONSTRAINT chk_notes_depth_range "
            "CHECK (depth >= 0 AND depth <= 2)"
        )
    )
    op.execute(
        text(
            "ALTER TABLE notes ADD CONSTRAINT chk_notes_no_self_parent CHECK (parent_id != id)"
        )
    )

    # -------------------------------------------------------------------------
    # Step 4: DDL — Indexes for tree queries and personal page RLS
    # -------------------------------------------------------------------------
    # Tree traversal: find all children of a parent
    op.create_index("ix_notes_parent_id", "notes", ["parent_id"])
    # Ordered children fetch (sidebar rendering, ordered by position)
    op.create_index("ix_notes_parent_position", "notes", ["parent_id", "position"])
    # Depth-filtered queries (e.g., roots only: WHERE depth = 0)
    op.create_index("ix_notes_depth", "notes", ["depth"])
    # Personal page RLS: owner_id lookup scoped to workspace
    op.create_index("ix_notes_owner_workspace", "notes", ["owner_id", "workspace_id"])

    # -------------------------------------------------------------------------
    # Step 5: DML — Classify existing project notes
    # Assigns sequential positions (1000, 2000, ...) per project ordered by
    # created_at. All rows are classified regardless of is_deleted status.
    # -------------------------------------------------------------------------
    op.execute(
        text(
            """
        UPDATE notes
        SET
            depth = 0,
            parent_id = NULL,
            position = sub.pos
        FROM (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY project_id
                    ORDER BY created_at
                ) * 1000 AS pos
            FROM notes
            WHERE project_id IS NOT NULL
        ) sub
        WHERE notes.id = sub.id
          AND notes.project_id IS NOT NULL
        """
        )
    )

    # -------------------------------------------------------------------------
    # Step 6: DML — Classify existing personal notes
    # Assigns sequential positions per (owner_id, workspace_id) pair ordered by
    # created_at. All rows classified regardless of is_deleted status.
    # -------------------------------------------------------------------------
    op.execute(
        text(
            """
        UPDATE notes
        SET
            depth = 0,
            parent_id = NULL,
            position = sub.pos
        FROM (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY owner_id, workspace_id
                    ORDER BY created_at
                ) * 1000 AS pos
            FROM notes
            WHERE project_id IS NULL
        ) sub
        WHERE notes.id = sub.id
          AND notes.project_id IS NULL
        """
        )
    )

    # -------------------------------------------------------------------------
    # Step 7: RLS — Atomic policy replacement
    # Drops notes_workspace_member (broad workspace-level access) and replaces
    # with two narrower, semantically correct policies:
    #   - notes_project_page_policy: workspace members access project pages
    #   - notes_personal_page_policy: only the owner accesses personal pages
    # Also creates notes_service_role bypass (no bypass existed before this).
    # -------------------------------------------------------------------------
    op.execute(
        text(
            """
        DROP POLICY IF EXISTS "notes_workspace_member" ON notes;

        CREATE POLICY "notes_project_page_policy"
        ON notes
        FOR ALL
        USING (
            project_id IS NOT NULL
            AND workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                  AND wm.is_deleted = false
            )
        )
        WITH CHECK (
            project_id IS NOT NULL
            AND workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                  AND wm.is_deleted = false
            )
        );

        CREATE POLICY "notes_personal_page_policy"
        ON notes
        FOR ALL
        USING (
            project_id IS NULL
            AND owner_id = current_setting('app.current_user_id', true)::uuid
        )
        WITH CHECK (
            project_id IS NULL
            AND owner_id = current_setting('app.current_user_id', true)::uuid
        );

        DROP POLICY IF EXISTS "notes_service_role" ON notes;

        CREATE POLICY "notes_service_role"
        ON notes
        FOR ALL
        TO service_role
        USING (true)
        WITH CHECK (true);
        """
        )
    )


def downgrade() -> None:
    """Reverse page tree columns, data classification, and RLS policy changes."""
    # -------------------------------------------------------------------------
    # Step 1: RLS — Drop new policies, restore original notes_workspace_member
    # Note: we do NOT restore notes_service_role because it did not exist before
    # this migration (migration 005 never created one for notes).
    # -------------------------------------------------------------------------
    op.execute(
        text(
            """
        DROP POLICY IF EXISTS "notes_project_page_policy" ON notes;
        DROP POLICY IF EXISTS "notes_personal_page_policy" ON notes;
        DROP POLICY IF EXISTS "notes_service_role" ON notes;

        CREATE POLICY "notes_workspace_member"
        ON notes
        FOR ALL
        USING (
            workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                  AND wm.is_deleted = false
            )
        )
        WITH CHECK (
            workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                  AND wm.is_deleted = false
            )
        );
        """
        )
    )

    # -------------------------------------------------------------------------
    # Step 2: DDL — Drop indexes (must precede FK and column drops)
    # -------------------------------------------------------------------------
    op.drop_index("ix_notes_owner_workspace", table_name="notes")
    op.drop_index("ix_notes_depth", table_name="notes")
    op.drop_index("ix_notes_parent_position", table_name="notes")
    op.drop_index("ix_notes_parent_id", table_name="notes")

    # -------------------------------------------------------------------------
    # Step 3: DDL — Drop FK (must precede parent_id column drop)
    # -------------------------------------------------------------------------
    op.drop_constraint("fk_notes_parent_id", "notes", type_="foreignkey")

    # -------------------------------------------------------------------------
    # Step 4: DDL — Drop CHECK constraints
    # -------------------------------------------------------------------------
    op.execute(
        text("ALTER TABLE notes DROP CONSTRAINT IF EXISTS chk_notes_depth_range")
    )
    op.execute(
        text("ALTER TABLE notes DROP CONSTRAINT IF EXISTS chk_notes_no_self_parent")
    )

    # -------------------------------------------------------------------------
    # Step 5: DDL — Drop columns (position and depth before parent_id)
    # -------------------------------------------------------------------------
    op.drop_column("notes", "position")
    op.drop_column("notes", "depth")
    op.drop_column("notes", "parent_id")
