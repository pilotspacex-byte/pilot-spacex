"""AIConfiguration repository for database operations.

Provides data access methods for AI configurations with workspace scoping.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import and_, select

from pilot_space.infrastructure.database.models.ai_configuration import (
    AIConfiguration,
    LLMProvider,
)
from pilot_space.infrastructure.database.repositories.base import BaseRepository

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class AIConfigurationRepository(BaseRepository[AIConfiguration]):
    """Repository for AIConfiguration entities.

    Extends BaseRepository with workspace-scoped queries and provider lookup.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with session.

        Args:
            session: Async database session.
        """
        super().__init__(session, AIConfiguration)

    async def get_by_workspace(
        self,
        workspace_id: UUID,
        *,
        include_inactive: bool = False,
    ) -> Sequence[AIConfiguration]:
        """Get all AI configurations for a workspace.

        Args:
            workspace_id: The workspace UUID.
            include_inactive: Whether to include inactive configurations.

        Returns:
            List of AI configurations for the workspace.
        """
        conditions = [
            AIConfiguration.workspace_id == workspace_id,
            AIConfiguration.is_deleted == False,  # noqa: E712
        ]
        if not include_inactive:
            conditions.append(AIConfiguration.is_active == True)  # noqa: E712

        query = select(AIConfiguration).where(and_(*conditions)).order_by(AIConfiguration.provider)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_workspace_and_id(
        self,
        workspace_id: UUID,
        config_id: UUID,
    ) -> AIConfiguration | None:
        """Get a specific AI configuration by workspace and ID.

        Args:
            workspace_id: The workspace UUID.
            config_id: The configuration UUID.

        Returns:
            The AI configuration if found, None otherwise.
        """
        query = select(AIConfiguration).where(
            and_(
                AIConfiguration.id == config_id,
                AIConfiguration.workspace_id == workspace_id,
                AIConfiguration.is_deleted == False,  # noqa: E712
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_workspace_and_provider(
        self,
        workspace_id: UUID,
        provider: LLMProvider,
    ) -> AIConfiguration | None:
        """Get AI configuration for a specific provider in a workspace.

        Args:
            workspace_id: The workspace UUID.
            provider: The LLM provider.

        Returns:
            The AI configuration if found, None otherwise.
        """
        query = select(AIConfiguration).where(
            and_(
                AIConfiguration.workspace_id == workspace_id,
                AIConfiguration.provider == provider,
                AIConfiguration.is_deleted == False,  # noqa: E712
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_active_for_provider(
        self,
        workspace_id: UUID,
        provider: LLMProvider,
    ) -> AIConfiguration | None:
        """Get active AI configuration for a specific provider.

        Args:
            workspace_id: The workspace UUID.
            provider: The LLM provider.

        Returns:
            Active AI configuration if found, None otherwise.
        """
        query = select(AIConfiguration).where(
            and_(
                AIConfiguration.workspace_id == workspace_id,
                AIConfiguration.provider == provider,
                AIConfiguration.is_active == True,  # noqa: E712
                AIConfiguration.is_deleted == False,  # noqa: E712
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def count_by_workspace(
        self,
        workspace_id: UUID,
        *,
        include_inactive: bool = True,
    ) -> int:
        """Count AI configurations for a workspace.

        Args:
            workspace_id: The workspace UUID.
            include_inactive: Whether to count inactive configurations.

        Returns:
            Count of AI configurations.
        """
        filters: dict[str, object] = {"workspace_id": workspace_id}
        if not include_inactive:
            filters["is_active"] = True
        return await self.count(filters=filters)


__all__ = ["AIConfigurationRepository"]
