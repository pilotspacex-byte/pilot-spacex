"""Authentication and authorization dependencies.

Provides request-scoped dependencies for token validation, user identity,
workspace membership checks, and user sync.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextvars import ContextVar
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.infrastructure.auth import (
    SupabaseAuth,
    SupabaseAuthError,
    TokenExpiredError,
    TokenPayload,
)
from pilot_space.infrastructure.database.engine import get_db_session
from pilot_space.infrastructure.logging import get_logger

# Singleton auth instance
_auth: SupabaseAuth | None = None

# Request-scoped session context (for dependency-injector integration)
# Pattern from FastAPI docs: https://fastapi.tiangolo.com/ko/release-notes
_request_session_ctx: ContextVar[AsyncSession | None] = ContextVar("request_session", default=None)


def get_auth() -> SupabaseAuth:
    """Get Supabase Auth instance (singleton).

    Returns:
        SupabaseAuth instance.
    """
    global _auth  # noqa: PLW0603
    if _auth is None:
        _auth = SupabaseAuth()
    return _auth


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session dependency with ContextVar injection.

    Provides session for FastAPI Depends() while also injecting it into
    ContextVar for dependency-injector Factory providers to access.

    Pattern from FastAPI best practices:
    - Uses ContextVar for request-scoped state (async-safe)
    - Token reset in finally block prevents memory leaks
    - Ensures proper cleanup even if exceptions occur

    Yields:
        AsyncSession for database operations.
    """
    async with get_db_session() as session:
        # Set session in context for container providers
        token = _request_session_ctx.set(session)
        try:
            yield session
        finally:
            # Always reset context var to avoid leaks
            _request_session_ctx.reset(token)


def get_current_session() -> AsyncSession:
    """Get session from current request context.

    Used by dependency-injector Factory providers to resolve session
    dependencies without explicit FastAPI Depends() injection.

    Returns:
        AsyncSession from current request context.

    Raises:
        RuntimeError: If no session in current context (get_session not called).
    """
    session = _request_session_ctx.get()
    if session is None:
        raise RuntimeError(
            "No session in current context. "
            "Ensure get_session() dependency is called first in the route handler."
        )
    return session


def get_token_from_header(request: Request) -> str:
    """Extract Bearer token from Authorization header.

    Args:
        request: The current request.

    Returns:
        The JWT token.

    Raises:
        HTTPException: If token is missing or malformed.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Use: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return parts[1]


def get_current_user(
    request: Request,
    auth: Annotated[SupabaseAuth, Depends(get_auth)],
) -> TokenPayload:
    """Get current authenticated user from request.

    First checks request.state (set by middleware), then validates token.

    Args:
        request: The current request.
        auth: Supabase Auth instance.

    Returns:
        Validated token payload with user info.

    Raises:
        HTTPException: If not authenticated or token invalid.
    """
    # Check if already validated by middleware
    user = getattr(request.state, "user", None)
    if user is not None:
        return user  # type: ignore[no-any-return]

    # Validate token manually (for routes without middleware)
    token = get_token_from_header(request)
    try:
        return auth.validate_token(token)
    except TokenExpiredError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except SupabaseAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


def get_current_user_id(
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
) -> UUID:
    """Get current user ID.

    Args:
        current_user: The validated token payload.

    Returns:
        User UUID.
    """
    return current_user.user_id


async def require_workspace_member(
    workspace_id: UUID,
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UUID:
    """Require user to be a workspace member.

    Queries workspace_members table to verify membership.
    AI endpoints bypass RLS (using Redis/in-memory), so this
    explicit check is required for authorization.

    Args:
        workspace_id: The workspace being accessed.
        current_user: The validated token payload.
        session: Database session.

    Returns:
        Workspace ID on success.

    Raises:
        HTTPException: 403 if user is not a workspace member.
    """
    user_id = current_user.user_id

    from sqlalchemy import exists, select

    from pilot_space.infrastructure.database.models.workspace_member import (
        WorkspaceMember,
    )
    from pilot_space.infrastructure.database.rls import set_rls_context

    await set_rls_context(session, user_id, workspace_id)

    stmt = select(
        exists().where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
    )
    result = await session.execute(stmt)
    is_member = result.scalar()

    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )
    return workspace_id


async def require_workspace_admin(
    workspace_id: UUID,
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UUID:
    """Require user to be a workspace admin or owner.

    Args:
        workspace_id: The workspace being accessed.
        current_user: The validated token payload.
        session: Database session.

    Returns:
        Workspace ID on success.

    Raises:
        HTTPException: 403 if user is not an admin/owner.
    """
    user_id = current_user.user_id

    from sqlalchemy import select

    from pilot_space.infrastructure.database.models.workspace_member import (
        WorkspaceMember,
        WorkspaceRole,
    )

    stmt = select(WorkspaceMember.role).where(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id,
    )
    result = await session.execute(stmt)
    role = result.scalar()

    if role not in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return workspace_id


# Type aliases for cleaner dependency injection
CurrentUser = Annotated[TokenPayload, Depends(get_current_user)]
CurrentUserId = Annotated[UUID, Depends(get_current_user_id)]
DbSession = Annotated[AsyncSession, Depends(get_session)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]
WorkspaceMemberId = Annotated[UUID, Depends(require_workspace_member)]
WorkspaceAdminId = Annotated[UUID, Depends(require_workspace_admin)]


# ============================================================================
# User Sync Dependencies
# ============================================================================


async def ensure_user_synced(
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UUID:
    """Ensure authenticated user exists in the local database.

    Syncs user from Supabase Auth to local users table on first access.
    This is necessary because Supabase Auth and local DB are separate.

    Args:
        current_user: The validated token payload from Supabase Auth.
        session: Database session.

    Returns:
        User UUID (synced to local DB).
    """
    from sqlalchemy.exc import IntegrityError

    from pilot_space.infrastructure.database.models.user import User
    from pilot_space.infrastructure.database.repositories.invitation_repository import (
        InvitationRepository,
    )
    from pilot_space.infrastructure.database.repositories.user_repository import (
        UserRepository,
    )
    from pilot_space.infrastructure.database.repositories.workspace_repository import (
        WorkspaceRepository,
    )

    logger = get_logger(__name__)
    user_repo = UserRepository(session=session)

    # Check if user exists by ID (scalar-only, no relationship loading)
    existing = await user_repo.get_by_id_scalar(current_user.user_id)
    if existing:
        return current_user.user_id

    # User doesn't exist - create from JWT claims
    email = current_user.email or f"user-{current_user.user_id}@placeholder.local"
    user = User(
        id=current_user.user_id,
        email=email,
        full_name=None,
        avatar_url=None,
    )
    try:
        await user_repo.create(user)
    except IntegrityError:
        # Concurrent request already created this user (race condition)
        await session.rollback()
        existing = await user_repo.get_by_id_scalar(current_user.user_id)
        if existing:
            return current_user.user_id
        raise

    # Auto-accept pending invitations for this email (FR-016, RD-004)
    invitation_repo = InvitationRepository(session=session)
    workspace_repo = WorkspaceRepository(session=session)
    pending_invitations = await invitation_repo.get_pending_by_email(email)
    for invitation in pending_invitations:
        try:
            await workspace_repo.add_member(
                workspace_id=invitation.workspace_id,
                user_id=user.id,
                role=invitation.role,
            )
            await invitation_repo.mark_accepted(invitation.id)
            logger.info(
                "Auto-accepted invitation %s for user %s to workspace %s",
                invitation.id,
                user.id,
                invitation.workspace_id,
            )
        except Exception:
            logger.exception(
                "Failed to auto-accept invitation %s for user %s to workspace %s",
                invitation.id,
                user.id,
                invitation.workspace_id,
            )

    await session.commit()

    return current_user.user_id


# Dependency that ensures user is synced before operations requiring owner_id
SyncedUserId = Annotated[UUID, Depends(ensure_user_synced)]
