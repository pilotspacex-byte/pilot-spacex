"""HTTP-level integration tests for AuthCore FastAPI routers.

Exercises the full ASGI stack via httpx.AsyncClient + ASGITransport
against a real FastAPI app wired to SQLite in-memory + stub Redis.
No real PostgreSQL or Redis required.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from authcore.config import Settings
from authcore.infrastructure.cache.redis_client import RedisClient
from authcore.infrastructure.database.base import Base
from authcore.infrastructure.database.models.audit_log import AuditLogModel  # noqa: F401
from authcore.infrastructure.database.models.refresh_token import RefreshTokenModel  # noqa: F401
from authcore.infrastructure.database.models.user import UserModel  # noqa: F401
from authcore.infrastructure.tokens.jwt_service import JWTService
from authcore.infrastructure.tokens.key_manager import KeyManager

_VERIFY_PREFIX = "authcore:verify:"


# ---------------------------------------------------------------------------
# In-memory Redis stub
# ---------------------------------------------------------------------------

class _StubRedis(RedisClient):
    def __init__(self) -> None:  # type: ignore[override]
        self._store: dict[str, str] = {}
        self._ttls: dict[str, int] = {}

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        self._store[key] = value
        if ex is not None:
            self._ttls[key] = ex
        return True

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def delete(self, key: str) -> bool:
        self._store.pop(key, None)
        self._ttls.pop(key, None)
        return True

    async def exists(self, key: str) -> bool:
        return key in self._store

    async def incr(self, key: str) -> int:
        current = int(self._store.get(key, "0"))
        new_val = current + 1
        self._store[key] = str(new_val)
        return new_val

    async def expire(self, key: str, seconds: int) -> None:
        self._ttls[key] = seconds

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Module-scoped SQLite engine
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="module")
async def _api_engine() -> AsyncGenerator[AsyncEngine, None]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture(scope="module")
def stub_redis() -> _StubRedis:
    """Shared in-memory Redis stub — accessible to tests for token extraction."""
    return _StubRedis()


# ---------------------------------------------------------------------------
# Main fixture: override Container providers + yield AsyncClient
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="module")
async def client(
    _api_engine: AsyncEngine,
    settings: Settings,
    stub_redis: _StubRedis,
) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient pointed at the full ASGI app with test DI overrides."""
    import authcore.main as main_module
    from authcore.container.container import Container

    stub_email = AsyncMock()
    session_factory = async_sessionmaker(
        _api_engine, expire_on_commit=False, class_=AsyncSession
    )
    key_manager = KeyManager(settings)
    jwt_svc = JWTService(key_manager, settings)

    container = Container()
    container.config.override(settings)  # type: ignore[misc]
    container.infra.db_engine.override(_api_engine)  # type: ignore[misc]
    container.infra.session_factory.override(session_factory)  # type: ignore[misc]
    container.infra.redis_client.override(stub_redis)  # type: ignore[misc]
    container.infra.jwt_service.override(jwt_svc)  # type: ignore[misc]
    container.infra.email_service.override(stub_email)  # type: ignore[misc]

    original_container = main_module._container
    main_module._container = container  # type: ignore[attr-defined]

    app = main_module.create_app()

    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    main_module._container = original_container  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Helper: register + verify email + login
# ---------------------------------------------------------------------------

async def _register_and_login(
    client: AsyncClient,
    stub_redis: _StubRedis,
    email: str,
    password: str = "Secure1!",
) -> dict[str, str]:
    """Register a user, verify their email via stub Redis token, then login."""
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert reg.status_code == 201, reg.text

    # Extract the most-recently added verification token from stub Redis
    verify_token = next(
        (k.removeprefix(_VERIFY_PREFIX) for k in stub_redis._store if k.startswith(_VERIFY_PREFIX)),
        None,
    )
    assert verify_token is not None, "No verification token found in stub Redis after register"
    verify_resp = await client.get(f"/api/v1/auth/verify-email?token={verify_token}")
    assert verify_resp.status_code == 200, verify_resp.text
    # Remove the consumed token so subsequent calls find the right one
    stub_redis._store.pop(f"{_VERIFY_PREFIX}{verify_token}", None)

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, login.text
    data = login.json()
    return {
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "user_id": str(data["user_id"]),
    }


# ---------------------------------------------------------------------------
# Health endpoints
# ---------------------------------------------------------------------------

class TestHealthEndpoints:
    async def test_health_returns_ok(self, client: AsyncClient) -> None:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    async def test_health_live_returns_ok(self, client: AsyncClient) -> None:
        resp = await client.get("/health/live")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    async def test_health_ready_returns_ready(self, client: AsyncClient) -> None:
        resp = await client.get("/health/ready")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ready"}


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------

class TestRegisterEndpoint:
    async def test_register_success(self, client: AsyncClient, stub_redis: _StubRedis) -> None:
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "reg_ok@test.com", "password": "Secure1!"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["email"] == "reg_ok@test.com"
        assert "user_id" in body
        # Clean up verification token so it doesn't affect other tests
        for k in list(stub_redis._store.keys()):
            if k.startswith(_VERIFY_PREFIX):
                stub_redis._store.pop(k, None)

    async def test_register_duplicate_email_returns_409(
        self, client: AsyncClient, stub_redis: _StubRedis
    ) -> None:
        await client.post(
            "/api/v1/auth/register",
            json={"email": "dup_api@test.com", "password": "Secure1!"},
        )
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "dup_api@test.com", "password": "Secure1!"},
        )
        assert resp.status_code == 409
        # Clean up
        for k in list(stub_redis._store.keys()):
            if k.startswith(_VERIFY_PREFIX):
                stub_redis._store.pop(k, None)

    async def test_register_weak_password_returns_400_or_422(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "weak_api@test.com", "password": "abc"},
        )
        assert resp.status_code in (400, 422)


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

class TestLoginEndpoint:
    async def test_login_success(self, client: AsyncClient, stub_redis: _StubRedis) -> None:
        tokens = await _register_and_login(client, stub_redis, "login_ok@test.com")
        assert tokens["access_token"]
        assert tokens["refresh_token"]

    async def test_login_wrong_password_returns_401(
        self, client: AsyncClient, stub_redis: _StubRedis
    ) -> None:
        # Register + verify first
        await _register_and_login(client, stub_redis, "login_bad@test.com")
        # Attempt login with wrong password
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "login_bad@test.com", "password": "WrongPass1!"},
        )
        assert resp.status_code == 401

    async def test_login_unknown_email_returns_401(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@test.com", "password": "Secure1!"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Refresh token
# ---------------------------------------------------------------------------

class TestRefreshEndpoint:
    async def test_refresh_success(self, client: AsyncClient, stub_redis: _StubRedis) -> None:
        tokens = await _register_and_login(client, stub_redis, "refresh_ok@test.com")
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body

    async def test_refresh_invalid_token_returns_4xx(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "not.a.valid.token"},
        )
        assert resp.status_code in (400, 401, 422)


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

class TestLogoutEndpoint:
    async def test_logout_success(self, client: AsyncClient, stub_redis: _StubRedis) -> None:
        tokens = await _register_and_login(client, stub_redis, "logout_ok@test.com")
        resp = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "Logged out successfully"

    async def test_logout_without_auth_returns_401_or_403(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": "any"},
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Logout all
# ---------------------------------------------------------------------------

class TestLogoutAllEndpoint:
    async def test_logout_all_success(self, client: AsyncClient, stub_redis: _StubRedis) -> None:
        tokens = await _register_and_login(client, stub_redis, "logall_ok@test.com")
        resp = await client.post(
            "/api/v1/auth/logout-all",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "All sessions revoked"

    async def test_logout_all_unauthenticated_returns_401_or_403(
        self, client: AsyncClient
    ) -> None:
        resp = await client.post("/api/v1/auth/logout-all")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Change password
# ---------------------------------------------------------------------------

class TestChangePasswordEndpoint:
    async def test_change_password_success(
        self, client: AsyncClient, stub_redis: _StubRedis
    ) -> None:
        tokens = await _register_and_login(client, stub_redis, "chpw_ok@test.com")
        resp = await client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json={"current_password": "Secure1!", "new_password": "NewSecure2@"},
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "Password changed successfully"

    async def test_change_password_wrong_current_returns_401(
        self, client: AsyncClient, stub_redis: _StubRedis
    ) -> None:
        tokens = await _register_and_login(client, stub_redis, "chpw_bad@test.com")
        resp = await client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json={"current_password": "WrongOld1!", "new_password": "NewSecure2@"},
        )
        assert resp.status_code in (400, 401)

    async def test_change_password_unauthenticated_returns_401_or_403(
        self, client: AsyncClient
    ) -> None:
        resp = await client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "Secure1!", "new_password": "NewSecure2@"},
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Verify email
# ---------------------------------------------------------------------------

class TestVerifyEmailEndpoint:
    async def test_verify_email_invalid_token_returns_400_or_404(
        self, client: AsyncClient
    ) -> None:
        resp = await client.get("/api/v1/auth/verify-email?token=bad_token_xyz")
        assert resp.status_code in (400, 404)

    async def test_verify_email_missing_token_param_returns_422(
        self, client: AsyncClient
    ) -> None:
        resp = await client.get("/api/v1/auth/verify-email")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Forgot password
# ---------------------------------------------------------------------------

class TestForgotPasswordEndpoint:
    async def test_forgot_password_unknown_email_returns_200(self, client: AsyncClient) -> None:
        # Anti-enumeration: always 200 regardless of whether email exists
        resp = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nobody_forgot@test.com"},
        )
        assert resp.status_code == 200

    async def test_forgot_password_known_email_returns_200(
        self, client: AsyncClient, stub_redis: _StubRedis
    ) -> None:
        await _register_and_login(client, stub_redis, "forgot_known@test.com")
        resp = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "forgot_known@test.com"},
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Admin: audit logs
# ---------------------------------------------------------------------------

class TestAdminAuditLogsEndpoint:
    async def test_audit_logs_non_admin_returns_403(
        self, client: AsyncClient, stub_redis: _StubRedis
    ) -> None:
        tokens = await _register_and_login(client, stub_redis, "audit_member@test.com")
        resp = await client.get(
            f"/api/v1/admin/users/{tokens['user_id']}/audit-logs",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert resp.status_code == 403

    async def test_audit_logs_unauthenticated_returns_401_or_403(
        self, client: AsyncClient
    ) -> None:
        resp = await client.get(f"/api/v1/admin/users/{uuid.uuid4()}/audit-logs")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Admin: change role
# ---------------------------------------------------------------------------

class TestAdminChangeRoleEndpoint:
    async def test_change_role_non_admin_returns_403(
        self, client: AsyncClient, stub_redis: _StubRedis
    ) -> None:
        tokens = await _register_and_login(client, stub_redis, "role_member@test.com")
        resp = await client.put(
            f"/api/v1/admin/users/{tokens['user_id']}/role",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json={"new_role": "admin"},
        )
        assert resp.status_code == 403

    async def test_change_role_unauthenticated_returns_401_or_403(
        self, client: AsyncClient
    ) -> None:
        resp = await client.put(
            f"/api/v1/admin/users/{uuid.uuid4()}/role",
            json={"new_role": "admin"},
        )
        assert resp.status_code in (401, 403)
