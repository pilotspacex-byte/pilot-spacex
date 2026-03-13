"""Integration tests for AuthCore RS256 JWT route guard.

Validates the full request path:
  Bearer RS256 token → get_current_user dependency → 200/401

Covers:
- Valid RS256 token passes get_current_user and is accepted by a protected route
- Expired RS256 token returns 401
- Startup raises ValueError when AUTH_PROVIDER=authcore + no AUTHCORE_PUBLIC_KEY
"""

from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import status

if TYPE_CHECKING:
    from httpx import AsyncClient


# ---------------------------------------------------------------------------
# RSA key helpers (mirrored from unit tests to keep this file self-contained)
# ---------------------------------------------------------------------------


def _make_rsa_keypair() -> tuple[str, str]:
    """Return (private_pem, public_pem) for a fresh RSA-2048 key pair."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return private_pem, public_pem


def _sign_rs256(payload: dict[str, Any], private_pem: str) -> str:
    return jwt.encode(payload, private_pem, algorithm="RS256")


def _valid_claims(user_id: uuid.UUID | None = None) -> dict[str, Any]:
    uid = user_id or uuid.uuid4()
    now = int(time.time())
    return {
        "sub": str(uid),
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + 3600,
        "role": "member",
    }


@pytest.fixture(scope="module")
def rsa_keypair() -> tuple[str, str]:
    """Module-scoped RSA key pair — generated once for all tests in this module."""
    return _make_rsa_keypair()


# ---------------------------------------------------------------------------
# Route guard tests — use GET /api/v1/auth/me as the protected route.
# We do NOT need a real DB user; a 404 means the JWT was accepted (guard passed).
# A 401 means the guard rejected the token.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestAuthCoreRouteGuard:
    """AuthCore RS256 tokens through the full FastAPI request pipeline."""

    async def test_valid_rs256_token_passes_route_guard(
        self,
        rsa_keypair: tuple[str, str],
    ) -> None:
        """A valid RS256 token signed with the configured key is accepted by get_current_user.

        We exercise the FastAPI dependency directly (not the full route stack) to avoid
        spinning up the DI container in the test environment. The guard either raises
        HTTPException(401) or returns a TokenPayload — we assert the latter.
        """
        from unittest.mock import MagicMock

        from fastapi import Request

        from pilot_space.dependencies.auth import get_current_user
        from pilot_space.dependencies.jwt_providers import AuthCoreJWTProvider
        from pilot_space.infrastructure.auth import TokenPayload

        private_pem, public_pem = rsa_keypair
        user_id = uuid.uuid4()
        token = _sign_rs256(_valid_claims(user_id), private_pem)

        provider = AuthCoreJWTProvider(public_key_pem=public_pem)

        # Build a minimal fake Request with the Authorization header.
        mock_request = MagicMock(spec=Request)
        mock_request.state = MagicMock()
        mock_request.state.user = None  # not pre-set by middleware
        mock_request.headers = {"Authorization": f"Bearer {token}"}

        with patch("pilot_space.dependencies.auth._jwt_provider", provider):
            result = get_current_user(mock_request)

        assert isinstance(result, TokenPayload)
        assert result.user_id == user_id

    async def test_expired_rs256_token_returns_401(
        self,
        client: AsyncClient,
        rsa_keypair: tuple[str, str],
    ) -> None:
        """An expired RS256 token is rejected with 401."""
        private_pem, public_pem = rsa_keypair
        claims = _valid_claims()
        claims["exp"] = int(time.time()) - 60  # already expired
        token = _sign_rs256(claims, private_pem)

        from pilot_space.dependencies.jwt_providers import AuthCoreJWTProvider

        provider = AuthCoreJWTProvider(public_key_pem=public_pem)

        with patch("pilot_space.dependencies.auth._jwt_provider", provider):
            response = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        body = response.json()
        assert "expired" in body.get("detail", "").lower()

    async def test_rs256_token_signed_with_wrong_key_returns_401(
        self,
        client: AsyncClient,
        rsa_keypair: tuple[str, str],
    ) -> None:
        """A token signed with a different private key is rejected with 401."""
        private_pem, _ = rsa_keypair
        _, different_public_pem = _make_rsa_keypair()  # different key pair
        token = _sign_rs256(_valid_claims(), private_pem)

        from pilot_space.dependencies.jwt_providers import AuthCoreJWTProvider

        provider = AuthCoreJWTProvider(public_key_pem=different_public_pem)

        with patch("pilot_space.dependencies.auth._jwt_provider", provider):
            response = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_missing_bearer_token_returns_401(
        self,
        client: AsyncClient,
        rsa_keypair: tuple[str, str],
    ) -> None:
        """Requests without Authorization header are rejected with 401."""
        _, public_pem = rsa_keypair

        from pilot_space.dependencies.jwt_providers import AuthCoreJWTProvider

        provider = AuthCoreJWTProvider(public_key_pem=public_pem)

        with patch("pilot_space.dependencies.auth._jwt_provider", provider):
            response = await client.get("/api/v1/auth/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_malformed_jwt_returns_401(
        self,
        client: AsyncClient,
        rsa_keypair: tuple[str, str],
    ) -> None:
        """A garbage string in the Authorization header returns 401."""
        _, public_pem = rsa_keypair

        from pilot_space.dependencies.jwt_providers import AuthCoreJWTProvider

        provider = AuthCoreJWTProvider(public_key_pem=public_pem)

        with patch("pilot_space.dependencies.auth._jwt_provider", provider):
            response = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": "Bearer not.a.real.token"},
            )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_rs256_token_with_missing_jti_claim_returns_401(
        self,
        client: AsyncClient,
        rsa_keypair: tuple[str, str],
    ) -> None:
        """A token without the required jti claim is rejected with 401."""
        private_pem, public_pem = rsa_keypair
        now = int(time.time())
        claims_without_jti = {
            "sub": str(uuid.uuid4()),
            "iat": now,
            "exp": now + 3600,
            "role": "member",
            # jti deliberately omitted
        }
        token = _sign_rs256(claims_without_jti, private_pem)

        from pilot_space.dependencies.jwt_providers import AuthCoreJWTProvider

        provider = AuthCoreJWTProvider(public_key_pem=public_pem)

        with patch("pilot_space.dependencies.auth._jwt_provider", provider):
            response = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# Startup validation: ValueError when authcore key is absent
# ---------------------------------------------------------------------------


class TestAuthCoreStartupValidation:
    """Startup fails fast when AUTH_PROVIDER=authcore + no AUTHCORE_PUBLIC_KEY."""

    def test_get_jwt_provider_raises_when_authcore_key_missing(self) -> None:
        """get_jwt_provider() raises ValueError for authcore with no public key."""
        from pilot_space.dependencies.jwt_providers import get_jwt_provider

        settings = MagicMock()
        settings.auth_provider = "authcore"
        settings.authcore_public_key = None

        with pytest.raises(ValueError, match="AUTHCORE_PUBLIC_KEY"):
            get_jwt_provider(settings)

    def test_get_jwt_provider_raises_when_authcore_key_is_empty_string(self) -> None:
        """get_jwt_provider() treats empty string as missing public key."""
        from pilot_space.dependencies.jwt_providers import get_jwt_provider

        settings = MagicMock()
        settings.auth_provider = "authcore"
        settings.authcore_public_key = ""

        with pytest.raises(ValueError, match="AUTHCORE_PUBLIC_KEY"):
            get_jwt_provider(settings)

    def test_get_jwt_provider_succeeds_when_authcore_key_present(
        self,
        rsa_keypair: tuple[str, str],
    ) -> None:
        """get_jwt_provider() returns DualJWTProvider when authcore key is set.

        DualJWTProvider wraps AuthCoreJWTProvider internally and accepts both
        Supabase and AuthCore tokens (dual-JWT support).
        """
        from pilot_space.dependencies.jwt_providers import (
            AuthCoreJWTProvider,
            DualJWTProvider,
            get_jwt_provider,
        )

        _, public_pem = rsa_keypair
        settings = MagicMock()
        settings.auth_provider = "authcore"
        settings.authcore_public_key = public_pem

        provider = get_jwt_provider(settings)
        # Returns DualJWTProvider which wraps AuthCoreJWTProvider internally
        assert isinstance(provider, DualJWTProvider)
        assert isinstance(provider._authcore, AuthCoreJWTProvider)
