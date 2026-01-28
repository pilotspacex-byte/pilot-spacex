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

    # SDK orchestrator not yet fully integrated
    # Will be implemented in P12-P15 with proper AsyncSession handling
    sdk_orchestrator = providers.Object(None)


def register_sdk_agents(orchestrator: Any) -> None:
    """Register all SDK agents in the orchestrator.

    NOTE: Some agents require key_storage which is session-dependent.
    For now, we pass orchestrator._key_storage to those agents.
    This works because the orchestrator is created per-request with
    a session-scoped key_storage instance.

    Args:
        orchestrator: SDKOrchestrator instance.
    """
    from pilot_space.ai.agents.ai_context_agent import AIContextAgent
    from pilot_space.ai.agents.assignee_recommender_agent_sdk import (
        AssigneeRecommenderAgent,
    )
    from pilot_space.ai.agents.commit_linker_agent_sdk import CommitLinkerAgent
    from pilot_space.ai.agents.diagram_generator_agent import DiagramGeneratorAgent
    from pilot_space.ai.agents.doc_generator_agent import DocGeneratorAgent

    # DuplicateDetectorAgent requires AsyncSession - cannot register at init time
    # from pilot_space.ai.agents.duplicate_detector_agent_sdk import (
    #     DuplicateDetectorAgent,
    # )
    from pilot_space.ai.agents.ghost_text_agent import GhostTextAgent
    from pilot_space.ai.agents.issue_enhancer_agent_sdk import IssueEnhancerAgent
    from pilot_space.ai.agents.issue_extractor_sdk_agent import IssueExtractorAgent
    from pilot_space.ai.agents.margin_annotation_agent_sdk import (
        MarginAnnotationAgentSDK,
    )
    from pilot_space.ai.agents.pilotspace_agent import PilotSpaceAgent
    from pilot_space.ai.agents.pr_review_agent import PRReviewAgent
    from pilot_space.ai.agents.task_decomposer_agent import TaskDecomposerAgent
    from pilot_space.ai.sdk_orchestrator import AgentName

    # Access orchestrator's protected members for agent initialization
    # These are design decisions per DD-002 (infrastructure injection)
    deps_base = {
        "tool_registry": orchestrator._tool_registry,  # noqa: SLF001
        "provider_selector": orchestrator._provider_selector,  # noqa: SLF001
        "cost_tracker": orchestrator._cost_tracker,  # noqa: SLF001
        "resilient_executor": orchestrator._resilient_executor,  # noqa: SLF001
    }

    # Extended deps for agents that need key_storage
    deps_with_key = {
        **deps_base,
        "key_storage": orchestrator._key_storage,  # noqa: SLF001
    }

    # Create SDK wrappers for PilotSpaceAgent
    from pathlib import Path

    from pilot_space.ai.agents.pilotspace_agent import SkillRegistry
    from pilot_space.ai.sdk import PermissionHandler, SessionHandler

    permission_handler = PermissionHandler(approval_service=orchestrator._approval_service)  # noqa: SLF001
    # SessionHandler is None if Redis not configured (session_manager=None)
    session_handler = (
        SessionHandler(session_manager=orchestrator._session_manager)  # noqa: SLF001
        if orchestrator._session_manager  # noqa: SLF001
        else None
    )

    # Get skills directory from backend/.claude/skills
    backend_dir = Path(__file__).parent.parent
    skills_dir = backend_dir / ".claude" / "skills"
    skill_registry = SkillRegistry(skills_dir)

    # Register all SDK agents
    # Note-related agents (no key_storage needed)
    orchestrator.register_agent(
        AgentName.GHOST_TEXT,
        GhostTextAgent(**deps_base),
    )
    orchestrator.register_agent(
        AgentName.MARGIN_ANNOTATION,
        MarginAnnotationAgentSDK(**deps_base),
    )
    # Issue extractor needs key_storage for API key access
    orchestrator.register_agent(
        AgentName.ISSUE_EXTRACTOR,
        IssueExtractorAgent(**deps_with_key),
    )

    # Issue-related agents
    orchestrator.register_agent(
        AgentName.AI_CONTEXT,
        AIContextAgent(**deps_base),
    )
    # PilotSpaceAgent: Main conversational agent with skill/subagent routing
    orchestrator.register_agent(
        AgentName.CONVERSATION,
        PilotSpaceAgent(
            tool_registry=orchestrator._tool_registry,  # noqa: SLF001
            provider_selector=orchestrator._provider_selector,  # noqa: SLF001
            cost_tracker=orchestrator._cost_tracker,  # noqa: SLF001
            resilient_executor=orchestrator._resilient_executor,  # noqa: SLF001
            permission_handler=permission_handler,
            session_handler=session_handler,
            skill_registry=skill_registry,
            subagents={},  # Subagents can be registered separately if needed
        ),
    )
    # Issue enhancer needs key_storage
    orchestrator.register_agent(
        AgentName.ISSUE_ENHANCER,
        IssueEnhancerAgent(**deps_with_key),
    )
    # Assignee recommender needs key_storage
    orchestrator.register_agent(
        AgentName.ASSIGNEE_RECOMMENDER,
        AssigneeRecommenderAgent(**deps_with_key),
    )
    # TODO(T036): DuplicateDetectorAgent requires AsyncSession parameter
    # which is per-request. Need to refactor to lazy instantiation or
    # pass session via context. Skipping registration for now.
    # orchestrator.register_agent(
    #     AgentName.DUPLICATE_DETECTOR,
    #     DuplicateDetectorAgent(**deps_with_key, session=???),
    # )

    # PR/Code agents (need key_storage for API access)
    orchestrator.register_agent(
        AgentName.PR_REVIEW,
        PRReviewAgent(**deps_with_key),
    )
    orchestrator.register_agent(
        AgentName.COMMIT_LINKER,
        CommitLinkerAgent(**deps_with_key),
    )

    # Documentation agents (no key_storage needed)
    orchestrator.register_agent(
        AgentName.DOC_GENERATOR,
        DocGeneratorAgent(**deps_base),
    )
    orchestrator.register_agent(
        AgentName.TASK_DECOMPOSER,
        TaskDecomposerAgent(**deps_base),
    )
    orchestrator.register_agent(
        AgentName.DIAGRAM_GENERATOR,
        DiagramGeneratorAgent(**deps_base),
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
