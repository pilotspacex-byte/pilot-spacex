"""FastAPI dependency injection.

Provides request-scoped dependencies for authentication, database, and services.

TODO(refactor): This file has 843 lines (exceeds 700-line limit).
  Split into modules:
  - dependencies/auth.py - Authentication dependencies
  - dependencies/database.py - Database session dependencies
  - dependencies/services.py - Service layer dependencies
  - dependencies/ai.py - AI-related dependencies
  Track: Issue to be created for proper refactoring
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Annotated, Any
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
    except Exception:
        # In development, fall back to demo user if auth fails
        if settings.app_env in ("development", "test"):
            return DEMO_USER_ID
        raise


# Type aliases for cleaner dependency injection
CurrentUser = Annotated[TokenPayload, Depends(get_current_user)]
CurrentUserId = Annotated[UUID, Depends(get_current_user_id)]
CurrentUserIdOrDemo = Annotated[UUID, Depends(get_current_user_id_or_demo)]
DbSession = Annotated[AsyncSession, Depends(get_session)]


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
    from pilot_space.infrastructure.database.models.user import User
    from pilot_space.infrastructure.database.repositories.user_repository import (
        UserRepository,
    )

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
    await user_repo.create(user)
    await session.commit()

    return current_user.user_id


# Dependency that ensures user is synced before operations requiring owner_id
SyncedUserId = Annotated[UUID, Depends(ensure_user_synced)]


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
    request: Request,
) -> GenerateAIContextService:
    """Get GenerateAIContextService instance.

    Args:
        session: Database session.
        request: FastAPI request for accessing app container.

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

    # Get AI infrastructure from container
    if not hasattr(request.app.state, "container"):
        raise RuntimeError("DI container not initialized. Check app startup.")

    container = request.app.state.container
    tool_registry = container.tool_registry()
    provider_selector = container.provider_selector()
    resilient_executor = container.resilient_executor()

    # Create session-scoped cost tracker
    from pilot_space.ai.infrastructure.cost_tracker import CostTracker

    cost_tracker = CostTracker(session=session)

    return GenerateAIContextService(
        session=session,
        ai_context_repository=AIContextRepository(session),
        issue_repository=IssueRepository(session),
        note_repository=NoteRepository(session),
        integration_link_repository=IntegrationLinkRepository(session),
        tool_registry=tool_registry,
        provider_selector=provider_selector,
        cost_tracker=cost_tracker,
        resilient_executor=resilient_executor,
    )


async def get_refine_ai_context_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    request: Request,
) -> RefineAIContextService:
    """Get RefineAIContextService instance.

    Args:
        session: Database session.
        request: FastAPI request for accessing app container.

    Returns:
        Configured RefineAIContextService.
    """
    from pilot_space.application.services.ai_context import RefineAIContextService
    from pilot_space.infrastructure.database.repositories import (
        AIContextRepository,
        IssueRepository,
    )

    # Get AI infrastructure from container
    if not hasattr(request.app.state, "container"):
        raise RuntimeError("DI container not initialized. Check app startup.")

    container = request.app.state.container
    tool_registry = container.tool_registry()
    provider_selector = container.provider_selector()
    resilient_executor = container.resilient_executor()

    # Create session-scoped cost tracker
    from pilot_space.ai.infrastructure.cost_tracker import CostTracker

    cost_tracker = CostTracker(session=session)

    return RefineAIContextService(
        session=session,
        ai_context_repository=AIContextRepository(session),
        issue_repository=IssueRepository(session),
        tool_registry=tool_registry,
        provider_selector=provider_selector,
        cost_tracker=cost_tracker,
        resilient_executor=resilient_executor,
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


# ============================================================================
# AI Infrastructure Dependencies
# ============================================================================


async def get_redis_client(request: Request) -> RedisClient:
    """Get Redis client from app state.

    Args:
        request: FastAPI request with app state.

    Returns:
        RedisClient instance.

    Raises:
        RuntimeError: If container not initialized or Redis not configured.
    """
    if not hasattr(request.app.state, "container"):
        raise RuntimeError("DI container not initialized. Check app startup.")

    container = request.app.state.container
    redis = container.redis_client()

    if redis is None:
        raise RuntimeError("Redis not configured. Check REDIS_URL environment variable.")

    return redis


async def get_session_manager(request: Request) -> SessionManager | None:
    """Get session manager from app state.

    Args:
        request: FastAPI request with app state.

    Returns:
        SessionManager instance or None if Redis not configured.

    Raises:
        RuntimeError: If container not initialized.
    """
    if not hasattr(request.app.state, "container"):
        raise RuntimeError("DI container not initialized. Check app startup.")

    container = request.app.state.container
    return container.session_manager()


async def get_provider_selector(request: Request) -> ProviderSelector:
    """Get provider selector from app state.

    Args:
        request: FastAPI request with app state.

    Returns:
        ProviderSelector instance.

    Raises:
        RuntimeError: If container not initialized.
    """
    if not hasattr(request.app.state, "container"):
        raise RuntimeError("DI container not initialized. Check app startup.")

    container = request.app.state.container
    return container.provider_selector()


async def get_resilient_executor(request: Request) -> ResilientExecutor:
    """Get resilient executor from app state.

    Args:
        request: FastAPI request with app state.

    Returns:
        ResilientExecutor instance.

    Raises:
        RuntimeError: If container not initialized.
    """
    if not hasattr(request.app.state, "container"):
        raise RuntimeError("DI container not initialized. Check app startup.")

    container = request.app.state.container
    return container.resilient_executor()


async def get_tool_registry(request: Request) -> ToolRegistry:
    """Get tool registry from app state.

    Args:
        request: FastAPI request with app state.

    Returns:
        ToolRegistry instance.

    Raises:
        RuntimeError: If container not initialized.
    """
    if not hasattr(request.app.state, "container"):
        raise RuntimeError("DI container not initialized. Check app startup.")

    container = request.app.state.container
    return container.tool_registry()


async def get_key_storage(
    session: Annotated[AsyncSession, Depends(get_session)],
    request: Request,
) -> SecureKeyStorage:
    """Get secure key storage with request-scoped session.

    Args:
        session: Database session.
        request: FastAPI request with app state.

    Returns:
        SecureKeyStorage instance.

    Raises:
        RuntimeError: If container not initialized.
    """
    from pilot_space.ai.infrastructure.key_storage import SecureKeyStorage

    if not hasattr(request.app.state, "container"):
        raise RuntimeError("DI container not initialized. Check app startup.")

    container = request.app.state.container
    encryption_key = container.encryption_key()

    return SecureKeyStorage(db=session, master_secret=encryption_key)


async def get_approval_service_dep(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApprovalService:
    """Get approval service with request-scoped session.

    Args:
        session: Database session.

    Returns:
        ApprovalService instance.
    """
    from pilot_space.ai.infrastructure.approval import ApprovalService

    return ApprovalService(session=session)


async def get_cost_tracker_dep(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CostTracker:
    """Get cost tracker with request-scoped session.

    Args:
        session: Database session.

    Returns:
        CostTracker instance.
    """
    from pilot_space.ai.infrastructure.cost_tracker import CostTracker

    return CostTracker(session=session)


# ============================================================================
# SDK Configuration Dependencies
# ============================================================================


async def get_permission_handler_dep(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PermissionHandler:
    """Get permission handler for SDK agents.

    Args:
        session: Database session.

    Returns:
        PermissionHandler instance.
    """
    from pilot_space.ai.infrastructure.approval import ApprovalService
    from pilot_space.ai.sdk import PermissionHandler

    approval_service = ApprovalService(session=session)
    return PermissionHandler(approval_service=approval_service)


async def get_session_handler_dep(request: Request) -> SessionHandler | None:
    """Get session handler for SDK agents.

    Args:
        request: FastAPI request with app state.

    Returns:
        SessionHandler instance or None if Redis not configured.

    Raises:
        RuntimeError: If container not initialized.
    """
    if not hasattr(request.app.state, "container"):
        raise RuntimeError("DI container not initialized. Check app startup.")

    from pilot_space.ai.sdk import SessionHandler

    container = request.app.state.container
    session_manager = container.session_manager()

    if session_manager is None:
        return None

    return SessionHandler(session_manager=session_manager)


async def get_skill_registry_dep(request: Request) -> Any:
    """Get skill registry for SDK agents.

    SkillRegistry was removed during 005-conversational-agent-arch migration.
    Skills are now loaded by PilotSpaceAgent from space's .claude/skills/ directory.

    Args:
        request: FastAPI request with app state.

    Returns:
        None (SkillRegistry has been removed).
    """
    return None


# ============================================================================
# PilotSpaceAgent Dependencies
# ============================================================================


async def get_pilotspace_agent(request: Request) -> PilotSpaceAgent:
    """Get PilotSpaceAgent from DI container.

    Args:
        request: FastAPI request with app state.

    Returns:
        Fully initialized PilotSpaceAgent.

    Raises:
        RuntimeError: If DI container not initialized.
    """
    if not hasattr(request.app.state, "container"):
        raise RuntimeError("DI container not initialized. Check app startup.")
    return request.app.state.container.pilotspace_agent()


async def get_queue_client(request: Request) -> SupabaseQueueClient | None:
    """Get queue client from DI container.

    Args:
        request: FastAPI request with app state.

    Returns:
        SupabaseQueueClient instance or None if not configured.
    """
    if not hasattr(request.app.state, "container"):
        return None
    return request.app.state.container.queue_client()


# Type imports for service return types (must be before type aliases)
if TYPE_CHECKING:
    from pilot_space.ai.agents.pilotspace_agent import PilotSpaceAgent
    from pilot_space.ai.infrastructure.approval import ApprovalService
    from pilot_space.ai.infrastructure.cost_tracker import CostTracker
    from pilot_space.ai.infrastructure.key_storage import SecureKeyStorage
    from pilot_space.ai.infrastructure.resilience import ResilientExecutor
    from pilot_space.ai.providers.provider_selector import ProviderSelector
    from pilot_space.ai.sdk import PermissionHandler, SessionHandler
    from pilot_space.ai.session.session_manager import SessionManager
    from pilot_space.ai.tools.mcp_server import ToolRegistry
    from pilot_space.infrastructure.cache.redis import RedisClient
    from pilot_space.infrastructure.queue.supabase_queue import SupabaseQueueClient

# Type aliases for AI dependencies (using string forward references)
SessionManagerDep = Annotated["SessionManager | None", Depends(get_session_manager)]
RedisDep = Annotated["RedisClient", Depends(get_redis_client)]
ProviderSelectorDep = Annotated["ProviderSelector", Depends(get_provider_selector)]
ResilientExecutorDep = Annotated["ResilientExecutor", Depends(get_resilient_executor)]
ToolRegistryDep = Annotated["ToolRegistry", Depends(get_tool_registry)]
KeyStorageDep = Annotated["SecureKeyStorage", Depends(get_key_storage)]
ApprovalServiceDep = Annotated["ApprovalService", Depends(get_approval_service_dep)]
CostTrackerDep = Annotated["CostTracker", Depends(get_cost_tracker_dep)]

PermissionHandlerDep = Annotated["PermissionHandler", Depends(get_permission_handler_dep)]
SessionHandlerDep = Annotated["SessionHandler | None", Depends(get_session_handler_dep)]
SkillRegistryDep = Annotated[Any, Depends(get_skill_registry_dep)]
PilotSpaceAgentDep = Annotated["PilotSpaceAgent", Depends(get_pilotspace_agent)]
QueueClientDep = Annotated["SupabaseQueueClient | None", Depends(get_queue_client)]


# Additional type imports for other services
if TYPE_CHECKING:
    from pilot_space.application.services.ai_context import (
        GenerateAIContextService,
        RefineAIContextService,
    )
    from pilot_space.application.services.issue import (
        ActivityService,
        CreateIssueService,
        GetIssueService,
        ListIssuesService,
        UpdateIssueService,
    )
    from pilot_space.infrastructure.database.models import AIConfiguration
