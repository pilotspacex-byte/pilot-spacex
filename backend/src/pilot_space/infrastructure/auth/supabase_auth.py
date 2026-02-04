"""Supabase Auth client for authentication and authorization.

Provides JWT validation, user management, and token operations.
Supports both HS256 (legacy/local) and ES256 (Supabase Cloud) algorithms.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any
from uuid import UUID

import httpx
import jwt
from jwt import PyJWKClient, PyJWTError

from pilot_space.config import get_settings

logger = logging.getLogger(__name__)


class SupabaseAuthError(Exception):
    """Base exception for Supabase Auth errors."""


class TokenExpiredError(SupabaseAuthError):
    """Token has expired."""


class TokenInvalidError(SupabaseAuthError):
    """Token is invalid or malformed."""


@dataclass(frozen=True)
class TokenPayload:
    """Validated JWT token payload.

    Attributes:
        sub: Subject (user ID).
        email: User email address.
        role: User role (authenticated, anon, etc.).
        aud: Audience (expected to be "authenticated").
        exp: Expiration timestamp.
        iat: Issued at timestamp.
        app_metadata: Application-level metadata.
        user_metadata: User-level metadata.
    """

    sub: str
    email: str | None
    role: str
    aud: str
    exp: int
    iat: int
    app_metadata: dict[str, Any]
    user_metadata: dict[str, Any]

    @property
    def user_id(self) -> UUID:
        """Get user ID from subject as UUID."""
        return UUID(self.sub)

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.now(tz=UTC).timestamp() > self.exp

    @property
    def expiration_datetime(self) -> datetime:
        """Get expiration as datetime."""
        return datetime.fromtimestamp(self.exp, tz=UTC)


@lru_cache(maxsize=1)
def _get_jwk_client(jwks_url: str) -> PyJWKClient:
    """Get cached JWK client for JWKS URL.

    Args:
        jwks_url: URL to fetch JWKS from.

    Returns:
        PyJWKClient instance.
    """
    return PyJWKClient(jwks_url, cache_keys=True, lifespan=3600)


class SupabaseAuth:
    """Supabase Auth client for JWT operations.

    Handles token validation and user authentication
    against Supabase Auth JWT tokens.

    Supports:
    - ES256 (ECDSA) tokens from Supabase Cloud via JWKS
    - HS256 (HMAC) tokens from local Supabase via JWT secret
    """

    def __init__(
        self,
        jwt_secret: str | None = None,
        supabase_url: str | None = None,
    ) -> None:
        """Initialize Supabase Auth client.

        Args:
            jwt_secret: JWT secret for HS256 validation. If None, uses settings.
            supabase_url: Supabase project URL for JWKS. If None, uses settings.
        """
        settings = get_settings()

        if jwt_secret is None:
            jwt_secret = settings.supabase_jwt_secret.get_secret_value()
        self._jwt_secret = jwt_secret

        if supabase_url is None:
            supabase_url = settings.supabase_url
        self._supabase_url = supabase_url

        # Construct JWKS URL for Supabase Cloud
        self._jwks_url = f"{supabase_url}/auth/v1/.well-known/jwks.json"
        self._jwk_client: PyJWKClient | None = None

    def _get_jwk_client(self) -> PyJWKClient:
        """Get or create JWK client for ES256 verification."""
        if self._jwk_client is None:
            self._jwk_client = _get_jwk_client(self._jwks_url)
        return self._jwk_client

    def _get_algorithm_from_token(self, token: str) -> str:
        """Extract algorithm from JWT header without verification.

        Args:
            token: The JWT token.

        Returns:
            Algorithm string (e.g., 'HS256', 'ES256').
        """
        try:
            header = jwt.get_unverified_header(token)
            return header.get("alg", "HS256")
        except PyJWTError:
            return "HS256"

    def validate_token(self, token: str) -> TokenPayload:
        """Validate and decode a JWT token.

        Automatically detects algorithm (ES256 or HS256) and uses
        appropriate verification method.

        Args:
            token: The JWT access token.

        Returns:
            Validated token payload.

        Raises:
            TokenExpiredError: If token is expired.
            TokenInvalidError: If token is invalid or malformed.
        """
        algorithm = self._get_algorithm_from_token(token)

        try:
            if algorithm == "ES256":
                # Use JWKS for ES256 (Supabase Cloud)
                payload = self._validate_with_jwks(token)
            else:
                # Use JWT secret for HS256 (local Supabase)
                payload = self._validate_with_secret(token, algorithm)

            return TokenPayload(
                sub=payload["sub"],
                email=payload.get("email"),
                role=payload.get("role", "authenticated"),
                aud=payload.get("aud", "authenticated"),
                exp=payload["exp"],
                iat=payload.get("iat", 0),
                app_metadata=payload.get("app_metadata", {}),
                user_metadata=payload.get("user_metadata", {}),
            )
        except jwt.ExpiredSignatureError as e:
            raise TokenExpiredError("Token has expired") from e
        except PyJWTError as e:
            logger.warning("Token validation failed: %s", e)
            raise TokenInvalidError(f"Invalid token: {e}") from e
        except httpx.HTTPError as e:
            logger.exception("Failed to fetch JWKS")
            raise TokenInvalidError(f"Failed to verify token: {e}") from e

    def _validate_with_jwks(self, token: str) -> dict[str, Any]:
        """Validate token using JWKS (for ES256).

        Args:
            token: The JWT token.

        Returns:
            Decoded payload.
        """
        jwk_client = self._get_jwk_client()
        signing_key = jwk_client.get_signing_key_from_jwt(token)

        # Accept both "authenticated" (cloud) and empty string (self-hosted)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            audience=["authenticated", ""],
        )

    def _validate_with_secret(self, token: str, algorithm: str) -> dict[str, Any]:
        """Validate token using JWT secret (for HS256).

        Args:
            token: The JWT token.
            algorithm: The algorithm to use.

        Returns:
            Decoded payload.
        """
        # For self-hosted Supabase (HS256), skip audience verification
        # since we control the JWT secret and self-hosted tokens have empty aud
        return jwt.decode(
            token,
            self._jwt_secret,
            algorithms=[algorithm],
            options={"verify_aud": False},
        )

    def decode_token_unsafe(self, token: str) -> dict[str, Any]:
        """Decode token without validation (for debugging).

        Args:
            token: The JWT token.

        Returns:
            Raw token payload (unvalidated).

        Warning:
            Do not use for authorization decisions.
        """
        return jwt.decode(  # type: ignore[no-any-return]
            token,
            options={"verify_signature": False},
        )

    def get_user_id_from_token(self, token: str) -> UUID:
        """Extract user ID from validated token.

        Args:
            token: The JWT access token.

        Returns:
            User UUID from token subject.

        Raises:
            TokenExpiredError: If token is expired.
            TokenInvalidError: If token is invalid.
        """
        payload = self.validate_token(token)
        return payload.user_id

    def verify_workspace_access(
        self,
        token: str,
        workspace_id: UUID,
    ) -> bool:
        """Verify user has access to workspace.

        This is a placeholder for RLS-based verification.
        Actual verification happens at database level via RLS.

        Args:
            token: The JWT access token.
            workspace_id: The workspace to check access for.

        Returns:
            True if token is valid (RLS handles actual access).
        """
        try:
            self.validate_token(token)
        except SupabaseAuthError:
            return False
        else:
            return True
