"""Add base_url and model_name columns to workspace_api_keys table.

Revision ID: 082_add_base_url_model_name_to_api_keys
Revises: 081_add_user_ai_settings
Create Date: 2026-03-14

Changes:
- DDL: Add base_url (String(2048), nullable) to workspace_api_keys
  Stores custom provider base URL (e.g. Azure OpenAI endpoint).
- DDL: Add model_name (String(200), nullable) to workspace_api_keys
  Stores default model name override per provider.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "082_add_base_url_model_name_to_api_keys"
down_revision: str = "081_add_user_ai_settings"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column("workspace_api_keys", sa.Column("base_url", sa.String(2048), nullable=True))
    op.add_column("workspace_api_keys", sa.Column("model_name", sa.String(200), nullable=True))


def downgrade() -> None:
    op.drop_column("workspace_api_keys", "model_name")
    op.drop_column("workspace_api_keys", "base_url")
