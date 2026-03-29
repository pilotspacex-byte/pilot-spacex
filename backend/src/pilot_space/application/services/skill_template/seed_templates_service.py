"""Seed templates service -- P20-07.

Seeds new workspaces with built-in skill templates.
Legacy RoleTemplate source removed in Phase 57 consolidation.
Now a no-op: built-in templates are seeded via migrations or admin tooling.

Source: Phase 20, P20-07
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


class SeedTemplatesService:
    """Seed new workspaces with built-in skill templates.

    Previously copied RoleTemplate rows into skill_templates as built_in.
    Legacy role_templates table removed in Phase 57 consolidation.
    Now a no-op -- workspaces get templates via migrations or marketplace.

    Non-fatal: all exceptions are caught and logged. Workspace creation
    succeeds regardless of seeding outcome.

    Called via ``asyncio.create_task`` in workspace creation -- fire-and-forget.
    """

    def __init__(self, db_session: AsyncSession) -> None:
        """Initialize with a database session.

        Args:
            db_session: Active async database session.
        """
        self._session = db_session

    async def seed_workspace(self, workspace_id: UUID) -> None:
        """No-op: legacy RoleTemplate seeding removed in Phase 57.

        Args:
            workspace_id: UUID of the newly created workspace.
        """
        logger.debug(
            "SeedTemplatesService.seed_workspace is a no-op (legacy RoleTemplate removed), "
            "workspace %s",
            workspace_id,
        )


__all__ = ["SeedTemplatesService"]
