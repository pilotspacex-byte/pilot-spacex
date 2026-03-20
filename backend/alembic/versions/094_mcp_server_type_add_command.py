"""Add 'command' value to mcp_server_type enum.

Revision ID: 094_mcp_server_type_add_command
Revises: 093_mcp_server_unique_display_name
Create Date: 2026-03-20

PostgreSQL ALTER TYPE ... ADD VALUE cannot run inside a transaction block, so
this migration uses op.execute() with the idempotent IF NOT EXISTS guard
(available since PostgreSQL 9.6) to safely add the new enum value.

The legacy 'npx' and 'uvx' values are preserved for backward compatibility with
existing rows.  The application layer maps new user-created servers to 'command'.
Downgrade is intentionally a no-op: PostgreSQL does not support removing enum
values once added, and leaving 'command' in the DB type is harmless — the
application code gating on the enum value prevents its use.
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = "094_mcp_server_type_add_command"
down_revision: str = "093_mcp_server_unique_display_name"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    """Extend mcp_server_type enum with the 'command' value."""
    # ALTER TYPE ... ADD VALUE cannot run inside a transaction block.
    # Alembic issues BEGIN automatically, so we must use COMMIT / BEGIN to
    # step outside the implicit transaction before issuing the DDL.
    op.execute(text("COMMIT"))
    op.execute(
        text("ALTER TYPE mcp_server_type ADD VALUE IF NOT EXISTS 'command'")
    )
    op.execute(text("BEGIN"))


def downgrade() -> None:
    """No-op: PostgreSQL does not support removing enum values.

    The 'command' value remains in the DB type.  If a rollback is truly
    required, drop and recreate the enum manually after migrating all rows
    back to 'npx' or 'uvx'.
    """
