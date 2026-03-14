"""Add service_type column to workspace_api_keys.

Revision ID: 084_add_service_type_to_api_keys
Revises: 083_fix_personal_page_rls_workspace_scope
Create Date: 2026-03-14

Adds service_type column ('embedding' | 'llm') to support service-based
provider configuration. Updates unique constraint to include service_type
so a provider like Ollama can serve both embedding and LLM with separate configs.

Backfills existing rows: google -> embedding, all others -> llm.
"""

import sqlalchemy as sa
from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "084_add_service_type_to_api_keys"
down_revision: str | None = "083_fix_personal_page_rls_workspace_scope"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Add service_type column and update unique constraint."""
    # Add service_type column with default 'llm'
    op.add_column(
        "workspace_api_keys",
        sa.Column(
            "service_type",
            sa.String(20),
            nullable=False,
            server_default="llm",
        ),
    )

    # Backfill: google provider -> embedding
    op.execute(
        text("UPDATE workspace_api_keys SET service_type = 'embedding' WHERE provider = 'google'")
    )

    # Drop old unique constraint
    op.drop_constraint(
        "uq_workspace_api_keys_workspace_provider",
        "workspace_api_keys",
        type_="unique",
    )

    # Create new unique constraint including service_type
    op.create_unique_constraint(
        "uq_workspace_api_keys_workspace_provider_service",
        "workspace_api_keys",
        ["workspace_id", "provider", "service_type"],
    )

    # Add index on service_type for filtering
    op.create_index(
        "ix_workspace_api_keys_service_type",
        "workspace_api_keys",
        ["service_type"],
    )

    # Make encrypted_key nullable (Ollama doesn't require API key)
    op.alter_column(
        "workspace_api_keys",
        "encrypted_key",
        existing_type=sa.Text(),
        nullable=True,
    )


def downgrade() -> None:
    """Remove service_type column and restore old constraint."""
    # Drop new index
    op.drop_index("ix_workspace_api_keys_service_type", table_name="workspace_api_keys")

    # Drop new unique constraint
    op.drop_constraint(
        "uq_workspace_api_keys_workspace_provider_service",
        "workspace_api_keys",
        type_="unique",
    )

    # Restore old unique constraint
    op.create_unique_constraint(
        "uq_workspace_api_keys_workspace_provider",
        "workspace_api_keys",
        ["workspace_id", "provider"],
    )

    # Restore encrypted_key NOT NULL
    op.alter_column(
        "workspace_api_keys",
        "encrypted_key",
        existing_type=sa.Text(),
        nullable=False,
    )

    # Drop column
    op.drop_column("workspace_api_keys", "service_type")
