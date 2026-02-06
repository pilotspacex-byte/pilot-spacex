"""Add workspace_onboarding table and is_guided_template to notes.

Revision ID: 022_workspace_onboarding
Revises: 022_multi_context_sessions
Create Date: 2026-02-05

Creates:
- workspace_onboardings: Tracks 3-step onboarding progress per workspace
- is_guided_template column on notes table

T010: Create Alembic migration for both tables + RLS policy.
Source: FR-001, FR-002, FR-003, FR-011, US1
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "022_workspace_onboarding"
down_revision: str | None = "022_multi_context_sessions"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Create workspace_onboardings table and add is_guided_template to notes."""
    # Create workspace_onboardings table
    op.create_table(
        "workspace_onboardings",
        # Base model columns
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        # Workspace reference (1:1)
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Steps JSONB: {"ai_providers": bool, "invite_members": bool, "first_note": bool}
        sa.Column(
            "steps",
            postgresql.JSONB(),
            server_default=sa.text(
                '\'{"ai_providers": false, "invite_members": false, "first_note": false}\'::jsonb'
            ),
            nullable=False,
        ),
        # Reference to guided note (optional)
        sa.Column("guided_note_id", postgresql.UUID(as_uuid=True), nullable=True),
        # Dismissed timestamp
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        # Completed timestamp (when all steps done)
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        # Foreign keys
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["guided_note_id"],
            ["notes.id"],
            ondelete="SET NULL",
        ),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", name="uq_workspace_onboardings_workspace_id"),
    )

    # Create indexes
    op.create_index(
        "ix_workspace_onboardings_workspace_id",
        "workspace_onboardings",
        ["workspace_id"],
        unique=True,
    )
    op.create_index(
        "ix_workspace_onboardings_completed_at",
        "workspace_onboardings",
        ["completed_at"],
    )

    # Create RLS policies for workspace_onboardings
    _create_onboarding_rls_policies()

    # Add is_guided_template column to notes table (T009)
    op.add_column(
        "notes",
        sa.Column(
            "is_guided_template",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )

    # Create index for is_guided_template
    op.create_index(
        "ix_notes_is_guided_template",
        "notes",
        ["is_guided_template"],
    )


def _create_onboarding_rls_policies() -> None:
    """Create RLS policies for workspace_onboardings entity.

    Only workspace owners and admins can access onboarding state.
    Per spec: "Onboarding checklist is visible only to owners and admins"
    """
    op.execute("ALTER TABLE workspace_onboardings ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE workspace_onboardings FORCE ROW LEVEL SECURITY")

    # Only owners/admins can SELECT onboarding state
    op.execute("""
        CREATE POLICY "workspace_onboardings_admin_select"
        ON workspace_onboardings
        FOR SELECT
        USING (
            workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                AND wm.role IN ('owner', 'admin')
                AND wm.is_deleted = false
            )
        )
    """)

    # Only owners/admins can INSERT onboarding state
    op.execute("""
        CREATE POLICY "workspace_onboardings_admin_insert"
        ON workspace_onboardings
        FOR INSERT
        WITH CHECK (
            workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                AND wm.role IN ('owner', 'admin')
                AND wm.is_deleted = false
            )
        )
    """)

    # Only owners/admins can UPDATE onboarding state
    op.execute("""
        CREATE POLICY "workspace_onboardings_admin_update"
        ON workspace_onboardings
        FOR UPDATE
        USING (
            workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                AND wm.role IN ('owner', 'admin')
                AND wm.is_deleted = false
            )
        )
        WITH CHECK (
            workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                AND wm.role IN ('owner', 'admin')
                AND wm.is_deleted = false
            )
        )
    """)

    # Service-role insert: backend sets app.current_user_id before operations.
    # Scoped to workspace admin membership (same as admin_insert above)
    # to prevent unauthorized inserts via direct SQL access.
    op.execute("""
        CREATE POLICY "workspace_onboardings_system_insert"
        ON workspace_onboardings
        FOR INSERT
        WITH CHECK (
            workspace_id IN (
                SELECT wm.workspace_id
                FROM workspace_members wm
                WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
                AND wm.role IN ('owner', 'admin')
                AND wm.is_deleted = false
            )
        )
    """)


def downgrade() -> None:
    """Drop workspace_onboardings table and remove is_guided_template from notes."""
    # Drop is_guided_template index from notes
    op.drop_index("ix_notes_is_guided_template", table_name="notes")

    # Remove is_guided_template column from notes
    op.drop_column("notes", "is_guided_template")

    # Drop RLS policies
    op.execute(
        'DROP POLICY IF EXISTS "workspace_onboardings_system_insert" ON workspace_onboardings'
    )
    op.execute(
        'DROP POLICY IF EXISTS "workspace_onboardings_admin_update" ON workspace_onboardings'
    )
    op.execute(
        'DROP POLICY IF EXISTS "workspace_onboardings_admin_insert" ON workspace_onboardings'
    )
    op.execute(
        'DROP POLICY IF EXISTS "workspace_onboardings_admin_select" ON workspace_onboardings'
    )
    op.execute("ALTER TABLE workspace_onboardings DISABLE ROW LEVEL SECURITY")

    # Drop indexes
    op.drop_index("ix_workspace_onboardings_completed_at", table_name="workspace_onboardings")
    op.drop_index("ix_workspace_onboardings_workspace_id", table_name="workspace_onboardings")

    # Drop table
    op.drop_table("workspace_onboardings")
