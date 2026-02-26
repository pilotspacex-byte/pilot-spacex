"""DriveOAuthService — Google Drive OAuth PKCE flow and credential management.

Feature: 020 — Chat Context Attachments & Google Drive
Source: FR-009, FR-010, FR-012
"""

from __future__ import annotations

import base64
import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import httpx
from fastapi import HTTPException, status

from pilot_space.api.v1.schemas.attachments import DriveStatusResponse
from pilot_space.infrastructure.database.models.drive_credential import DriveCredential
from pilot_space.infrastructure.encryption import EncryptionError, decrypt_api_key, encrypt_api_key
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.config import Settings
    from pilot_space.infrastructure.cache.redis import RedisClient
    from pilot_space.infrastructure.database.repositories.drive_credential_repository import (
        DriveCredentialRepository,
    )

logger = get_logger(__name__)

_TOKEN_URL = "https://oauth2.googleapis.com/token"
_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
_AUTH_BASE = "https://accounts.google.com/o/oauth2/v2/auth"
_SCOPE = "https://www.googleapis.com/auth/drive.readonly"


class DriveOAuthService:
    """Manages Google Drive OAuth PKCE flow and credential lifecycle.

    Maintains a PKCE pending-state registry (state → code_verifier +
    workspace_id + redirect_uri + user_id) for CSRF protection during
    the OAuth redirect flow. Redis is used when available for multi-worker
    compatibility; falls back to in-memory for single-worker/test environments.
    """

    _PKCE_STATE_TTL = 600  # 10 minutes

    def __init__(
        self,
        credential_repo: DriveCredentialRepository,
        settings: Settings,
        redis_client: RedisClient | None = None,
    ) -> None:
        """Initialize service.

        Args:
            credential_repo: Repository for Drive credential persistence.
            settings: Application settings with Google OAuth fields.
            redis_client: Optional Redis client for multi-worker PKCE state storage.
                When None, falls back to in-memory dict (single-worker / tests).
        """
        self._credential_repo = credential_repo
        self._settings = settings
        self._redis = redis_client
        # Fallback in-memory for tests/dev (redis_client is None)
        # state → (code_verifier, workspace_id_str, redirect_uri, user_id_str)
        self._pending_states: dict[str, tuple[str, str, str, str]] = {}

    async def get_status(
        self,
        user_id: UUID,
        workspace_id: UUID,
        session: AsyncSession | None = None,
    ) -> DriveStatusResponse:
        """Return Drive connection status for the user+workspace.

        Args:
            user_id: Authenticated user ID.
            workspace_id: Target workspace ID.
            session: Optional database session (unused; repo manages its own).

        Returns:
            DriveStatusResponse with connected flag and email when present.
        """
        cred = await self._credential_repo.get_by_user_workspace(user_id, workspace_id)
        if cred is None:
            return DriveStatusResponse(connected=False, google_email=None, connected_at=None)

        return DriveStatusResponse(
            connected=True,
            google_email=cred.google_email,
            connected_at=cred.created_at,
        )

    async def get_auth_url(
        self,
        workspace_id: UUID,
        redirect_uri: str,
        user_id: UUID,
    ) -> dict[str, str]:
        """Build a Google OAuth PKCE authorization URL.

        Generates a PKCE code verifier + challenge pair and a random state
        token, stores both (plus user_id) in the state registry keyed by state,
        then returns the constructed authorization URL.

        Args:
            workspace_id: Workspace initiating the OAuth flow.
            redirect_uri: Callback URI registered with the OAuth client.
            user_id: Authenticated user ID initiating the OAuth flow.

        Returns:
            Dict with key ``auth_url`` containing the full authorization URL.
        """
        code_verifier = secrets.token_urlsafe(64)
        digest = hashlib.sha256(code_verifier.encode()).digest()
        code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
        state = secrets.token_urlsafe(32)

        state_data = (code_verifier, str(workspace_id), redirect_uri, str(user_id))

        if self._redis is not None:
            key = f"drive:pkce:{state}"
            await self._redis.set(key, {"state_data": list(state_data)}, ttl=self._PKCE_STATE_TTL)
        else:
            self._pending_states[state] = state_data

        from urllib.parse import urlencode

        params = {
            "client_id": str(self._settings.google_client_id),
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": _SCOPE,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "state": state,
            "access_type": "offline",
        }
        auth_url = f"{_AUTH_BASE}?{urlencode(params)}"

        return {"auth_url": auth_url}

    async def handle_callback(
        self,
        code: str,
        state: str,
        session: AsyncSession | None = None,
    ) -> str:
        """Exchange an authorization code for tokens and persist the credential.

        Validates the ``state`` parameter against the state registry,
        performs the PKCE token exchange with Google, fetches the associated
        Google account email, encrypts the tokens, and upserts the credential.
        The user_id and workspace_id are extracted from the state registry —
        no JWT is required on this endpoint (Google does not send one).

        Args:
            code: Authorization code received from Google's redirect.
            state: CSRF state token that must match a previously issued value.
            session: Optional database session (unused; repo manages its own).

        Returns:
            workspace_id as a string (used by the caller to build the redirect URL).

        Raises:
            HTTPException 400: When ``state`` is invalid or was never issued.
        """
        if self._redis is not None:
            key = f"drive:pkce:{state}"
            cached = await self._redis.get(key)
            if not cached:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "INVALID_STATE",
                        "message": "OAuth state is invalid or expired",
                    },
                )
            code_verifier, workspace_id_str, redirect_uri, user_id_str = cached["state_data"]
            await self._redis.delete(key)
        else:
            if state not in self._pending_states:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "INVALID_STATE",
                        "message": "OAuth state is invalid or expired",
                    },
                )
            code_verifier, workspace_id_str, redirect_uri, user_id_str = self._pending_states.pop(
                state
            )

        user_id = UUID(user_id_str)
        workspace_id = UUID(workspace_id_str)

        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                _TOKEN_URL,
                data={
                    "client_id": str(self._settings.google_client_id),
                    "client_secret": self._settings.google_client_secret.get_secret_value(),
                    "code": code,
                    "code_verifier": code_verifier,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
            )
            token_response.raise_for_status()
            token_data = token_response.json()

            userinfo_response = await client.get(
                _USERINFO_URL,
                headers={"Authorization": f"Bearer {token_data['access_token']}"},
            )
            userinfo_response.raise_for_status()
            userinfo = userinfo_response.json()

        expires_in: int = token_data.get("expires_in", 3600)
        token_expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)

        encrypted_access_token = encrypt_api_key(token_data["access_token"])
        encrypted_refresh_token = encrypt_api_key(token_data.get("refresh_token", ""))

        credential = DriveCredential(
            id=uuid4(),
            user_id=user_id,
            workspace_id=workspace_id,
            google_email=userinfo.get("email", ""),
            access_token=encrypted_access_token,
            refresh_token=encrypted_refresh_token,
            token_expires_at=token_expires_at,
            scope=token_data.get("scope", _SCOPE),
        )

        await self._credential_repo.upsert(credential)
        logger.info(
            "drive_credential_upserted",
            user_id=str(user_id),
            workspace_id=str(workspace_id),
            google_email=userinfo.get("email"),
        )

        return workspace_id_str

    async def refresh_access_token(
        self,
        user_id: UUID,
        workspace_id: UUID,
    ) -> str:
        """Silently refresh an expired access token using the stored refresh token.

        Args:
            user_id: Authenticated user ID.
            workspace_id: Target workspace ID.

        Returns:
            New plaintext access token.

        Raises:
            HTTPException 402: When no credential or no refresh token exists.
            HTTPException 502: When Google refresh API call fails.
        """
        cred = await self._credential_repo.get_by_user_workspace(user_id, workspace_id)
        if not cred:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={"code": "DRIVE_NOT_CONNECTED", "message": "No Drive credential"},
            )

        try:
            refresh_token = decrypt_api_key(cred.refresh_token)
        except EncryptionError:
            refresh_token = cred.refresh_token

        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={"code": "DRIVE_NOT_CONNECTED", "message": "No refresh token stored"},
            )

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    _TOKEN_URL,
                    data={
                        "client_id": str(self._settings.google_client_id),
                        "client_secret": self._settings.google_client_secret.get_secret_value(),
                        "refresh_token": refresh_token,
                        "grant_type": "refresh_token",
                    },
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail={"code": "DRIVE_API_ERROR", "message": "Token refresh failed"},
                ) from exc

        token_data = response.json()
        new_access_token = token_data["access_token"]
        expires_in: int = token_data.get("expires_in", 3600)
        new_expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)

        cred.access_token = encrypt_api_key(new_access_token)
        cred.token_expires_at = new_expires_at
        await self._credential_repo.upsert(cred)

        logger.info(
            "drive_token_refreshed",
            user_id=str(user_id),
            workspace_id=str(workspace_id),
        )
        return new_access_token

    async def revoke(
        self,
        user_id: UUID,
        workspace_id: UUID,
        session: AsyncSession | None = None,
    ) -> None:
        """Revoke Google Drive access and delete the stored credential.

        Calls Google's token revocation endpoint before deleting the local
        credential record. If the credential does not exist, raises 404.

        Args:
            user_id: Authenticated user ID.
            workspace_id: Target workspace ID.
            session: Optional database session (unused; repo manages its own).

        Raises:
            HTTPException 404: When no credential exists for user+workspace.
        """
        cred = await self._credential_repo.get_by_user_workspace(user_id, workspace_id)
        if cred is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "DRIVE_NOT_CONNECTED",
                    "message": "No Google Drive credential found for this workspace",
                },
            )

        try:
            access_token = decrypt_api_key(cred.access_token)
        except EncryptionError:
            # Fallback for test mocks or dev where stored value is plaintext
            access_token = cred.access_token

        async with httpx.AsyncClient() as client:
            try:
                revoke_response = await client.post(
                    _REVOKE_URL,
                    params={"token": access_token},
                )
                revoke_response.raise_for_status()
            except httpx.HTTPStatusError:
                # Token may already be expired or revoked remotely.
                # Always delete the local credential regardless.
                logger.warning(
                    "drive_token_remote_revocation_failed",
                    user_id=str(user_id),
                    workspace_id=str(workspace_id),
                )

        await self._credential_repo.delete_by_user_workspace(user_id, workspace_id)
        logger.info(
            "drive_credential_revoked",
            user_id=str(user_id),
            workspace_id=str(workspace_id),
        )


__all__ = ["DriveOAuthService"]
