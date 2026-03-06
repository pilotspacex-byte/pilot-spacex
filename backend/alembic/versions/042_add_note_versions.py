"""Add note_versions table and auto-version pg_cron function.

Creates the note_versions table for point-in-time note snapshots.
Supports auto/manual/ai_before/ai_after triggers with RLS workspace isolation.
Includes pg_cron function fn_auto_version_active_notes() scheduled every 5 min.

Revision ID: 042_add_note_versions
Revises: 041_add_skill_approval_expiry
Create Date: 2026-02-19

Feature 017: Note Versioning + PM Blocks — Sprint 1 (T-201, T-202)
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision = "042_add_note_versions"
down_revision = "041_add_skill_approval_expiry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add note_versions table with RLS, indexes, and auto-version pg_cron job."""
    # 1. Create note_versions table
    op.create_table(
        "note_versions",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "note_id",
            UUID(as_uuid=True),
            sa.ForeignKey("notes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Trigger enum: who/what initiated this version snapshot
        sa.Column(
            "trigger",
            sa.Enum(
                "auto",
                "manual",
                "ai_before",
                "ai_after",
                name="note_version_trigger_enum",
            ),
            nullable=False,
        ),
        # Full TipTap JSON document at snapshot time (immutable after creation)
        sa.Column("content", sa.JSON(), nullable=False),
        # Human-readable label (e.g. "Before AI edit", "Manual save") — max 100 chars per spec
        sa.Column("label", sa.String(100), nullable=True),
        # Pinned flag: pinned versions exempt from retention cleanup (FR-075)
        sa.Column(
            "pinned",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        # AI-generated change digest (cached; invalidated when linked entities change)
        sa.Column("digest", sa.Text(), nullable=True),
        sa.Column("digest_cached_at", sa.DateTime(timezone=True), nullable=True),
        # Version creator
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Optimistic locking token (C-9): monotonically increasing per note
        sa.Column(
            "version_number",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 2. Indexes for note_versions
    # Primary query pattern: versions for a note, newest first
    op.create_index(
        "ix_note_versions_note_created",
        "note_versions",
        ["note_id", "created_at"],
    )
    op.create_index(
        "ix_note_versions_workspace_id",
        "note_versions",
        ["workspace_id"],
    )
    op.create_index(
        "ix_note_versions_trigger",
        "note_versions",
        ["note_id", "trigger"],
    )
    op.create_index(
        "ix_note_versions_pinned",
        "note_versions",
        ["note_id", "pinned"],
    )
    op.create_index(
        "ix_note_versions_created_by",
        "note_versions",
        ["created_by"],
    )
    # C-9: Prevent duplicate version_number for the same note (race condition guard)
    op.create_unique_constraint(
        "uq_note_versions_note_version_number",
        "note_versions",
        ["note_id", "version_number"],
    )

    # 3. RLS for note_versions (workspace-scoped via workspace_id column)
    op.execute("ALTER TABLE note_versions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE note_versions FORCE ROW LEVEL SECURITY")

    op.execute(
        """
        CREATE POLICY "note_versions_workspace_isolation"
        ON note_versions FOR ALL
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
        )
    """
    )

    # 4. T-202: Auto-version pg_cron function
    # Finds notes with last_edit_at in the past 5 minutes that have no version
    # created in the past 5 minutes → enqueues an auto-snapshot job.
    # Falls back gracefully if notes table has no last_edit_at column (uses updated_at).
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_auto_version_active_notes()
        RETURNS void
        LANGUAGE plpgsql
        SECURITY DEFINER
        AS $$
        DECLARE
            _note RECORD;
        BEGIN
            FOR _note IN
                SELECT n.id AS note_id, n.workspace_id, n.owner_id
                FROM notes n
                WHERE n.is_deleted = false
                  AND n.updated_at > now() - interval '5 minutes'
                  AND NOT EXISTS (
                      SELECT 1
                      FROM note_versions nv
                      WHERE nv.note_id = n.id
                        AND nv.created_at > now() - interval '5 minutes'
                  )
            LOOP
                INSERT INTO note_versions (
                    note_id,
                    workspace_id,
                    trigger,
                    content,
                    label,
                    pinned,
                    created_by,
                    version_number
                )
                SELECT
                    _note.note_id,
                    _note.workspace_id,
                    'auto',
                    n.content,
                    'Auto-save',
                    false,
                    _note.owner_id,
                    COALESCE(
                        (SELECT MAX(nv2.version_number) FROM note_versions nv2
                         WHERE nv2.note_id = _note.note_id),
                        0
                    ) + 1
                FROM notes n
                WHERE n.id = _note.note_id
                  AND n.is_deleted = false;
            END LOOP;
        END;
        $$
    """
    )

    # Schedule pg_cron job every 5 minutes (FR-034).
    # Wrapped in DO block to skip gracefully if pg_cron not installed.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron') THEN
                PERFORM cron.schedule(
                    'auto-version-active-notes',
                    '*/5 * * * *',
                    'SELECT fn_auto_version_active_notes()'
                );
            END IF;
        END;
        $$
    """
    )


def downgrade() -> None:
    """Remove note_versions table and auto-version pg_cron job."""
    # Remove pg_cron job
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron') THEN
                PERFORM cron.unschedule('auto-version-active-notes');
            END IF;
        END;
        $$
    """
    )
    op.execute("DROP FUNCTION IF EXISTS fn_auto_version_active_notes()")

    # Drop note_versions
    op.execute(
        'DROP POLICY IF EXISTS "note_versions_workspace_isolation" ON note_versions'
    )
    op.execute("ALTER TABLE note_versions DISABLE ROW LEVEL SECURITY")
    op.drop_constraint(
        "uq_note_versions_note_version_number", "note_versions", type_="unique"
    )
    op.drop_index("ix_note_versions_created_by", table_name="note_versions")
    op.drop_index("ix_note_versions_pinned", table_name="note_versions")
    op.drop_index("ix_note_versions_trigger", table_name="note_versions")
    op.drop_index("ix_note_versions_workspace_id", table_name="note_versions")
    op.drop_index("ix_note_versions_note_created", table_name="note_versions")
    op.drop_table("note_versions")
    op.execute("DROP TYPE IF EXISTS note_version_trigger_enum")
