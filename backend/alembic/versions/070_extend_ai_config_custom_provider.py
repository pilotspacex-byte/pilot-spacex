"""Extend ai_configurations for custom/kimi/glm provider support.

Revision ID: 070_extend_ai_config_custom_provider
Revises: 069_add_operation_type_to_costs
Create Date: 2026-03-09

Phase 13 — AI Provider Registry + Model Selection (AIPR-01, AIPR-02):

1. Adds 'kimi', 'glm', 'custom' values to the llm_provider PostgreSQL enum
   (IF NOT EXISTS guards make this idempotent).
2. Adds base_url VARCHAR(512): required for custom OpenAI-compatible providers,
   optional for kimi/glm (default URLs used when null).
3. Adds display_name VARCHAR(128): human-readable label for custom providers.

Downgrade note: PostgreSQL enum values cannot be removed after they are added.
The kimi/glm/custom enum values remain in the DB type after downgrade.
Only the base_url and display_name columns are dropped on downgrade.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision = "070_extend_ai_config_custom_provider"
down_revision = "069_add_operation_type_to_costs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add kimi/glm/custom enum values and base_url/display_name columns."""
    # Add new enum values to the existing llm_provider type.
    # PostgreSQL does not support removing enum values, so IF NOT EXISTS guards
    # make this migration idempotent.
    op.execute(text("ALTER TYPE llm_provider ADD VALUE IF NOT EXISTS 'kimi'"))
    op.execute(text("ALTER TYPE llm_provider ADD VALUE IF NOT EXISTS 'glm'"))
    op.execute(text("ALTER TYPE llm_provider ADD VALUE IF NOT EXISTS 'custom'"))

    # Add base_url column — stores the OpenAI-compatible API endpoint.
    # Required when provider='custom'; optional for kimi/glm (service defaults used).
    op.add_column(
        "ai_configurations",
        sa.Column("base_url", sa.String(512), nullable=True),
    )

    # Add display_name column — human-readable label shown in UI for custom providers.
    op.add_column(
        "ai_configurations",
        sa.Column("display_name", sa.String(128), nullable=True),
    )


def downgrade() -> None:
    """Remove base_url and display_name columns.

    NOTE: PostgreSQL enum values 'kimi', 'glm', 'custom' CANNOT be removed
    after being added to an enum type. They remain in llm_provider after
    this downgrade. This is a known PostgreSQL limitation.
    """
    op.drop_column("ai_configurations", "display_name")
    op.drop_column("ai_configurations", "base_url")
