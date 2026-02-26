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

    Maintains an in-memory pending-state registry (state → code_verifier +
    workspace_id) for CSRF protection during the OAuth redirect flow.
    """

    def __init__(
        self,
        credential_repo: DriveCredentialRepository,
        settings: Settings,
    ) -> None:
        """Initialize service.

        Args:
            credential_repo: Repository for Drive credential persistence.
            settings: Application settings with Google OAuth fields.
        """
        self._credential_repo = credential_repo
        self._settings = settings
        # state → (code_verifier, workspace_id_str, redirect_uri)
        self._pending_states: dict[str, tuple[str, str, str]] = {}

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
    ) -> dict[str, str]:
        """Build a Google OAuth PKCE authorization URL.

        Generates a PKCE code verifier + challenge pair and a random state
        token, stores both in ``_pending_states`` keyed by state, then
        returns the constructed authorization URL.

        Args:
            workspace_id: Workspace initiating the OAuth flow.
            redirect_uri: Callback URI registered with the OAuth client.

        Returns:
            Dict with key ``auth_url`` containing the full authorization URL.
        """
        code_verifier = secrets.token_urlsafe(64)
        digest = hashlib.sha256(code_verifier.encode()).digest()
        code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
        state = secrets.token_urlsafe(32)

        self._pending_states[state] = (code_verifier, str(workspace_id), redirect_uri)

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
        workspace_id: UUID,
        user_id: UUID,
        session: AsyncSession | None = None,
    ) -> None:
        """Exchange an authorization code for tokens and persist the credential.

        Validates the ``state`` parameter against the in-memory registry,
        performs the PKCE token exchange with Google, fetches the associated
        Google account email, encrypts the tokens, and upserts the credential.

        Args:
            code: Authorization code received from Google's redirect.
            state: CSRF state token that must match a previously issued value.
            workspace_id: Workspace the credential belongs to.
            user_id: Authenticated user ID owning the credential.
            session: Optional database session (unused; repo manages its own).

        Raises:
            HTTPException 400: When ``state`` is invalid or was never issued.
        """
        if state not in self._pending_states:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_STATE", "message": "OAuth state is invalid or expired"},
            )

        code_verifier, _workspace_id_str, redirect_uri = self._pending_states.pop(state)

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
