"""Action button service for workspace skill action button CRUD.

Extracts business logic from workspace_action_buttons router into
a proper service layer following Clean Architecture.

Source: Phase 17, SKBTN-01..04
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.domain.exceptions import NotFoundError
from pilot_space.infrastructure.database.models.skill_action_button import (
    SkillActionButton,
)
from pilot_space.infrastructure.database.repositories.skill_action_button_repository import (
    SkillActionButtonRepository,
)
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)


class ActionButtonService:
    """Service for managing workspace action button configurations.

    Handles CRUD, reorder, and soft-delete operations on skill action buttons.
    All operations are workspace-scoped.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = SkillActionButtonRepository(session)

    async def list_active(self, workspace_id: UUID) -> Sequence[SkillActionButton]:
        """List active action buttons for a workspace.

        Args:
            workspace_id: Workspace UUID.

        Returns:
            Active buttons ordered by sort_order.
        """
        return await self._repo.get_active_by_workspace(workspace_id)

    async def list_all(self, workspace_id: UUID) -> Sequence[SkillActionButton]:
        """List all non-deleted action buttons for a workspace (admin view).

        Args:
            workspace_id: Workspace UUID.

        Returns:
            All non-deleted buttons ordered by sort_order.
        """
        return await self._repo.get_all_by_workspace(workspace_id)

    async def create(
        self,
        workspace_id: UUID,
        *,
        name: str,
        icon: str | None = None,
        binding_type: str,
        binding_id: UUID | None = None,
        binding_metadata: dict[str, Any] | None = None,
    ) -> SkillActionButton:
        """Create a new action button.

        Args:
            workspace_id: Workspace UUID.
            name: Button display name.
            icon: Optional icon identifier.
            binding_type: Type of binding (e.g. skill, plugin).
            binding_id: ID of the bound entity.
            binding_metadata: Optional metadata dict.

        Returns:
            Created button entity.
        """
        button = SkillActionButton(
            workspace_id=workspace_id,
            name=name,
            icon=icon,
            binding_type=binding_type,
            binding_id=binding_id,
            binding_metadata=binding_metadata,
        )
        created = await self._repo.create(button)
        logger.info("[ActionButtons] Created %s in workspace %s", name, workspace_id)
        return created

    async def update(
        self,
        workspace_id: UUID,
        button_id: UUID,
        update_data: dict[str, Any],
    ) -> SkillActionButton:
        """Update an existing action button.

        Args:
            workspace_id: Workspace UUID.
            button_id: Button UUID.
            update_data: Dict of fields to update (exclude_unset from schema).

        Returns:
            Updated button entity.

        Raises:
            NotFoundError: If button not found.
        """
        button = await self._repo.get_by_workspace_and_id(workspace_id, button_id)
        if button is None:
            raise NotFoundError("Button not found")

        for field_name, value in update_data.items():
            setattr(button, field_name, value)

        updated = await self._repo.update(button)
        logger.info("[ActionButtons] Updated %s", button_id)
        return updated

    async def reorder(
        self,
        workspace_id: UUID,
        button_ids: list[UUID],
    ) -> None:
        """Reorder action buttons by providing ordered list of IDs.

        Args:
            workspace_id: Workspace UUID.
            button_ids: Ordered list of button UUIDs.
        """
        all_buttons = await self._repo.get_all_by_workspace(workspace_id)
        buttons_by_id = {b.id: b for b in all_buttons}
        for idx, bid in enumerate(button_ids):
            button = buttons_by_id.get(bid)
            if button is not None:
                button.sort_order = idx * 10
        await self._session.flush()

        logger.info(
            "[ActionButtons] Reordered %d buttons in workspace %s",
            len(button_ids),
            workspace_id,
        )

    async def delete(self, workspace_id: UUID, button_id: UUID) -> None:
        """Soft-delete an action button.

        Args:
            workspace_id: Workspace UUID.
            button_id: Button UUID.

        Raises:
            NotFoundError: If button not found.
        """
        button = await self._repo.get_by_workspace_and_id(workspace_id, button_id)
        if button is None:
            raise NotFoundError("Button not found")

        await self._repo.soft_delete(button)
        logger.info(
            "[ActionButtons] Deleted %s from workspace %s",
            button_id,
            workspace_id,
        )


__all__ = ["ActionButtonService"]
