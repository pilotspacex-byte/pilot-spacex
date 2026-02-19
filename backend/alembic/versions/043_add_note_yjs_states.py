"""Add note_yjs_states table for Yjs CRDT persistence.

T-116: Persists the binary Yjs document state per note so that:
  - New collaborators can load the full document state on join
  - Offline clients can merge their local Y.Doc on reconnect
  - Server-authoritative state survives all clients disconnecting

Schema:
  note_id       UUID PK → notes.id (CASCADE DELETE)
  state         BYTEA — full Y.Doc binary state (Y.encodeStateAsUpdate output)
  updated_at    timestamptz — last write timestamp

No separate `version` column — Yjs handles convergence internally.
State is overwritten on each persistence call (last-writer-wins at DB level;
CRDT convergence handles conflicts within Yjs).

RLS: workspace isolation via join to notes → workspace_members.

Revision ID: 043_add_note_yjs_states
Revises: 042_add_note_versions
Create Date: 2026-02-19
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers
revision = "043_add_note_yjs_states"
down_revision = "042_add_note_versions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create table
    op.create_table(
        "note_yjs_states",
        sa.Column(
            "note_id",
            UUID(as_uuid=True),
            sa.ForeignKey("notes.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "state",
            sa.LargeBinary(),
            nullable=False,
            comment="Full Y.Doc binary state (Y.encodeStateAsUpdate output)",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # 2. Index on updated_at for cleanup queries
    op.create_index(
        "ix_note_yjs_states_updated_at",
        "note_yjs_states",
        ["updated_at"],
    )

    # 3. RLS — workspace isolation via notes → workspace_members
    op.execute("ALTER TABLE note_yjs_states ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE note_yjs_states FORCE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY "note_yjs_states_workspace_isolation"
        ON note_yjs_states FOR ALL
        USING (
            EXISTS (
                SELECT 1
                FROM notes n
                JOIN workspace_members wm ON wm.workspace_id = n.workspace_id
                WHERE n.id = note_yjs_states.note_id
                AND wm.user_id = current_setting('app.current_user_id', true)::uuid
                AND wm.is_deleted = false
            )
        )
        WITH CHECK (
            EXISTS (
                SELECT 1
                FROM notes n
                JOIN workspace_members wm ON wm.workspace_id = n.workspace_id
                WHERE n.id = note_yjs_states.note_id
                AND wm.user_id = current_setting('app.current_user_id', true)::uuid
                AND wm.is_deleted = false
            )
        )
    """)


def downgrade() -> None:
    op.execute('DROP POLICY IF EXISTS "note_yjs_states_workspace_isolation" ON note_yjs_states')
    op.execute("ALTER TABLE note_yjs_states DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_note_yjs_states_updated_at", table_name="note_yjs_states")
    op.drop_table("note_yjs_states")
