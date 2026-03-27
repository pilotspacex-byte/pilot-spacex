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

from pilot_space.config import get_settings
from pilot_space.dependencies.jwt_providers import (
    JWTExpiredError,
    JWTProvider,
    JWTValidationError,
    get_jwt_provider,
)
from pilot_space.infrastructure.auth import SupabaseAuth, TokenPayload
from pilot_space.infrastructure.database.engine import get_db_session
from pilot_space.infrastructure.logging import get_logger

# Singleton auth instance (Supabase; kept for backward compat with callers that
# depend on get_auth() or use TokenPayload directly, e.g. ensure_user_synced).
_auth: SupabaseAuth | None = None

# Singleton JWT provider (provider-agnostic, used by get_current_user_id).
_jwt_provider: JWTProvider | None = None

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


def _get_jwt_provider() -> JWTProvider:
    """Get the configured JWT provider singleton.

    Provider is chosen by settings.auth_provider (default: "supabase").
    Also used by WebSocket endpoints that cannot use FastAPI Depends()
    for token validation (e.g. transcription_ws.py).

    Returns:
        JWTProvider implementation.
    """
    global _jwt_provider  # noqa: PLW0603
    if _jwt_provider is None:
        _jwt_provider = get_jwt_provider(get_settings())
    return _jwt_provider


def verify_token(raw_token: str) -> TokenPayload:
    """Verify a JWT token and return the payload.

    Public accessor for WebSocket endpoints that receive the token as a
    query parameter instead of an Authorization header.

    Args:
        raw_token: Raw JWT string.

    Returns:
        Validated TokenPayload.

    Raises:
        JWTExpiredError: If token is expired.
        JWTValidationError: If token is invalid.
    """
    return _get_jwt_provider().verify_token(raw_token)


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
) -> TokenPayload:
    """Get current authenticated user from request.

    First checks request.state (set by middleware), then validates token
    via the configured JWT provider (Supabase default, or AuthCore when
    AUTH_PROVIDER=authcore).

    Args:
        request: The current request.

    Returns:
        Validated token payload with user info.

    Raises:
        HTTPException: If not authenticated or token invalid.
    """
    # Check if already validated by middleware
    user = getattr(request.state, "user", None)
    if user is not None:
        return user  # type: ignore[no-any-return]

    token = get_token_from_header(request)
    provider = _get_jwt_provider()
    try:
        return provider.verify_token(token)
    except JWTExpiredError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except JWTValidationError as e:
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
            WorkspaceMember.is_deleted == False,  # noqa: E712
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
    from pilot_space.infrastructure.database.rls import set_rls_context

    await set_rls_context(session, user_id, workspace_id)

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

    # Commit user row immediately so it is visible to all subsequent operations,
    # including workspace creation requests that may arrive in parallel.
    # Invitation acceptance runs in a separate transaction below so any failure
    # (e.g. RLS policy violation on project_members after migration 101) cannot
    # roll back the user row.
    await session.commit()

    # Auto-accept pending invitations for this email (FR-016, RD-004)
    invitation_repo = InvitationRepository(session=session)
    workspace_repo = WorkspaceRepository(session=session)
    pending_invitations = await invitation_repo.get_pending_by_email(email)
    for invitation in pending_invitations:
        # Use a SAVEPOINT for each invitation so that a DB-level failure
        # (e.g. RLS violation on workspace_members or project_members) rolls
        # back only this invitation and leaves the outer transaction intact.
        try:
            async with session.begin_nested():
                # Set RLS context to the inviting admin/owner before any INSERT.
                # Both workspace_members_admin and project_members_insert policies
                # require app.current_user_id to be a workspace admin/owner.
                from pilot_space.infrastructure.database.rls import set_rls_context

                if invitation.invited_by:
                    await set_rls_context(session, invitation.invited_by)
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
                # FR-03: Materialize project assignments stored on the invitation.
                # materialize_invite_assignments uses per-entry SAVEPOINTs
                # internally, so partial failures are isolated and do not abort
                # the outer transaction.
                if invitation.project_assignments:
                    from pilot_space.application.services.project_member import (
                        InviteAssignmentsPayload,
                        ProjectMemberService,
                    )
                    from pilot_space.infrastructure.database.repositories.project_member import (
                        ProjectMemberRepository,
                    )

                    pm_repo = ProjectMemberRepository(session=session)
                    pm_svc = ProjectMemberService(project_member_repository=pm_repo)
                    count = await pm_svc.materialize_invite_assignments(
                        InviteAssignmentsPayload(
                            workspace_id=invitation.workspace_id,
                            user_id=user.id,
                            assigned_by=invitation.invited_by,
                            project_assignments=invitation.project_assignments,
                        )
                    )
                    if count:
                        logger.info(
                            "Materialized %d project assignments for user %s from invitation %s",
                            count,
                            user.id,
                            invitation.id,
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
