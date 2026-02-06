"""Add workspace_invitations table for member invitation flow.

Revision ID: 022_workspace_invitations
Revises: 021_ai_msg_queue_cols
Create Date: 2026-02-03

Creates table for:
- workspace_invitations: Pending invitations for users who may not yet have an account.

Source: FR-016, FR-031, plan.md Data Model.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "022_workspace_invitations"
down_revision: str | None = "021_ai_msg_queue_cols"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Create workspace_invitations table with indexes and RLS policies."""
    # Create invitation_status enum
    invitation_status = postgresql.ENUM(
        "pending",
        "accepted",
        "expired",
        "cancelled",
        name="invitation_status",
        create_type=False,
    )
    invitation_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "workspace_invitations",
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
            nullable=False,
        ),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        # Invitation-specific columns
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM(
                "owner",
                "admin",
                "member",
                "guest",
                name="workspace_role",
                create_type=False,
            ),
            nullable=False,
            server_default="member",
        ),
        sa.Column("invited_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "pending",
                "accepted",
                "expired",
                "cancelled",
                name="invitation_status",
                create_type=False,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        # Foreign keys
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["invited_by"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "email",
            name="uq_workspace_invitations_pending",
        ),
    )

    # Create indexes
    op.create_index(
        "ix_workspace_invitations_email_status",
        "workspace_invitations",
        ["email", "status"],
    )
    op.create_index(
        "ix_workspace_invitations_workspace_status",
        "workspace_invitations",
        ["workspace_id", "status"],
    )
    op.create_index(
        "ix_workspace_invitations_expires_at",
        "workspace_invitations",
        ["expires_at"],
    )

    # Create RLS policies (FR-031)
    _create_rls_policies()


def _create_rls_policies() -> None:
    """Create RLS policies for workspace_invitations — admin-only access."""
    op.execute("ALTER TABLE workspace_invitations ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE workspace_invitations FORCE ROW LEVEL SECURITY")

    # Admin/owner select policy
    op.execute("""
        CREATE POLICY "workspace_invitation_isolation_select"
        ON workspace_invitations
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

    # Admin/owner modify policy
    op.execute("""
        CREATE POLICY "workspace_invitation_isolation_modify"
        ON workspace_invitations
        FOR ALL
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


def downgrade() -> None:
    """Drop workspace_invitations table and RLS policies."""
    # Drop RLS policies
    op.execute(
        'DROP POLICY IF EXISTS "workspace_invitation_isolation_modify" ON workspace_invitations'
    )
    op.execute(
        'DROP POLICY IF EXISTS "workspace_invitation_isolation_select" ON workspace_invitations'
    )
    op.execute("ALTER TABLE workspace_invitations DISABLE ROW LEVEL SECURITY")

    # Drop indexes
    op.drop_index("ix_workspace_invitations_expires_at", table_name="workspace_invitations")
    op.drop_index("ix_workspace_invitations_workspace_status", table_name="workspace_invitations")
    op.drop_index("ix_workspace_invitations_email_status", table_name="workspace_invitations")

    # Drop table
    op.drop_table("workspace_invitations")

    # Drop enum type
    op.execute("DROP TYPE IF EXISTS invitation_status")
