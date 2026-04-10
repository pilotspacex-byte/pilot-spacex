"""AI-related dependencies.

Provides request-scoped dependencies for AI context services, AI configuration,
AI infrastructure (Redis, providers, tools), SDK configuration, and agents.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.dependencies.auth import DbSession, get_current_user, get_session
from pilot_space.infrastructure.auth import TokenPayload

# RedisClient must be imported at runtime (not just TYPE_CHECKING) so that
# RedisDep's Annotated type can be resolved by Pydantic during OpenAPI generation.
from pilot_space.infrastructure.cache.redis import RedisClient

if TYPE_CHECKING:
    from pilot_space.ai.agents.pilotspace_agent import PilotSpaceAgent
    from pilot_space.ai.infrastructure.approval import ApprovalService
    from pilot_space.ai.infrastructure.cost_tracker import CostTracker
    from pilot_space.ai.infrastructure.key_storage import SecureKeyStorage
    from pilot_space.ai.infrastructure.resilience import ResilientExecutor
    from pilot_space.ai.providers.provider_selector import ProviderSelector
    from pilot_space.ai.sdk import PermissionHandler, SessionHandler
    from pilot_space.ai.services.ghost_text import GhostTextService
    from pilot_space.ai.session.session_manager import SessionManager
    from pilot_space.ai.tools.mcp_server import ToolRegistry
    from pilot_space.application.services.ai_context import (
        GenerateAIContextService,
        RefineAIContextService,
    )
    from pilot_space.infrastructure.database.models import AIConfiguration
    from pilot_space.infrastructure.queue.supabase_queue import SupabaseQueueClient


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
    pilotspace_agent = container.pilotspace_agent()
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
        pilotspace_agent=pilotspace_agent,
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
    pilotspace_agent = container.pilotspace_agent()
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
        pilotspace_agent=pilotspace_agent,
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

    # Phase 69-05: consult granular PermissionService when available.
    permission_service = None
    try:
        from pilot_space.container.container import get_container

        permission_service = get_container().permission_service()
    except Exception:
        permission_service = None

    return PermissionHandler(
        approval_service=approval_service,
        permission_service=permission_service,
    )


async def get_session_handler_dep(
    request: Request,
    session: DbSession,
) -> SessionHandler | None:
    """Get session handler for SDK agents.

    Args:
        request: FastAPI request with app state.
        session: SQLAlchemy async session for PostgreSQL fallback.

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

    return SessionHandler(session_manager=session_manager, db_session=session)


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


# ============================================================================
# GhostTextService Dependencies
# ============================================================================


async def get_ghost_text_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    redis: Annotated[RedisClient, Depends(get_redis_client)],
    request: Request,
) -> GhostTextService:
    """Get GhostTextService with AI infrastructure from container.

    Follows the same pattern as get_ai_context_service:
    - Singletons (executor, selector, client pool) from container
    - Request-scoped deps (key_storage, cost_tracker) from session
    - Redis from get_redis_client Depends (FastAPI deduplicates with RedisDep)

    Args:
        session: Database session (BYOK lookup + cost persistence).
        redis: Redis client (shared with rate limiter via FastAPI Depends caching).
        request: FastAPI request for container access.

    Returns:
        Configured GhostTextService.

    Raises:
        RuntimeError: If DI container not initialized.
    """
    from pilot_space.ai.infrastructure.cost_tracker import CostTracker
    from pilot_space.ai.infrastructure.key_storage import SecureKeyStorage
    from pilot_space.ai.services.ghost_text import GhostTextService

    if not hasattr(request.app.state, "container"):
        raise RuntimeError("DI container not initialized. Check app startup.")

    container = request.app.state.container

    return GhostTextService(
        redis=redis,
        resilient_executor=container.resilient_executor(),
        provider_selector=container.provider_selector(),
        client_pool=container.anthropic_client_pool(),
        key_storage=SecureKeyStorage(
            db=session,
            master_secret=container.encryption_key(),
        ),
        cost_tracker=CostTracker(session=session),
    )


# Type aliases for AI dependencies (using string forward references)
SessionManagerDep = Annotated["SessionManager | None", Depends(get_session_manager)]
RedisDep = Annotated[RedisClient, Depends(get_redis_client)]
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
GhostTextServiceDep = Annotated["GhostTextService", Depends(get_ghost_text_service)]
