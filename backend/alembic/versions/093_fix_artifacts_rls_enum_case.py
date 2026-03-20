"""No-op: migration 092 already uses correct UPPERCASE enum values.

This migration was originally created under the false assumption that
workspace_role stores lowercase values. In fact, the enum was created with
UPPERCASE values ('OWNER', 'ADMIN', 'MEMBER', 'GUEST') in migration 002,
and migration 066 normalizes existing data to UPPERCASE. Migration 092
already creates the policy with correct UPPERCASE values.

The original lowercase policy caused: ERROR invalid input value for enum
workspace_role: "owner" — breaking the Upgrade Simulation CI workflow.

Revision ID: 093_fix_artifacts_rls_enum_case
Revises: 092_add_artifacts_rls_policies
Create Date: 2026-03-20
"""

from collections.abc import Sequence

from alembic import op  # noqa: F401

revision: str = "093_fix_artifacts_rls_enum_case"
down_revision: str = "092_add_artifacts_rls_policies"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # No-op: migration 092 already has correct UPPERCASE enum values.
    pass


def downgrade() -> None:
    # No-op: nothing to revert.
    pass
