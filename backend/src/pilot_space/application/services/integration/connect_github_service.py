"""Connect GitHub OAuth service.

T181: Create ConnectGitHubService for OAuth code exchange and setup.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pilot_space.infrastructure.database.models import (
    Integration,
    IntegrationProvider,
)
from pilot_space.infrastructure.encryption import encrypt_api_key
from pilot_space.integrations.github.client import (
    GitHubAuthError,
    GitHubClient,
)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.repositories import IntegrationRepository

logger = logging.getLogger(__name__)


class GitHubConnectionError(Exception):
    """Raised when GitHub connection fails."""


@dataclass
class ConnectGitHubPayload:
    """Payload for connecting GitHub integration.

    Attributes:
        workspace_id: Workspace UUID.
        code: OAuth authorization code.
        user_id: User performing the connection.
        client_id: GitHub OAuth app client ID.
        client_secret: GitHub OAuth app client secret.
        redirect_uri: OAuth redirect URI.
    """

    workspace_id: UUID
    code: str
    user_id: UUID
    client_id: str
    client_secret: str
    redirect_uri: str | None = None


@dataclass
class ConnectGitHubResult:
    """Result from GitHub connection."""

    integration: Integration
    github_login: str
    github_name: str | None
    github_avatar_url: str
    connected: bool = True


class ConnectGitHubService:
    """Service for connecting GitHub via OAuth.

    Handles:
    - OAuth code exchange
    - Token encryption and storage
    - User info retrieval
    - Integration record creation
    """

    def __init__(
        self,
        session: AsyncSession,
        integration_repo: IntegrationRepository,
    ) -> None:
        """Initialize service.

        Args:
            session: Async database session.
            integration_repo: Integration repository.
        """
        self._session = session
        self._repo = integration_repo

    async def execute(self, payload: ConnectGitHubPayload) -> ConnectGitHubResult:
        """Connect GitHub integration via OAuth.

        Args:
            payload: Connection parameters.

        Returns:
            ConnectGitHubResult with integration details.

        Raises:
            GitHubConnectionError: If connection fails.
        """
        logger.info(
            "Connecting GitHub integration",
            extra={"workspace_id": str(payload.workspace_id)},
        )

        # Check for existing integration
        existing = await self._repo.get_by_provider(
            workspace_id=payload.workspace_id,
            provider=IntegrationProvider.GITHUB,
        )
        if existing and existing.is_active:
            raise GitHubConnectionError("GitHub integration already exists for this workspace")

        # Exchange code for token
        try:
            access_token, refresh_token = await GitHubClient.exchange_code(
                client_id=payload.client_id,
                client_secret=payload.client_secret,
                code=payload.code,
                redirect_uri=payload.redirect_uri,
            )
        except GitHubAuthError as e:
            logger.exception("GitHub OAuth failed")
            raise GitHubConnectionError(f"OAuth code exchange failed: {e}") from e

        # Get user info
        async with GitHubClient(access_token) as client:
            try:
                user = await client.get_current_user()
            except Exception as e:
                logger.exception("Failed to get GitHub user")
                raise GitHubConnectionError(f"Failed to get user info: {e}") from e

        # Encrypt tokens for storage
        encrypted_access = encrypt_api_key(access_token)
        encrypted_refresh = encrypt_api_key(refresh_token) if refresh_token else None

        # Create or update integration
        if existing:
            # Reactivate existing integration
            existing.access_token = encrypted_access
            existing.refresh_token = encrypted_refresh
            existing.external_account_id = str(user.id)
            existing.external_account_name = user.login
            existing.is_active = True
            existing.is_deleted = False
            existing.installed_by_id = payload.user_id
            existing.settings = {
                "avatar_url": user.avatar_url,
                "name": user.name,
                "email": user.email,
            }
            await self._session.flush()
            await self._session.refresh(existing)
            integration = existing
        else:
            # Create new integration
            integration = Integration(
                workspace_id=payload.workspace_id,
                provider=IntegrationProvider.GITHUB,
                access_token=encrypted_access,
                refresh_token=encrypted_refresh,
                external_account_id=str(user.id),
                external_account_name=user.login,
                installed_by_id=payload.user_id,
                is_active=True,
                settings={
                    "avatar_url": user.avatar_url,
                    "name": user.name,
                    "email": user.email,
                },
            )
            self._session.add(integration)
            await self._session.flush()
            await self._session.refresh(integration)

        logger.info(
            "GitHub integration connected",
            extra={
                "workspace_id": str(payload.workspace_id),
                "github_login": user.login,
            },
        )

        return ConnectGitHubResult(
            integration=integration,
            github_login=user.login,
            github_name=user.name,
            github_avatar_url=user.avatar_url,
        )

    @staticmethod
    def get_authorize_url(
        client_id: str,
        redirect_uri: str,
        state: str | None = None,
    ) -> str:
        """Generate GitHub OAuth authorization URL.

        Args:
            client_id: GitHub OAuth app client ID.
            redirect_uri: Redirect URI after authorization.
            state: CSRF state parameter.

        Returns:
            Authorization URL.
        """
        return GitHubClient.get_authorize_url(
            client_id=client_id,
            redirect_uri=redirect_uri,
            state=state,
        )


__all__ = [
    "ConnectGitHubPayload",
    "ConnectGitHubResult",
    "ConnectGitHubService",
    "GitHubConnectionError",
]
