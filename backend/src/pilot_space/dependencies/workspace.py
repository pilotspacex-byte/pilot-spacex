"""Workspace context dependencies.

Provides request-scoped dependencies for workspace identification
and database session pass-through.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.dependencies.auth import DEMO_WORKSPACE_SLUGS, get_session

# Demo workspace UUID for slug-based workspace IDs
DEMO_WORKSPACE_UUID = UUID("00000000-0000-0000-0000-000000000002")


def get_current_workspace_id(request: Request) -> UUID:
    """Get current workspace ID from request state or header.

    Checks in order:
    1. request.state.workspace_id (set by middleware)
    2. X-Workspace-Id header
    3. X-Workspace-ID header (alternative casing)

    Supports demo workspace slugs in development mode.

    Args:
        request: The current request.

    Returns:
        Workspace UUID.

    Raises:
        HTTPException: If workspace ID not found.
    """
    from pilot_space.config import get_settings

    settings = get_settings()

    # First check request.state (set by middleware)
    workspace_id = getattr(request.state, "workspace_id", None)
    if workspace_id is not None:
        return workspace_id

    # Fallback to header (case-insensitive check)
    header_value = request.headers.get("X-Workspace-Id") or request.headers.get("X-Workspace-ID")
    if header_value:
        # Check for demo workspace slugs in development mode
        if settings.app_env in ("development", "test"):
            if header_value.lower() in DEMO_WORKSPACE_SLUGS:
                request.state.workspace_id = DEMO_WORKSPACE_UUID
                return DEMO_WORKSPACE_UUID

        try:
            workspace_id = UUID(header_value)
            # Store in request.state for subsequent use
            request.state.workspace_id = workspace_id
            return workspace_id
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid workspace ID format: {header_value}",
            ) from e

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Workspace context not established. Provide X-Workspace-Id header.",
    )


def get_db_session_dep(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AsyncSession:
    """Get database session for dependency injection.

    Args:
        session: Database session from get_session.

    Returns:
        AsyncSession for database operations.
    """
    return session
