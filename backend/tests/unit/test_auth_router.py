"""Test auth router endpoints (T011).

Verifies removed 501 endpoints are gone (RD-002):
- POST /callback removed
- POST /refresh removed
"""

from __future__ import annotations

from pilot_space.api.v1.routers.auth import router


def _get_route_paths() -> set[str]:
    """Extract all registered route paths from the auth router."""
    return {route.path for route in router.routes}


def test_auth_router_has_login_endpoint() -> None:
    """Verify /auth/login endpoint is registered."""
    assert "/auth/login" in _get_route_paths()


def test_auth_router_has_me_endpoint() -> None:
    """Verify /auth/me endpoint is registered."""
    assert "/auth/me" in _get_route_paths()


def test_auth_router_has_logout_endpoint() -> None:
    """Verify /auth/logout endpoint is registered."""
    assert "/auth/logout" in _get_route_paths()


def test_auth_router_no_callback_endpoint() -> None:
    """Verify /auth/callback endpoint was removed (RD-002)."""
    assert "/auth/callback" not in _get_route_paths()


def test_auth_router_no_refresh_endpoint() -> None:
    """Verify /auth/refresh endpoint was removed (RD-002)."""
    assert "/auth/refresh" not in _get_route_paths()


def test_auth_router_has_config_endpoint() -> None:
    """Verify /auth/config endpoint is registered (US-03: frontend auth routing)."""
    assert "/auth/config" in _get_route_paths()


def test_auth_router_expected_route_count() -> None:
    """Verify auth router has exactly the expected number of routes.

    Expected: /auth/login (GET), /auth/me (GET, PATCH), /auth/logout (POST),
              /auth/config (GET — JWT provider config for frontend),
              /auth/validate-key (POST — CLI API key validation),
              /auth/complete-signup (POST — new user signup completion, S012).
    """
    paths = _get_route_paths()
    expected_paths = {
        "/auth/login",
        "/auth/me",
        "/auth/logout",
        "/auth/config",
        "/auth/validate-key",
        "/auth/complete-signup",
    }
    assert paths == expected_paths
