"""MCP OAuth 2.0 flow service.

Extracts OAuth state generation, Redis persistence, and code exchange logic
from workspace_mcp_servers.py router. The router keeps only HTTP concerns
(query param extraction, RedirectResponse construction).
"""

from __future__ import annotations

import json
import secrets
import urllib.parse
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.domain.exceptions import (
    NotFoundError,
    ServiceUnavailableError,
    ValidationError,
)
from pilot_space.infrastructure.database.models.workspace_mcp_server import (
    McpAuthType,
)
from pilot_space.infrastructure.database.repositories.workspace_mcp_server_repository import (
    WorkspaceMcpServerRepository,
)
from pilot_space.infrastructure.encryption import encrypt_api_key
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)


@dataclass
class OAuthInitResult:
    """Result of initiating an OAuth flow."""

    auth_url: str
    state: str


@dataclass
class OAuthCallbackResult:
    """Result of handling an OAuth callback."""

    success: bool
    redirect_path: str
    error_reason: str | None = None


class McpOAuthService:
    """Handles MCP server OAuth 2.0 authorization flows.

    Responsibilities:
    - Generate OAuth state tokens and persist to Redis
    - Build authorization URLs
    - Handle callbacks: validate state, exchange code for token, encrypt and store
    """

    def __init__(
        self,
        session: AsyncSession,
        redis: Any,
        workspace_mcp_server_repository: WorkspaceMcpServerRepository,
    ) -> None:
        self._session = session
        self._redis = redis
        self._repo = workspace_mcp_server_repository

    async def initiate_oauth(
        self,
        workspace_id: UUID,
        server_id: UUID,
        user_id: UUID,
        workspace_slug: str,
        backend_url: str,
    ) -> OAuthInitResult:
        """Build OAuth 2.0 authorization URL and persist state to Redis.

        Args:
            workspace_id: Target workspace UUID.
            server_id: Server requiring OAuth authorization.
            user_id: Authenticated user initiating the flow.
            workspace_slug: Workspace slug for redirect URL.
            backend_url: Backend base URL for callback construction.

        Returns:
            OAuthInitResult with auth_url and state token.

        Raises:
            NotFoundError: Server not found.
            ValidationError: Server not configured for OAuth2.
            ServiceUnavailableError: Redis unavailable.
        """
        server = await self._repo.get_by_workspace_and_id(
            server_id=server_id, workspace_id=workspace_id
        )
        if not server:
            raise NotFoundError("MCP server not found")
        if server.auth_type != McpAuthType.OAUTH2:
            raise ValidationError("Server is not configured for OAuth2 auth_type")
        if not server.oauth_auth_url or not server.oauth_client_id:
            raise ValidationError("Server missing oauth_auth_url or oauth_client_id")

        if self._redis is None:
            raise ServiceUnavailableError(
                "OAuth state storage (Redis) is unavailable; cannot initiate OAuth flow"
            )

        state = secrets.token_urlsafe(32)

        state_data: dict[str, Any] = {
            "server_id": str(server_id),
            "workspace_id": str(workspace_id),
            "workspace_slug": workspace_slug,
            "user_id": str(user_id),
        }
        try:
            await self._redis.client.set(
                f"mcp_oauth_state:{state}",
                json.dumps(state_data),
                ex=600,
            )
        except Exception as exc:
            logger.exception(
                "mcp_oauth_state_persist_failed",
                server_id=str(server_id),
                error=str(exc),
            )
            raise ServiceUnavailableError(
                "Failed to persist OAuth state; cannot initiate OAuth flow"
            ) from exc

        callback_url = backend_url.rstrip("/") + "/api/v1/oauth2/mcp-callback"
        params = {
            "response_type": "code",
            "client_id": server.oauth_client_id,
            "redirect_uri": callback_url,
            "state": state,
        }
        if server.oauth_scopes:
            params["scope"] = server.oauth_scopes

        auth_url = server.oauth_auth_url + "?" + urllib.parse.urlencode(params)

        logger.info(
            "mcp_oauth_url_generated",
            workspace_id=str(workspace_id),
            server_id=str(server_id),
        )
        return OAuthInitResult(auth_url=auth_url, state=state)

    @staticmethod
    async def handle_callback(  # noqa: PLR0911
        *,
        redis: Any,
        code: str,
        state: str,
        backend_url: str,
        workspace_slug_re: Any,
    ) -> OAuthCallbackResult:
        """Handle OAuth 2.0 callback: validate state, exchange code, store token.

        This is a static method because the callback route does not have a
        request-scoped session -- it opens its own session via get_db_session().

        Args:
            redis: Redis client for state retrieval.
            code: Authorization code from the OAuth provider.
            state: State token for CSRF validation.
            backend_url: Backend base URL for callback construction.
            workspace_slug_re: Compiled regex for slug validation.

        Returns:
            OAuthCallbackResult with redirect path and success/error status.
        """
        from pilot_space.infrastructure.database import get_db_session
        from pilot_space.infrastructure.database.rls import set_rls_context

        fallback_redirect = "/settings/mcp-servers"

        if redis is None:
            return OAuthCallbackResult(
                success=False,
                redirect_path=f"{fallback_redirect}?status=error&reason=no_redis",
            )

        raw = await redis.client.get(f"mcp_oauth_state:{state}")
        if raw is None:
            return OAuthCallbackResult(
                success=False,
                redirect_path=f"{fallback_redirect}?status=error&reason=invalid_state",
            )

        try:
            state_data = json.loads(raw)
            server_id = UUID(state_data["server_id"])
            workspace_id = UUID(state_data["workspace_id"])
            initiating_user_id = UUID(state_data["user_id"])
        except (json.JSONDecodeError, KeyError, ValueError):
            return OAuthCallbackResult(
                success=False,
                redirect_path=f"{fallback_redirect}?status=error&reason=state_decode_error",
            )

        workspace_slug = state_data.get("workspace_slug", "")
        if workspace_slug and not workspace_slug_re.match(workspace_slug):
            workspace_slug = ""
        redirect_base = (
            f"/{workspace_slug}/settings/mcp-servers" if workspace_slug else "/settings/mcp-servers"
        )

        await redis.client.delete(f"mcp_oauth_state:{state}")

        try:
            async with get_db_session() as db_session:
                await set_rls_context(db_session, initiating_user_id, workspace_id)
                repo = WorkspaceMcpServerRepository(session=db_session)
                server = await repo.get_by_workspace_and_id(
                    server_id=server_id, workspace_id=workspace_id
                )
                if not server or not server.oauth_token_url:
                    return OAuthCallbackResult(
                        success=False,
                        redirect_path=f"{redirect_base}?status=error&reason=server_not_found",
                    )

                callback_url = backend_url.rstrip("/") + "/api/v1/oauth2/mcp-callback"
                token_response = await _exchange_oauth_code(
                    token_url=server.oauth_token_url,
                    client_id=server.oauth_client_id or "",
                    code=code,
                    redirect_uri=callback_url,
                )

                if token_response is None:
                    return OAuthCallbackResult(
                        success=False,
                        redirect_path=f"{redirect_base}?status=error&reason=token_exchange_failed",
                    )

                encrypted = encrypt_api_key(token_response)
                server.auth_token_encrypted = encrypted
                await repo.update(server)

                logger.info(
                    "mcp_oauth_token_stored",
                    server_id=str(server_id),
                    workspace_id=str(workspace_id),
                )

        except Exception as exc:
            logger.error("mcp_oauth_callback_exception", error=str(exc), exc_info=True)
            return OAuthCallbackResult(
                success=False,
                redirect_path=f"{redirect_base}?status=error&reason=internal_error",
            )

        return OAuthCallbackResult(
            success=True,
            redirect_path=f"{redirect_base}?status=connected",
        )


async def _exchange_oauth_code(
    token_url: str,
    client_id: str,
    code: str,
    redirect_uri: str,
) -> str | None:
    """Exchange authorization code for access token."""
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
            response = await client.post(
                token_url,
                data={
                    "grant_type": "authorization_code",
                    "client_id": client_id,
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
            return data.get("access_token")
    except Exception as exc:
        logger.warning("mcp_oauth_token_exchange_failed", error=str(exc))
        return None
