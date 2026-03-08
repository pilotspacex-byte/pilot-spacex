"""TENANT-04: Super-admin operator dashboard API tests.

Router-level tests for the internal admin API:
- GET /api/v1/admin/workspaces — list all workspaces with metrics
- Authentication via super-admin token (not workspace JWT)
- Token must not appear in structured logs

All tests are xfail stubs pending Phase 3 plan 03-05 implementation:
- Admin router (backend/src/pilot_space/api/v1/routers/admin.py)
- Super-admin token validation (settings.SUPER_ADMIN_TOKEN)
- Log masking middleware for admin token header
"""

from __future__ import annotations

import pytest


@pytest.mark.xfail(strict=False, reason="TENANT-04: admin router not yet created")
async def test_admin_workspaces_requires_super_admin_token(client: object) -> None:
    """GET /api/v1/admin/workspaces without token returns 401.

    Unauthenticated requests (no Authorization header, or missing
    X-Super-Admin-Token header) must be rejected with HTTP 401.
    """
    raise NotImplementedError


@pytest.mark.xfail(strict=False, reason="TENANT-04: admin router not yet created")
async def test_invalid_super_admin_token_returns_401(client: object) -> None:
    """GET /api/v1/admin/workspaces with wrong token returns 401.

    Using a plausible-looking but incorrect token (e.g., "wrong-token-value")
    must return HTTP 401, not 403 (token is invalid, not insufficient permissions).
    """
    raise NotImplementedError


@pytest.mark.xfail(strict=False, reason="TENANT-04: admin router not yet created")
async def test_valid_super_admin_token_returns_workspace_list(client: object) -> None:
    """GET /api/v1/admin/workspaces with valid token returns list with metrics.

    Each workspace entry must include:
    - id, name, slug, created_at
    - member_count (integer)
    - storage_used_bytes (integer)
    - plan_tier (string)

    Assert: HTTP 200, response is a list, each item has required fields.
    """
    raise NotImplementedError


@pytest.mark.xfail(strict=False, reason="TENANT-04: super-admin token must not appear in logs")
async def test_super_admin_token_masked_in_logs() -> None:
    """Structured log entry for admin request shows token as '****', not plaintext.

    Log masking must occur before the log record is emitted to any handler.
    Assert: captured log output for an admin request does not contain the raw
    token value; appears as '****' or similar redaction marker.
    """
    raise NotImplementedError
