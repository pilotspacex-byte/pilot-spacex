"""Super-admin bearer token dependency.

Completely separate from Supabase JWT auth. Used exclusively by /api/v1/admin/* routes.
The token is a deployment-time env var (PILOT_SPACE_SUPER_ADMIN_TOKEN), not a DB record.

The token is validated as a SecretStr — its value is never logged or exposed in repr().

Usage:
    @router.get("/workspaces")
    async def list_workspaces(_: Annotated[None, Depends(get_super_admin)]) -> ...:
        ...
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from pilot_space.config import get_settings

# auto_error=False so we can return 401 with WWW-Authenticate header
# instead of FastAPI's default 403 for missing schemes.
_bearer = HTTPBearer(auto_error=False)


async def get_super_admin(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> None:
    """Validate super-admin bearer token.

    Returns None on success. Raises HTTP 401 on:
    - Missing Authorization header
    - Wrong token value
    - PILOT_SPACE_SUPER_ADMIN_TOKEN not configured (None)

    Args:
        credentials: Bearer token from Authorization header (None if absent).

    Raises:
        HTTPException: 401 if token is missing, invalid, or super-admin is unconfigured.
    """
    settings = get_settings()
    expected = settings.pilot_space_super_admin_token

    if credentials is None or expected is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Super-admin access requires a valid PILOT_SPACE_SUPER_ADMIN_TOKEN",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if credentials.credentials != expected.get_secret_value():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid super-admin token",
            headers={"WWW-Authenticate": "Bearer"},
        )
