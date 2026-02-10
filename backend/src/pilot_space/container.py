"""Dependency Injection container for Pilot Space.

Uses dependency-injector to manage application dependencies including:
- Database connections and sessions
- Repositories
- Services
- External clients (Redis, Meilisearch, Queue, AI providers)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from dependency_injector import containers, providers

from pilot_space.ai.agents.pilotspace_agent import PilotSpaceAgent
from pilot_space.config import get_settings
from pilot_space.infrastructure.auth.supabase_auth import SupabaseAuth
from pilot_space.infrastructure.database.engine import (
    get_engine,
    get_session_factory,
)
from pilot_space.infrastructure.database.repositories.project_repository import (
    ProjectRepository,
)
from pilot_space.infrastructure.database.repositories.user_repository import (
    UserRepository,
)
from pilot_space.infrastructure.database.repositories.workspace_repository import (
    WorkspaceRepository,
)
from pilot_space.spaces.manager import SpaceManager

if TYPE_CHECKING:
    from pilot_space.ai.infrastructure.resilience import ResilientExecutor
    from pilot_space.ai.providers.provider_selector import ProviderSelector
    from pilot_space.ai.tools.mcp_server import ToolRegistry
    from pilot_space.config import Settings
    from pilot_space.infrastructure.cache.redis import RedisClient
    from pilot_space.infrastructure.queue.supabase_queue import SupabaseQueueClient

from pilot_space.ai.session.session_manager import SessionManager


class Container(containers.DeclarativeContainer):
    """Main application DI container.

    Provides dependency injection for all application components.
    Wire this container to modules that need dependency resolution.

    Usage:
        container = Container()
        container.wire(modules=[...])

        # Access dependencies
        user_repo = container.user_repository()
    """

    wiring_config = containers.WiringConfiguration(
        modules=[
            "pilot_space.api.v1.routers.auth",
            "pilot_space.api.v1.routers.workspaces",
            "pilot_space.api.v1.routers.projects",
            "pilot_space.dependencies",
        ],
    )

    # Configuration
    config = providers.Singleton(get_settings)

    # Database
    engine = providers.Singleton(get_engine)
    session_factory = providers.Singleton(get_session_factory)

    # Auth
    supabase_auth = providers.Singleton(SupabaseAuth)

    # Repositories
    # Note: Repositories are Factory providers since they need a new session per request
    user_repository = providers.Factory(UserRepository)
    workspace_repository = providers.Factory(WorkspaceRepository)
    project_repository = providers.Factory(ProjectRepository)

    # Infrastructure clients
    # Note: These are optional singletons that may not be configured
    # Check if redis_client or queue_client is not None before using

    @staticmethod
    def _create_queue_client() -> SupabaseQueueClient | None:
        """Create queue client if configured."""
        from pilot_space.infrastructure.queue.supabase_queue import SupabaseQueueClient

        settings = get_settings()
        service_key = settings.supabase_service_key.get_secret_value()
        if settings.supabase_url and service_key:
            return SupabaseQueueClient(
                supabase_url=settings.supabase_url,
                service_key=service_key,
            )
        return None

    @staticmethod
    def _create_redis_client() -> RedisClient | None:
        """Create Redis client if configured."""
        from pilot_space.infrastructure.cache.redis import RedisClient

        settings = get_settings()
        if settings.redis_url:
            return RedisClient(settings.redis_url)
        return None

    queue_client = providers.Singleton(_create_queue_client)
    redis_client = providers.Singleton(_create_redis_client)

    # AI Infrastructure
    # Note: Session-dependent services are created via dependency functions
    # in dependencies.py, not as singletons in the container.

    @staticmethod
    def _create_session_manager(redis_client: RedisClient | None) -> SessionManager | None:
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

    @staticmethod
    def _create_provider_selector() -> ProviderSelector:
        """Create provider selector.

        Returns:
            ProviderSelector instance.
        """
        from pilot_space.ai.providers.provider_selector import ProviderSelector

        return ProviderSelector()

    @staticmethod
    def _create_resilient_executor() -> ResilientExecutor:
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

    @staticmethod
    def _create_tool_registry() -> ToolRegistry:
        """Create tool registry.

        Returns:
            ToolRegistry instance.
        """
        from pilot_space.ai.tools.mcp_server import ToolRegistry

        return ToolRegistry()

    # AI service providers (stateless singletons only)
    # Note: Services requiring AsyncSession are created per-request in dependencies.py

    @staticmethod
    def _get_encryption_key_from_config(settings: Settings) -> str:
        """Get encryption key from settings.

        Args:
            settings: Application settings.

        Returns:
            Encryption key for API key storage.
        """
        return settings.encryption_key.get_secret_value()

    encryption_key = providers.Factory(
        _get_encryption_key_from_config,
        settings=config,
    )

    session_manager = providers.Singleton(
        _create_session_manager,
        redis_client=redis_client,
    )

    provider_selector = providers.Singleton(_create_provider_selector)

    resilient_executor = providers.Singleton(_create_resilient_executor)

    tool_registry = providers.Singleton(_create_tool_registry)

    @staticmethod
    def _create_space_manager() -> Any:
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

    space_manager = providers.Singleton(_create_space_manager)

    @staticmethod
    def _create_pilotspace_agent(
        tool_registry: ToolRegistry,
        provider_selector: ProviderSelector,
        resilient_executor: ResilientExecutor,
        session_manager: SessionManager | None,
        space_manager: SpaceManager,
    ) -> PilotSpaceAgent:
        """Create PilotSpaceAgent with all dependencies.

        Args:
            tool_registry: MCP tool registry.
            provider_selector: Provider/model selection service.
            resilient_executor: Retry and circuit breaker service.
            session_manager: Session manager (None if Redis not configured).
            space_manager: Space management service.

        Returns:
            Fully initialized PilotSpaceAgent.
        """
        from pilot_space.ai.infrastructure.approval import ApprovalService
        from pilot_space.ai.infrastructure.cost_tracker import CostTracker
        from pilot_space.ai.sdk.permission_handler import PermissionHandler

        # CostTracker and ApprovalService require a DB session for persistence.
        # In singleton context (worker), pass None — cost/approval tracking
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
        )

    pilotspace_agent = providers.Singleton(
        _create_pilotspace_agent,
        tool_registry=tool_registry,
        provider_selector=provider_selector,
        resilient_executor=resilient_executor,
        session_manager=session_manager,
        space_manager=space_manager,
    )


def create_container(settings: Settings | None = None) -> Container:
    """Create and configure the DI container.

    Args:
        settings: Optional settings override for testing.

    Returns:
        Configured Container instance.
    """
    container = Container()
    if settings is not None:
        container.config.override(providers.Object(settings))  # type: ignore[no-untyped-call]
    return container


# Global container instance
container = create_container()


def get_container() -> Container:
    """Get the global container instance.

    Returns:
        Global Container instance.
    """
    return container


__all__ = ["Container", "container", "create_container", "get_container"]
