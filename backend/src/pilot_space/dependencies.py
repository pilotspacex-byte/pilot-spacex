"""FastAPI dependency injection.

Provides request-scoped dependencies for authentication, database, and services.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Annotated
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

# Singleton auth instance
_auth: SupabaseAuth | None = None


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
    """Get database session dependency.

    Yields:
        AsyncSession for database operations.
    """
    async with get_db_session() as session:
        yield session


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


def require_workspace_member(
    workspace_id: UUID,
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
) -> UUID:
    """Require user to be a workspace member.

    Note: Actual membership verification happens via RLS at database level.
    This dependency ensures user is authenticated before workspace access.

    Args:
        workspace_id: The workspace being accessed.
        current_user: The validated token payload.

    Returns:
        Workspace ID (passed through for use in handlers).
    """
    # Authentication is verified by get_current_user
    # RLS policies will enforce workspace membership at DB level
    return workspace_id


# Demo user ID for development/testing
DEMO_USER_ID = UUID("00000000-0000-0000-0000-000000000001")
DEMO_WORKSPACE_SLUGS = {"pilot-space-demo", "demo", "test"}


def get_current_user_id_or_demo(
    request: Request,
    auth: Annotated[SupabaseAuth, Depends(get_auth)],
) -> UUID:
    """Get current user ID with demo mode fallback.

    In development mode with demo workspaces, allows unauthenticated access
    using a fixed demo user ID. This enables testing without full auth setup.

    Args:
        request: The current request.
        auth: Supabase Auth instance.

    Returns:
        User UUID (real or demo).

    Raises:
        HTTPException: If not authenticated in production.
    """
    from pilot_space.config import get_settings

    settings = get_settings()

    # Check if demo mode is allowed
    if settings.app_env in ("development", "test"):
        workspace_slug = request.headers.get("X-Workspace-Id", "")
        if workspace_slug in DEMO_WORKSPACE_SLUGS:
            return DEMO_USER_ID

    # Check if already validated by middleware
    user = getattr(request.state, "user", None)
    if user is not None:
        return user.user_id  # type: ignore[no-any-return]

    # Validate token manually
    try:
        token = get_token_from_header(request)
        payload = auth.validate_token(token)
        return payload.user_id
    except HTTPException:
        # In development, fall back to demo user if no auth header
        if settings.app_env in ("development", "test"):
            return DEMO_USER_ID
        raise


# Type aliases for cleaner dependency injection
CurrentUser = Annotated[TokenPayload, Depends(get_current_user)]
CurrentUserId = Annotated[UUID, Depends(get_current_user_id)]
CurrentUserIdOrDemo = Annotated[UUID, Depends(get_current_user_id_or_demo)]
DbSession = Annotated[AsyncSession, Depends(get_session)]


# ============================================================================
# Workspace Context Dependencies
# ============================================================================


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


# ============================================================================
# Issue Service Dependencies
# ============================================================================


async def get_create_issue_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CreateIssueService:
    """Get CreateIssueService instance.

    Args:
        session: Database session.

    Returns:
        Configured CreateIssueService.
    """
    from pilot_space.application.services.issue import CreateIssueService
    from pilot_space.infrastructure.database.repositories import (
        ActivityRepository,
        IssueRepository,
        LabelRepository,
    )

    return CreateIssueService(
        session=session,
        issue_repository=IssueRepository(session),
        activity_repository=ActivityRepository(session),
        label_repository=LabelRepository(session),
    )


async def get_update_issue_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UpdateIssueService:
    """Get UpdateIssueService instance.

    Args:
        session: Database session.

    Returns:
        Configured UpdateIssueService.
    """
    from pilot_space.application.services.issue import UpdateIssueService
    from pilot_space.infrastructure.database.repositories import (
        ActivityRepository,
        IssueRepository,
        LabelRepository,
    )

    return UpdateIssueService(
        session=session,
        issue_repository=IssueRepository(session),
        activity_repository=ActivityRepository(session),
        label_repository=LabelRepository(session),
    )


async def get_get_issue_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> GetIssueService:
    """Get GetIssueService instance.

    Args:
        session: Database session.

    Returns:
        Configured GetIssueService.
    """
    from pilot_space.application.services.issue import GetIssueService
    from pilot_space.infrastructure.database.repositories import IssueRepository

    return GetIssueService(
        issue_repository=IssueRepository(session),
    )


async def get_list_issues_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ListIssuesService:
    """Get ListIssuesService instance.

    Args:
        session: Database session.

    Returns:
        Configured ListIssuesService.
    """
    from pilot_space.application.services.issue import ListIssuesService
    from pilot_space.infrastructure.database.repositories import IssueRepository

    return ListIssuesService(
        issue_repository=IssueRepository(session),
    )


async def get_activity_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ActivityService:
    """Get ActivityService instance.

    Args:
        session: Database session.

    Returns:
        Configured ActivityService.
    """
    from pilot_space.application.services.issue import ActivityService
    from pilot_space.infrastructure.database.repositories import ActivityRepository

    return ActivityService(
        activity_repository=ActivityRepository(session),
    )


# ============================================================================
# AI Context Service Dependencies
# ============================================================================


async def get_ai_context_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> GenerateAIContextService:
    """Get GenerateAIContextService instance.

    Args:
        session: Database session.

    Returns:
        Configured GenerateAIContextService.
    """
    from pilot_space.application.services.ai_context import GenerateAIContextService
    from pilot_space.infrastructure.database.repositories import (
        AIContextRepository,
        IntegrationLinkRepository,
        IssueRepository,
        NoteRepository,
    )

    return GenerateAIContextService(
        session=session,
        ai_context_repository=AIContextRepository(session),
        issue_repository=IssueRepository(session),
        note_repository=NoteRepository(session),
        integration_link_repository=IntegrationLinkRepository(session),
    )


async def get_user_api_keys(
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
    request: Request,
) -> dict[str, str]:
    """Get API keys for the current user's workspace.

    Retrieves AI provider API keys from workspace AI configuration.

    Args:
        session: Database session.
        current_user: Current user.
        request: Request for workspace context.

    Returns:
        Dictionary of provider name to API key.
    """
    from pilot_space.infrastructure.database.repositories import AIConfigurationRepository
    from pilot_space.infrastructure.encryption import decrypt_api_key

    workspace_id = getattr(request.state, "workspace_id", None)
    if not workspace_id:
        return {}

    repo = AIConfigurationRepository(session)
    configs = await repo.get_by_workspace(workspace_id)

    api_keys: dict[str, str] = {}
    for config in configs:
        if config.is_active and config.api_key_encrypted:
            # Decrypt and map provider enum to key name
            decrypted_key = decrypt_api_key(config.api_key_encrypted)
            api_keys[config.provider.value] = decrypted_key

    return api_keys


# ============================================================================
# AI Configuration Dependencies
# ============================================================================


async def get_ai_config(
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
    request: Request,
) -> AIConfiguration | None:
    """Get AI configuration for the current workspace.

    Args:
        session: Database session.
        current_user: Current user.
        request: Request for workspace context.

    Returns:
        AI configuration or None if not configured.
    """
    from pilot_space.infrastructure.database.repositories import AIConfigurationRepository

    workspace_id = getattr(request.state, "workspace_id", None)
    if not workspace_id:
        return None

    repo = AIConfigurationRepository(session)
    configs = await repo.get_by_workspace(workspace_id)
    # Return the first active configuration (if any)
    return configs[0] if configs else None


async def get_ai_config_or_demo(
    session: Annotated[AsyncSession, Depends(get_session)],
    request: Request,
) -> AIConfiguration | None:
    """Get AI configuration with demo mode support.

    In demo mode (development + demo workspace), returns None to allow mock mode.
    In production, requires authentication and returns workspace config.

    Args:
        session: Database session.
        request: Request for workspace context.

    Returns:
        AI configuration or None (for mock mode).
    """
    from pilot_space.config import get_settings

    settings = get_settings()
    workspace_id = getattr(request.state, "workspace_id", None)

    # In demo mode with mock AI, return None to use mock responses
    if settings.app_env in ("development", "test") and settings.ai_fake_mode:
        return None

    # In production, require auth and return config
    if not workspace_id:
        return None

    from pilot_space.infrastructure.database.repositories import AIConfigurationRepository

    repo = AIConfigurationRepository(session)
    configs = await repo.get_by_workspace(workspace_id)
    return configs[0] if configs else None


# Type imports for service return types
if TYPE_CHECKING:
    from pilot_space.application.services.ai_context import GenerateAIContextService
    from pilot_space.application.services.issue import (
        ActivityService,
        CreateIssueService,
        GetIssueService,
        ListIssuesService,
        UpdateIssueService,
    )
    from pilot_space.infrastructure.database.models import AIConfiguration
