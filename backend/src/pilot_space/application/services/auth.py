"""Authentication service for Pilot Space (CQRS-lite).

Handles OAuth login URL construction, user profile retrieval/update, logout,
and CLI API key validation.
Migrated from direct repo/settings usage in auth router per DD-064.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.domain.exceptions import NotFoundError, UnauthorizedError
from pilot_space.infrastructure.database.models.user import User
from pilot_space.infrastructure.database.repositories.pilot_api_key_repository import (
    PilotAPIKeyRepository,
)
from pilot_space.infrastructure.database.repositories.user_repository import (
    UserRepository,
)
from pilot_space.infrastructure.database.repositories.workspace_repository import (
    WorkspaceRepository,
)
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

# Sentinel to distinguish "not provided" from "explicitly None"
UNSET: Any = object()


@dataclass
class GetLoginUrlPayload:
    """Payload for building OAuth login URL."""

    provider: str
    redirect_url: str | None = None


@dataclass
class GetLoginUrlResult:
    """Result containing the OAuth redirect URL."""

    url: str
    provider: str


@dataclass
class GetProfilePayload:
    """Payload for retrieving user profile."""

    user_id: UUID


@dataclass
class GetProfileResult:
    """Result containing the user profile entity."""

    user: User


@dataclass
class UpdateProfilePayload:
    """Payload for updating user profile fields."""

    user_id: UUID
    full_name: str | None = None
    avatar_url: str | None = None
    bio: str | None = None
    default_sdlc_role: str | None = None
    ai_settings: Any = field(default=UNSET)  # UNSET sentinel or dict | None


@dataclass
class UpdateProfileResult:
    """Result containing updated user and list of changed fields."""

    user: User
    changed_fields: list[str] = field(default_factory=list)


@dataclass
class LogoutPayload:
    """Payload for user logout."""

    user_id: UUID


@dataclass
class LogoutResult:
    """Result confirming logout success."""

    success: bool


class AuthService:
    """Service for authentication operations.

    Follows CQRS-lite pattern per DD-064.
    """

    def __init__(
        self,
        user_repo: UserRepository,
        supabase_url: str,
        default_redirect_origin: str,
    ) -> None:
        self._user_repo = user_repo
        self._supabase_url = supabase_url
        self._default_redirect_origin = default_redirect_origin

    async def get_login_url(
        self,
        payload: GetLoginUrlPayload,
    ) -> GetLoginUrlResult:
        """Build Supabase OAuth redirect URL.

        Args:
            payload: Login URL payload with provider and optional redirect.

        Returns:
            Result containing the constructed OAuth URL.
        """
        redirect_to = payload.redirect_url or f"{self._default_redirect_origin}/auth/callback"
        auth_url = (
            f"{self._supabase_url}/auth/v1/authorize"
            f"?provider={payload.provider}&redirect_to={redirect_to}"
        )

        return GetLoginUrlResult(url=auth_url, provider=payload.provider)

    async def get_profile(
        self,
        payload: GetProfilePayload,
    ) -> GetProfileResult:
        """Retrieve user profile by ID.

        Args:
            payload: Profile retrieval payload.

        Returns:
            Result containing the user entity.

        Raises:
            ValueError: If user not found.
        """
        user = await self._user_repo.get_by_id(payload.user_id)
        if not user:
            msg = "User not found"
            raise NotFoundError(msg)

        return GetProfileResult(user=user)

    async def update_profile(
        self,
        payload: UpdateProfilePayload,
    ) -> UpdateProfileResult:
        """Update user profile fields.

        Only updates explicitly provided (non-None) fields.

        Args:
            payload: Profile update payload.

        Returns:
            Result containing updated user and list of changed field names.

        Raises:
            ValueError: If user not found.
        """
        user = await self._user_repo.get_by_id(payload.user_id)
        if not user:
            msg = "User not found"
            raise NotFoundError(msg)

        changed_fields: list[str] = []

        if payload.full_name is not None:
            user.full_name = payload.full_name
            changed_fields.append("full_name")
        if payload.avatar_url is not None:
            user.avatar_url = payload.avatar_url
            changed_fields.append("avatar_url")
        if payload.bio is not None:
            user.bio = payload.bio
            changed_fields.append("bio")
        if payload.default_sdlc_role is not None:
            user.default_sdlc_role = payload.default_sdlc_role
            changed_fields.append("default_sdlc_role")
        if payload.ai_settings is not UNSET:
            user.ai_settings = payload.ai_settings  # Can be None (clear) or dict (set)
            changed_fields.append("ai_settings")

        if changed_fields:
            user = await self._user_repo.update(user)

        return UpdateProfileResult(user=user, changed_fields=changed_fields)

    async def logout(
        self,
        payload: LogoutPayload,
    ) -> LogoutResult:
        """Process user logout.

        With JWT-based auth, server-side logout is a no-op.
        Client should discard the token.

        Args:
            payload: Logout payload.

        Returns:
            Result confirming success.
        """
        logger.info("User logout", extra={"user_id": str(payload.user_id)})
        return LogoutResult(success=True)


@dataclass
class ValidateAPIKeyPayload:
    """Payload for validating a CLI API key.

    Attributes:
        raw_key: The plaintext API key from the Authorization: Bearer header.
                 Never stored or logged.
    """

    raw_key: str


@dataclass
class ValidateAPIKeyResult:
    """Result returned on successful CLI API key validation.

    Attributes:
        workspace_slug: URL-friendly slug of the key's workspace.
        user_id: UUID string of the key's owning user.
    """

    workspace_slug: str
    user_id: str


class ValidateAPIKeyService:
    """Validate a CLI API key and return workspace context.

    Follows CQRS-lite pattern per DD-064. The raw key is hashed with
    SHA-256 before any database lookup; plaintext is never persisted or logged.
    """

    def __init__(
        self,
        api_key_repository: PilotAPIKeyRepository,
        workspace_repository: WorkspaceRepository,
    ) -> None:
        """Initialize ValidateAPIKeyService.

        Args:
            api_key_repository: Repository for pilot_api_keys table.
            workspace_repository: Repository for workspaces table.
        """
        self._api_key_repo = api_key_repository
        self._workspace_repo = workspace_repository

    async def execute(
        self, payload: ValidateAPIKeyPayload, session: AsyncSession
    ) -> ValidateAPIKeyResult:
        """Validate a raw CLI API key and return workspace info.

        Hashes the raw key with SHA-256, looks it up in the database (the
        pilot_api_keys SELECT policy permits cross-workspace lookup without
        workspace context — see migration 053), then sets RLS context using
        the key's user_id and workspace_id before querying the workspaces table.

        Args:
            payload: Payload containing the raw API key.

        Returns:
            ValidateAPIKeyResult with workspace_slug and user_id.

        Raises:
            UnauthorizedError: If API key is invalid or not found (401).
            NotFoundError: If workspace associated with key is missing.
        """
        from pilot_space.infrastructure.database.rls import set_rls_context

        key_hash = hashlib.sha256(payload.raw_key.encode()).hexdigest()

        api_key = await self._api_key_repo.get_by_key_hash(key_hash)
        if api_key is None:
            logger.warning("api_key_validation_failed", reason="key_not_found")
            msg = "invalid_api_key"
            raise UnauthorizedError(msg)

        # SQL query already filters expired/deleted keys — no Python re-check needed.
        await self._api_key_repo.mark_last_used(api_key.id)

        # Set RLS context so workspace_repository.get_by_id() is scoped correctly.
        await set_rls_context(session, api_key.user_id, api_key.workspace_id)

        workspace = await self._workspace_repo.get_by_id(api_key.workspace_id)
        if workspace is None:
            logger.error(
                "api_key_workspace_not_found",
                key_id=str(api_key.id),
                workspace_id=str(api_key.workspace_id),
            )
            msg = "workspace_not_found"
            raise NotFoundError(msg)

        logger.info("api_key_validated", workspace_slug=workspace.slug)
        return ValidateAPIKeyResult(
            workspace_slug=workspace.slug,
            user_id=str(api_key.user_id),
        )


__all__ = [
    "UNSET",
    "AuthService",
    "GetLoginUrlPayload",
    "GetLoginUrlResult",
    "GetProfilePayload",
    "GetProfileResult",
    "LogoutPayload",
    "LogoutResult",
    "UpdateProfilePayload",
    "UpdateProfileResult",
    "ValidateAPIKeyPayload",
    "ValidateAPIKeyResult",
    "ValidateAPIKeyService",
]
