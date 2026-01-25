"""Integration repository with workspace-scoped queries.

T175: Create IntegrationRepository for OAuth token management.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import and_, select
from sqlalchemy.orm import joinedload

from pilot_space.infrastructure.database.models import (
    Integration,
    IntegrationProvider,
)
from pilot_space.infrastructure.database.repositories.base import (
    BaseRepository,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class IntegrationRepository(BaseRepository[Integration]):
    """Repository for Integration entities.

    Provides:
    - Workspace-scoped CRUD operations
    - Provider-specific queries
    - Active integration retrieval
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: Async database session.
        """
        super().__init__(session, Integration)

    async def get_by_workspace(
        self,
        workspace_id: UUID,
        *,
        include_inactive: bool = False,
        include_deleted: bool = False,
    ) -> Sequence[Integration]:
        """Get all integrations for a workspace.

        Args:
            workspace_id: Workspace UUID.
            include_inactive: Whether to include inactive integrations.
            include_deleted: Whether to include soft-deleted integrations.

        Returns:
            List of integrations for the workspace.
        """
        query = select(Integration).where(Integration.workspace_id == workspace_id)

        if not include_deleted:
            query = query.where(Integration.is_deleted == False)  # noqa: E712
        if not include_inactive:
            query = query.where(Integration.is_active == True)  # noqa: E712

        query = query.order_by(Integration.provider, Integration.created_at)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_provider(
        self,
        workspace_id: UUID,
        provider: IntegrationProvider,
        *,
        include_deleted: bool = False,
    ) -> Integration | None:
        """Get integration by provider for a workspace.

        Args:
            workspace_id: Workspace UUID.
            provider: Integration provider (github/slack).
            include_deleted: Whether to include soft-deleted integrations.

        Returns:
            Integration if found, None otherwise.
        """
        query = select(Integration).where(
            and_(
                Integration.workspace_id == workspace_id,
                Integration.provider == provider,
            )
        )

        if not include_deleted:
            query = query.where(Integration.is_deleted == False)  # noqa: E712

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_active_github(
        self,
        workspace_id: UUID,
    ) -> Integration | None:
        """Get active GitHub integration for a workspace.

        Args:
            workspace_id: Workspace UUID.

        Returns:
            Active GitHub Integration or None.
        """
        query = select(Integration).where(
            and_(
                Integration.workspace_id == workspace_id,
                Integration.provider == IntegrationProvider.GITHUB,
                Integration.is_active == True,  # noqa: E712
                Integration.is_deleted == False,  # noqa: E712
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_external_account(
        self,
        provider: IntegrationProvider,
        external_account_id: str,
    ) -> Sequence[Integration]:
        """Get all integrations for an external account.

        Useful for processing webhooks where we need to find
        all workspaces connected to a GitHub org/installation.

        Args:
            provider: Integration provider.
            external_account_id: External service account ID.

        Returns:
            List of matching integrations.
        """
        query = (
            select(Integration)
            .where(
                and_(
                    Integration.provider == provider,
                    Integration.external_account_id == external_account_id,
                    Integration.is_active == True,  # noqa: E712
                    Integration.is_deleted == False,  # noqa: E712
                )
            )
            .options(joinedload(Integration.links))
        )
        result = await self.session.execute(query)
        return result.unique().scalars().all()

    async def deactivate(
        self,
        integration_id: UUID,
    ) -> Integration | None:
        """Deactivate an integration.

        Args:
            integration_id: Integration UUID.

        Returns:
            Updated integration or None if not found.
        """
        integration = await self.get_by_id(integration_id)
        if integration:
            integration.is_active = False
            await self.session.flush()
            await self.session.refresh(integration)
        return integration

    async def update_tokens(
        self,
        integration_id: UUID,
        *,
        access_token: str,
        refresh_token: str | None = None,
        token_expires_at: str | None = None,
    ) -> Integration | None:
        """Update OAuth tokens for an integration.

        Args:
            integration_id: Integration UUID.
            access_token: New access token (encrypted).
            refresh_token: New refresh token (encrypted, optional).
            token_expires_at: Token expiration timestamp (optional).

        Returns:
            Updated integration or None if not found.
        """
        integration = await self.get_by_id(integration_id)
        if integration:
            integration.access_token = access_token
            if refresh_token is not None:
                integration.refresh_token = refresh_token
            if token_expires_at is not None:
                integration.token_expires_at = token_expires_at
            await self.session.flush()
            await self.session.refresh(integration)
        return integration


__all__ = ["IntegrationRepository"]
