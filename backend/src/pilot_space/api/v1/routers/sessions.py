"""Workspace session management router — AUTH-06.

Provides admin endpoints for listing active sessions and force-terminating them.
Routes are mounted under /api/v1/workspaces/{workspace_id}/sessions.

Authentication: JWT with workspace admin or owner role.

Endpoints:
  GET    /{workspace_id}/sessions                   — list active sessions
  DELETE /{workspace_id}/sessions/{session_id}      — force-terminate single session
  DELETE /{workspace_id}/sessions/users/{user_id}   — terminate all sessions for a user
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from pilot_space.application.services.session_service import SessionDisplay

from fastapi import APIRouter, HTTPException, Request, status

from pilot_space.api.v1.schemas.sessions import SessionResponse, TerminateAllResponse
from pilot_space.application.services.session_service import SessionService
from pilot_space.dependencies.auth import CurrentUser, SessionDep, WorkspaceAdminId

router = APIRouter(tags=["sessions"])


def _get_session_service(request: Request, session: Any) -> SessionService:
    """Create SessionService using DI container redis client.

    Args:
        request: HTTP request for accessing app state container.
        session: Database session (AsyncSession).

    Returns:
        SessionService instance.
    """
    from pilot_space.infrastructure.auth.supabase_auth import SupabaseAuth
    from pilot_space.infrastructure.database.repositories.workspace_session_repository import (
        WorkspaceSessionRepository,
    )

    redis = None
    try:
        container = request.app.state.container
        redis = container.redis_client()
    except Exception:
        pass

    return SessionService(
        session_repo=WorkspaceSessionRepository(session),
        redis=redis,  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]
        supabase_admin_client=SupabaseAuth(),
    )


def _get_current_token_hash(request: Request) -> str | None:
    """Extract SHA-256 hash of the current request's bearer token.

    Args:
        request: HTTP request.

    Returns:
        Hex digest of the bearer token, or None if not present.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:]
    if not token:
        return None
    return hashlib.sha256(token.encode()).hexdigest()


def _display_to_response(
    display: SessionDisplay,
    *,
    is_current: bool,
) -> SessionResponse:
    """Convert SessionDisplay to SessionResponse.

    Args:
        display: Session display object.
        is_current: Whether this is the requesting user's current session.

    Returns:
        SessionResponse Pydantic model.
    """
    return SessionResponse(
        id=display.session_id,
        user_id=display.user_id,
        user_display_name=display.user_display_name,
        user_avatar_url=display.user_avatar_url,
        ip_address=display.ip_address,
        browser=display.browser,
        os=display.os,
        device=display.device,
        last_seen_at=display.last_seen_at,
        created_at=display.created_at,
        is_current=is_current,
    )


@router.get(
    "/{workspace_id}/sessions",
    response_model=list[SessionResponse],
    summary="List active workspace sessions",
)
async def list_sessions(
    workspace_id: UUID,
    request: Request,
    session: SessionDep,
    current_user: CurrentUser,
    _admin_id: WorkspaceAdminId,
) -> list[SessionResponse]:
    """List all active sessions for a workspace.

    Returns sessions ordered by last_seen_at DESC. The requesting user's
    current session is marked with is_current=True (matched by token hash).

    Requires workspace admin or owner role.

    Args:
        workspace_id: Workspace UUID.
        request: HTTP request for extracting current token hash.
        session: Database session.
        current_user: Authenticated user (admin/owner check via WorkspaceAdminId).
        _admin: Workspace admin authorization gate.
    """
    svc = _get_session_service(request, session)
    displays = await svc.list_sessions(workspace_id=workspace_id, db=session)
    current_hash = _get_current_token_hash(request)

    # Fetch token hashes to mark current session
    from pilot_space.infrastructure.database.repositories.workspace_session_repository import (
        WorkspaceSessionRepository,
    )

    repo = WorkspaceSessionRepository(session)
    responses: list[SessionResponse] = []
    for display in displays:
        # Check if this session matches the requesting token
        session_row = await repo.get_session_by_id(display.session_id, workspace_id)
        is_current = (
            current_hash is not None
            and session_row is not None
            and session_row.session_token_hash == current_hash
        )
        responses.append(_display_to_response(display, is_current=is_current))

    return responses


@router.delete(
    "/{workspace_id}/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Force-terminate a single session",
)
async def force_terminate_session(
    workspace_id: UUID,
    session_id: UUID,
    request: Request,
    session: SessionDep,
    current_user: CurrentUser,
    _admin_id: WorkspaceAdminId,
) -> None:
    """Force-terminate a single active workspace session.

    Sets revoked_at in the DB and writes a revocation key to Redis so that
    subsequent requests using the same token receive 401 immediately.

    An admin cannot terminate their own current session.

    Requires workspace admin or owner role.

    Args:
        workspace_id: Workspace UUID.
        session_id: Session UUID to terminate.
        request: HTTP request for detecting own session.
        session: Database session.
        current_user: Authenticated user.
        _admin: Workspace admin authorization gate.

    Raises:
        HTTPException: 403 if attempting to terminate own active session.
        HTTPException: 404 if session not found.
    """
    from pilot_space.infrastructure.database.repositories.workspace_session_repository import (
        WorkspaceSessionRepository,
    )

    repo = WorkspaceSessionRepository(session)

    # Verify session exists before checking if it is the current one
    target_session = await repo.get_session_by_id(session_id, workspace_id)
    if target_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    # Prevent admin from terminating their own session via this endpoint
    current_hash = _get_current_token_hash(request)
    if current_hash and target_session.session_token_hash == current_hash:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot terminate your own active session",
        )

    svc = _get_session_service(request, session)
    await svc.force_terminate(
        session_id=session_id,
        workspace_id=workspace_id,
        db=session,
    )


@router.delete(
    "/{workspace_id}/sessions/users/{user_id}",
    response_model=TerminateAllResponse,
    summary="Terminate all sessions for a user",
)
async def terminate_user_sessions(
    workspace_id: UUID,
    user_id: UUID,
    request: Request,
    session: SessionDep,
    current_user: CurrentUser,
    _admin_id: WorkspaceAdminId,
) -> TerminateAllResponse:
    """Terminate all active sessions for a specific workspace member.

    Revokes all sessions in DB, writes revocation keys to Redis, and calls
    Supabase auth.admin.sign_out with global scope for hard token invalidation.

    Requires workspace admin or owner role.

    Args:
        workspace_id: Workspace UUID.
        user_id: UUID of the user whose sessions to terminate.
        request: HTTP request.
        session: Database session.
        current_user: Authenticated user.
        _admin: Workspace admin authorization gate.

    Returns:
        TerminateAllResponse with count of terminated sessions.
    """
    svc = _get_session_service(request, session)
    count = await svc.terminate_all_for_user(
        user_id=user_id,
        workspace_id=workspace_id,
        db=session,
    )
    return TerminateAllResponse(terminated=count)
