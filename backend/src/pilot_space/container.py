"""Dependency Injection container for Pilot Space.

Uses dependency-injector to manage application dependencies including:
- Database connections and sessions
- Repositories
- Services
- External clients (Redis, Meilisearch, Queue, AI providers)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dependency_injector import containers, providers

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

if TYPE_CHECKING:
    from pilot_space.config import Settings
    from pilot_space.infrastructure.cache.redis import RedisClient
    from pilot_space.infrastructure.queue.supabase_queue import SupabaseQueueClient


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
