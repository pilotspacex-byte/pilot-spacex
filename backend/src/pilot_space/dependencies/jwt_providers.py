"""JWT Provider Abstraction — supports Supabase (default) and AuthCore.

Controlled by AUTH_PROVIDER env var (default: "supabase").

PO trade-off (MVP): AuthCore path validates RS256 signature + expiry only.
JTI blacklist is NOT checked — access tokens are short-lived (15 min).
"""

from __future__ import annotations

import base64
import json
from typing import TYPE_CHECKING, Protocol, runtime_checkable
from uuid import UUID

import jwt
from jwt import PyJWTError

from pilot_space.infrastructure.auth import (
    SupabaseAuth,
    SupabaseAuthError,
    TokenExpiredError as SupabaseTokenExpiredError,
    TokenPayload,
)
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from pilot_space.config import Settings

logger = get_logger(__name__)


class JWTValidationError(Exception):
    """Token failed validation (invalid signature, missing claims, etc.)."""


class JWTExpiredError(JWTValidationError):
    """Token is expired."""


@runtime_checkable
class JWTProvider(Protocol):
    """Protocol for JWT validation providers.

    Each implementation validates a raw Bearer token and returns a
    TokenPayload or raises JWTValidationError / JWTExpiredError.
    """

    def verify_token(self, token: str) -> TokenPayload:
        """Validate token and return TokenPayload.

        Args:
            token: Raw JWT Bearer token string.

        Returns:
            Validated TokenPayload with user identity and claims.

        Raises:
            JWTExpiredError: If the token has expired.
            JWTValidationError: If the token is invalid for any other reason.
        """
        ...


class SupabaseJWTProvider:
    """Validates Supabase Auth JWT tokens (HS256 / ES256).

    Delegates to the existing SupabaseAuth infrastructure. This provider
    is the default and maintains full backward compatibility.
    """

    def __init__(self, auth: SupabaseAuth | None = None) -> None:
        self._auth = auth or SupabaseAuth()

    def verify_token(self, token: str) -> TokenPayload:
        """Validate Supabase JWT and return TokenPayload.

        Args:
            token: Raw JWT Bearer token string.

        Returns:
            Validated TokenPayload from Supabase claims.

        Raises:
            JWTExpiredError: If the token has expired.
            JWTValidationError: If the token is invalid.
        """
        try:
            return self._auth.validate_token(token)
        except SupabaseTokenExpiredError as e:
            raise JWTExpiredError(str(e)) from e
        except SupabaseAuthError as e:
            raise JWTValidationError(str(e)) from e


class AuthCoreJWTProvider:
    """Validates AuthCore RS256 JWT tokens.

    Verifies the RS256 signature using the configured PEM public key,
    enforces required claims (sub, jti, exp, iat), and constructs a
    TokenPayload compatible with all downstream Pilot Space code.

    JTI blacklist is NOT checked (PO-approved MVP trade-off).
    Access tokens are short-lived (15 min), making revocation less critical.
    """

    ALGORITHM = "RS256"

    def __init__(self, public_key_pem: str) -> None:
        """Initialise AuthCore JWT provider.

        Args:
            public_key_pem: PEM-encoded RSA public key for RS256 verification.
        """
        self._public_key_pem = public_key_pem

    def verify_token(self, token: str) -> TokenPayload:
        """Validate AuthCore RS256 JWT and return TokenPayload.

        Performs:
        1. RS256 signature verification with the configured public key.
        2. Required claim validation (sub, jti, exp, iat).
        3. UUID parsing of the sub claim.

        AuthCore tokens do not carry email, aud, app_metadata, or
        user_metadata — TokenPayload handles these with safe defaults.

        Args:
            token: Raw JWT Bearer token string.

        Returns:
            TokenPayload with user_id populated from sub claim.

        Raises:
            JWTExpiredError: If the token has expired.
            JWTValidationError: If the token signature is invalid or claims
                                are missing/malformed.
        """
        try:
            claims = jwt.decode(
                token,
                self._public_key_pem,
                algorithms=[self.ALGORITHM],
                options={"require": ["sub", "jti", "exp", "iat"]},
            )
        except jwt.ExpiredSignatureError as e:
            raise JWTExpiredError("AuthCore token has expired") from e
        except PyJWTError as e:
            raise JWTValidationError(f"AuthCore token is invalid: {e}") from e

        sub = claims.get("sub")
        try:
            UUID(str(sub))  # validate UUID format before passing to TokenPayload
        except (ValueError, TypeError) as e:
            raise JWTValidationError(f"Invalid sub claim: {sub!r}") from e

        return TokenPayload(
            sub=str(sub),
            exp=int(claims["exp"]),
            iat=int(claims["iat"]),
            role=str(claims.get("role", "authenticated")),
            # email, aud, app_metadata, user_metadata use TokenPayload defaults
        )


class DualJWTProvider:
    """Routes token validation to AuthCore (RS256) or Supabase (HS256).

    During the migration period, browsers may hold cached Supabase tokens
    while the backend is configured for AuthCore. This provider inspects
    the JWT header's ``alg`` field (without verification) to select the
    correct verifier, maintaining security since both providers validate
    signatures independently.
    """

    def __init__(
        self,
        authcore: AuthCoreJWTProvider,
        supabase: SupabaseJWTProvider,
    ) -> None:
        self._authcore = authcore
        self._supabase = supabase

    def verify_token(self, token: str) -> TokenPayload:
        """Validate token using the provider matching its algorithm.

        Args:
            token: Raw JWT Bearer token string.

        Returns:
            Validated TokenPayload from the matching provider.

        Raises:
            JWTExpiredError: If the token has expired.
            JWTValidationError: If the token is invalid.
        """
        alg = self._peek_algorithm(token)
        if alg in ("HS256", "ES256"):
            return self._supabase.verify_token(token)
        if alg == "RS256":
            return self._authcore.verify_token(token)
        raise JWTValidationError(f"Unsupported or unreadable JWT algorithm: {alg!r}")

    @staticmethod
    def _peek_algorithm(token: str) -> str:
        """Read the alg field from the unverified JWT header."""
        try:
            header_b64 = token.split(".", maxsplit=1)[0]
            # Pad base64url to standard base64
            padding = 4 - len(header_b64) % 4
            if padding < 4:
                header_b64 += "=" * padding
            header = json.loads(base64.urlsafe_b64decode(header_b64))
            return str(header.get("alg", ""))
        except Exception:
            return ""


def get_jwt_provider(settings: Settings) -> JWTProvider:
    """Factory: return the correct JWTProvider based on settings.auth_provider.

    Default is "supabase" for full backward compatibility.
    Fails-fast at startup for authcore mode when AUTHCORE_PUBLIC_KEY is absent.

    When AUTH_PROVIDER=authcore, returns a DualJWTProvider that accepts both
    AuthCore RS256 and Supabase HS256 tokens.  This handles the migration
    period where browsers may still hold cached Supabase tokens.

    Args:
        settings: Application settings instance.

    Returns:
        A JWTProvider implementation for the configured auth provider.

    Raises:
        ValueError: If auth_provider is unrecognised OR if auth_provider is
                    "authcore" and AUTHCORE_PUBLIC_KEY is not set.
    """
    provider = (settings.auth_provider or "supabase").lower().strip()

    if provider == "supabase":
        return SupabaseJWTProvider()

    if provider == "authcore":
        public_key = settings.authcore_public_key
        if not public_key:
            raise ValueError(
                "AUTH_PROVIDER=authcore requires AUTHCORE_PUBLIC_KEY to be set. "
                "Set AUTHCORE_PUBLIC_KEY to the PEM-encoded RSA public key."
            )
        return DualJWTProvider(
            authcore=AuthCoreJWTProvider(public_key_pem=public_key),
            supabase=SupabaseJWTProvider(),
        )

    raise ValueError(
        f"Unknown AUTH_PROVIDER {provider!r}. Supported values: 'supabase' (default), 'authcore'."
    )
