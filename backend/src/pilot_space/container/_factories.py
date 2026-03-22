"""Factory functions for creating infrastructure and AI components.

Extracted from Container static methods for the 700-line file limit.
These functions are used by DI container providers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pilot_space.config import get_settings

if TYPE_CHECKING:
    from pilot_space.ai.infrastructure.anthropic_client_pool import AnthropicClientPool
    from pilot_space.ai.infrastructure.resilience import ResilientExecutor
    from pilot_space.ai.providers.provider_selector import ProviderSelector
    from pilot_space.ai.tools.mcp_server import ToolRegistry
    from pilot_space.config import Settings
    from pilot_space.infrastructure.cache.redis import RedisClient
    from pilot_space.infrastructure.queue.supabase_queue import SupabaseQueueClient


def create_queue_client() -> SupabaseQueueClient | None:
    """Create queue client if Supabase is configured.

    The client lazily obtains the shared SDK AsyncClient singleton on first use,
    so no URL/key arguments are needed here.
    """
    from pilot_space.infrastructure.queue.supabase_queue import SupabaseQueueClient

    settings = get_settings()
    service_key = settings.supabase_service_key.get_secret_value()
    if settings.supabase_url and service_key:
        return SupabaseQueueClient()
    return None


def create_redis_client() -> RedisClient | None:
    """Create Redis client if configured."""
    from pilot_space.infrastructure.cache.redis import RedisClient

    settings = get_settings()
    if settings.redis_url:
        return RedisClient(settings.redis_url)
    return None


def create_session_manager(redis_client: RedisClient | None) -> Any:
    """Create session manager if Redis is available and connected.

    Args:
        redis_client: Redis client instance.

    Returns:
        SessionManager instance or None if Redis not configured or not connected.
    """
    if redis_client is None:
        return None

    # Check if Redis client is actually connected
    # (RedisClient may be instantiated but not connected)
    if not redis_client.is_connected:
        return None

    from pilot_space.ai.session.session_manager import SessionManager

    return SessionManager(redis=redis_client)


def create_provider_selector() -> ProviderSelector:
    """Create provider selector.

    Returns:
        ProviderSelector instance.
    """
    from pilot_space.ai.providers.provider_selector import ProviderSelector

    return ProviderSelector()


def create_resilient_executor() -> ResilientExecutor:
    """Create resilient executor with circuit breaker.

    Returns:
        ResilientExecutor instance.
    """
    from pilot_space.ai.infrastructure.resilience import (
        CircuitBreakerConfig,
        ResilientExecutor,
    )

    settings = get_settings()
    circuit_config = CircuitBreakerConfig(
        failure_threshold=5,
        timeout_seconds=settings.ai_timeout_seconds,
    )

    return ResilientExecutor(circuit_config=circuit_config)


def create_anthropic_client_pool() -> AnthropicClientPool:
    """Create singleton Anthropic client pool for connection reuse.

    Returns:
        AnthropicClientPool instance.
    """
    from pilot_space.ai.infrastructure.anthropic_client_pool import AnthropicClientPool

    return AnthropicClientPool()


def create_tool_registry() -> ToolRegistry:
    """Create tool registry.

    Returns:
        ToolRegistry instance.
    """
    from pilot_space.ai.tools.mcp_server import ToolRegistry

    return ToolRegistry()


def get_encryption_key_from_config(settings: Settings) -> str:
    """Get encryption key from settings.

    Args:
        settings: Application settings.

    Returns:
        Encryption key for API key storage.
    """
    return settings.encryption_key.get_secret_value()


def create_space_manager() -> Any:
    """Create SpaceManager for agent isolation.

    Returns:
        SpaceManager instance configured from settings.
    """
    from pilot_space.spaces import ProjectBootstrapper, SpaceManager

    settings = get_settings()

    bootstrapper = ProjectBootstrapper(templates_dir=settings.system_templates_dir)
    return SpaceManager(
        storage_root=settings.space_storage_root,
        bootstrapper=bootstrapper,
    )


def create_pilotspace_agent(
    tool_registry: ToolRegistry,
    provider_selector: ProviderSelector,
    resilient_executor: ResilientExecutor,
    session_manager: Any,
    space_manager: Any,
    queue_client: Any = None,
    session_factory: Any = None,
) -> Any:
    """Create PilotSpaceAgent with all dependencies.

    Args:
        tool_registry: MCP tool registry.
        provider_selector: Provider/model selection service.
        resilient_executor: Retry and circuit breaker service.
        session_manager: Session manager (None if Redis not configured).
        space_manager: Space management service.
        queue_client: Queue client for graph embedding jobs (optional).
        session_factory: Async sessionmaker for AuditLogHook out-of-request DB writes.

    Returns:
        Fully initialized PilotSpaceAgent.
    """
    from pilot_space.ai.agents.pilotspace_agent import PilotSpaceAgent
    from pilot_space.ai.infrastructure.approval import ApprovalService
    from pilot_space.ai.infrastructure.cost_tracker import CostTracker
    from pilot_space.ai.sdk.permission_handler import PermissionHandler

    # CostTracker and ApprovalService require a DB session for persistence.
    # In singleton context (worker), pass None -- cost/approval tracking
    # is only active in request-scoped contexts with a live session.
    cost_tracker = CostTracker(session=None)  # type: ignore[arg-type]
    approval_service = ApprovalService(session=None)  # type: ignore[arg-type]
    permission_handler = PermissionHandler(approval_service=approval_service)

    # Skills are now loaded by PilotSpaceAgent from the space's .claude/skills/ directory
    # (DD-086 migration from siloed SkillRegistry to filesystem-based auto-discovery).

    session_handler = None
    if session_manager is not None:
        from pilot_space.ai.sdk.session_handler import SessionHandler

        session_handler = SessionHandler(session_manager=session_manager)

    return PilotSpaceAgent(
        tool_registry=tool_registry,
        provider_selector=provider_selector,
        cost_tracker=cost_tracker,
        resilient_executor=resilient_executor,
        permission_handler=permission_handler,
        session_handler=session_handler,
        space_manager=space_manager,
        graph_queue_client=queue_client,
        session_factory=session_factory,
    )


def get_default_redirect_origin(settings: Settings) -> str:
    """Get default redirect origin from CORS origins.

    Args:
        settings: Application settings.

    Returns:
        First CORS origin or localhost fallback.
    """
    if settings.cors_origins:
        return settings.cors_origins[0]
    return "http://localhost:3000"
