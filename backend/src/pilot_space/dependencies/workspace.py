"""Workspace context dependencies.

Provides request-scoped dependencies for workspace identification,
membership enforcement, and database session pass-through.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.dependencies.auth import get_current_user, get_session
from pilot_space.infrastructure.auth import TokenPayload


def get_current_workspace_id(request: Request) -> UUID:
    """Get current workspace ID from request state or header.

    Checks in order:
    1. request.state.workspace_id (set by middleware)
    2. X-Workspace-Id header
    3. X-Workspace-ID header (alternative casing)

    Args:
        request: The current request.

    Returns:
        Workspace UUID.

    Raises:
        HTTPException: If workspace ID not found.
    """
    # First check request.state (set by middleware)
    workspace_id = getattr(request.state, "workspace_id", None)
    if workspace_id is not None:
        return workspace_id

    # Fallback to header (case-insensitive check)
    header_value = request.headers.get("X-Workspace-Id") or request.headers.get("X-Workspace-ID")
    if header_value:
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


async def require_header_workspace_member(
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UUID:
    """Require workspace membership using workspace ID from X-Workspace-Id header.

    Combines get_current_workspace_id (header extraction) with membership
    verification and RLS context setup. Use for routes that receive the
    workspace ID via header rather than path parameter.

    Args:
        workspace_id: Workspace UUID from X-Workspace-Id header.
        current_user: Authenticated user from JWT.
        session: Database session.

    Returns:
        Workspace UUID on success.

    Raises:
        HTTPException: 403 if user is not a workspace member.
    """
    from sqlalchemy import exists, select

    from pilot_space.infrastructure.database.models.workspace_member import (
        WorkspaceMember,
    )
    from pilot_space.infrastructure.database.rls import set_rls_context

    user_id = current_user.user_id
    await set_rls_context(session, user_id, workspace_id)

    is_member = (
        await session.execute(
            select(
                exists().where(
                    WorkspaceMember.workspace_id == workspace_id,
                    WorkspaceMember.user_id == user_id,
                    WorkspaceMember.is_deleted == False,  # noqa: E712
                )
            )
        )
    ).scalar()

    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )
    return workspace_id


# Type alias for header-based workspace membership dependency
HeaderWorkspaceMemberId = Annotated[UUID, Depends(require_header_workspace_member)]


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
