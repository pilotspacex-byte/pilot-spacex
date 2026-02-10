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
from pilot_space.application.services.ai import (
    GetPRReviewStatusService,
    TriggerPRReviewService,
)
from pilot_space.application.services.ai_context import (
    ExportAIContextService,
    GenerateAIContextService,
    RefineAIContextService,
)
from pilot_space.application.services.annotation import CreateAnnotationService
from pilot_space.application.services.cycle import (
    AddIssueToCycleService,
    CreateCycleService,
    GetCycleService,
    RolloverCycleService,
    UpdateCycleService,
)
from pilot_space.application.services.discussion import CreateDiscussionService
from pilot_space.application.services.homepage import (
    DismissSuggestionService,
    GetActivityService,
    GetDigestService,
)
from pilot_space.application.services.integration import (
    AutoTransitionService,
    ConnectGitHubService,
    LinkCommitService,
    ProcessGitHubWebhookService,
)
from pilot_space.application.services.issue import (
    ActivityService,
    CreateIssueService,
    DeleteIssueService,
    GetIssueService,
    ListIssuesService,
    UpdateIssueService,
)
from pilot_space.application.services.note import (
    CreateNoteFromChatService,
    CreateNoteService,
    DeleteNoteService,
    GetNoteService,
    ListAnnotationsService,
    ListNotesService,
    PinNoteService,
    UpdateAnnotationService,
    UpdateNoteService,
)
from pilot_space.application.services.note.ai_update_service import (
    NoteAIUpdateService,
)
from pilot_space.application.services.onboarding import (
    CreateGuidedNoteService,
    GetOnboardingService,
    UpdateOnboardingService,
)
from pilot_space.application.services.role_skill import (
    CreateRoleSkillService,
    DeleteRoleSkillService,
    GenerateRoleSkillService,
    ListRoleSkillsService,
    UpdateRoleSkillService,
)
from pilot_space.application.services.workspace import WorkspaceService
from pilot_space.application.services.workspace_invitation import (
    WorkspaceInvitationService,
)
from pilot_space.application.services.workspace_member import WorkspaceMemberService
from pilot_space.config import get_settings
from pilot_space.dependencies.auth import get_current_session
from pilot_space.infrastructure.auth.supabase_auth import SupabaseAuth
from pilot_space.infrastructure.database.engine import (
    get_engine,
    get_session_factory,
)
from pilot_space.infrastructure.database.repositories.activity_repository import (
    ActivityRepository,
)
from pilot_space.infrastructure.database.repositories.ai_configuration_repository import (
    AIConfigurationRepository,
)
from pilot_space.infrastructure.database.repositories.ai_context_repository import (
    AIContextRepository,
)
from pilot_space.infrastructure.database.repositories.ai_task_repository import (
    AITaskRepository,
)
from pilot_space.infrastructure.database.repositories.approval_repository import (
    ApprovalRepository,
)
from pilot_space.infrastructure.database.repositories.cycle_repository import (
    CycleRepository,
)
from pilot_space.infrastructure.database.repositories.digest_repository import (
    DigestRepository,
)
from pilot_space.infrastructure.database.repositories.discussion_repository import (
    DiscussionRepository,
)
from pilot_space.infrastructure.database.repositories.homepage_repository import (
    HomepageRepository,
)
from pilot_space.infrastructure.database.repositories.integration_link_repository import (
    IntegrationLinkRepository,
)
from pilot_space.infrastructure.database.repositories.integration_repository import (
    IntegrationRepository,
)
from pilot_space.infrastructure.database.repositories.invitation_repository import (
    InvitationRepository,
)
from pilot_space.infrastructure.database.repositories.issue_link_repository import (
    IssueLinkRepository,
)
from pilot_space.infrastructure.database.repositories.issue_repository import (
    IssueRepository,
)
from pilot_space.infrastructure.database.repositories.label_repository import (
    LabelRepository,
)
from pilot_space.infrastructure.database.repositories.note_annotation_repository import (
    NoteAnnotationRepository,
)
from pilot_space.infrastructure.database.repositories.note_issue_link_repository import (
    NoteIssueLinkRepository,
)
from pilot_space.infrastructure.database.repositories.note_repository import (
    NoteRepository,
)
from pilot_space.infrastructure.database.repositories.onboarding_repository import (
    OnboardingRepository,
)
from pilot_space.infrastructure.database.repositories.project_repository import (
    ProjectRepository,
)
from pilot_space.infrastructure.database.repositories.role_skill_repository import (
    RoleSkillRepository,
)
from pilot_space.infrastructure.database.repositories.template_repository import (
    TemplateRepository,
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
            # Core routers
            "pilot_space.api.v1.routers.auth",
            "pilot_space.api.v1.routers.workspaces",
            "pilot_space.api.v1.routers.workspace_members",
            "pilot_space.api.v1.routers.workspace_invitations",
            "pilot_space.api.v1.routers.workspace_notes",
            "pilot_space.api.v1.routers.workspace_issues",
            "pilot_space.api.v1.routers.workspace_cycles",
            "pilot_space.api.v1.routers.workspace_note_issue_links",
            "pilot_space.api.v1.routers.workspace_ai_settings",
            "pilot_space.api.v1.routers.projects",
            "pilot_space.api.v1.routers.issues",
            "pilot_space.api.v1.routers.cycles",
            # AI routers
            "pilot_space.api.v1.routers.ai",
            "pilot_space.api.v1.routers.ai_chat",
            "pilot_space.api.v1.routers.ai_annotations",
            "pilot_space.api.v1.routers.ai_approvals",
            "pilot_space.api.v1.routers.ai_configuration",
            "pilot_space.api.v1.routers.ai_costs",
            "pilot_space.api.v1.routers.ai_extraction",
            "pilot_space.api.v1.routers.ai_pr_review",
            "pilot_space.api.v1.routers.ai_sessions",
            "pilot_space.api.v1.routers.ai_tasks",
            "pilot_space.api.v1.routers.ghost_text",
            "pilot_space.api.v1.routers.issues_ai",
            "pilot_space.api.v1.routers.issues_ai_context",
            "pilot_space.api.v1.routers.issues_ai_context_streaming",
            "pilot_space.api.v1.routers.notes_ai",
            "pilot_space.api.v1.routers.workspace_notes_ai",
            # Integration routers
            "pilot_space.api.v1.routers.integrations",
            "pilot_space.api.v1.routers.webhooks",
            # Support routers
            "pilot_space.api.v1.routers.homepage",
            "pilot_space.api.v1.routers.onboarding",
            "pilot_space.api.v1.routers.role_skills",
            "pilot_space.api.v1.routers.skills",
            "pilot_space.api.v1.routers.mcp_tools",
            # Dependencies
            "pilot_space.dependencies",
            "pilot_space.api.v1.dependencies",
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
    # Pattern: Factory providers with Callable session injection
    # Session is resolved per-request from ContextVar (set by get_session dependency)
    # FastAPI + dependency-injector integration:
    # https://python-dependency-injector.ets-labs.io/examples/fastapi.html

    user_repository = providers.Factory(
        UserRepository,
        session=providers.Callable(get_current_session),
    )

    workspace_repository = providers.Factory(
        WorkspaceRepository,
        session=providers.Callable(get_current_session),
    )

    project_repository = providers.Factory(
        ProjectRepository,
        session=providers.Callable(get_current_session),
    )

    activity_repository = providers.Factory(
        ActivityRepository,
        session=providers.Callable(get_current_session),
    )

    ai_configuration_repository = providers.Factory(
        AIConfigurationRepository,
        session=providers.Callable(get_current_session),
    )

    ai_context_repository = providers.Factory(
        AIContextRepository,
        session=providers.Callable(get_current_session),
    )

    ai_task_repository = providers.Factory(
        AITaskRepository,
        session=providers.Callable(get_current_session),
    )

    approval_repository = providers.Factory(
        ApprovalRepository,
        session=providers.Callable(get_current_session),
    )

    cycle_repository = providers.Factory(
        CycleRepository,
        session=providers.Callable(get_current_session),
    )

    digest_repository = providers.Factory(
        DigestRepository,
        session=providers.Callable(get_current_session),
    )

    discussion_repository = providers.Factory(
        DiscussionRepository,
        session=providers.Callable(get_current_session),
    )

    homepage_repository = providers.Factory(
        HomepageRepository,
        session=providers.Callable(get_current_session),
    )

    integration_repository = providers.Factory(
        IntegrationRepository,
        session=providers.Callable(get_current_session),
    )

    integration_link_repository = providers.Factory(
        IntegrationLinkRepository,
        session=providers.Callable(get_current_session),
    )

    invitation_repository = providers.Factory(
        InvitationRepository,
        session=providers.Callable(get_current_session),
    )

    issue_repository = providers.Factory(
        IssueRepository,
        session=providers.Callable(get_current_session),
    )

    issue_link_repository = providers.Factory(
        IssueLinkRepository,
        session=providers.Callable(get_current_session),
    )

    label_repository = providers.Factory(
        LabelRepository,
        session=providers.Callable(get_current_session),
    )

    note_repository = providers.Factory(
        NoteRepository,
        session=providers.Callable(get_current_session),
    )

    note_annotation_repository = providers.Factory(
        NoteAnnotationRepository,
        session=providers.Callable(get_current_session),
    )

    note_issue_link_repository = providers.Factory(
        NoteIssueLinkRepository,
        session=providers.Callable(get_current_session),
    )

    onboarding_repository = providers.Factory(
        OnboardingRepository,
        session=providers.Callable(get_current_session),
    )

    role_skill_repository = providers.Factory(
        RoleSkillRepository,
        session=providers.Callable(get_current_session),
    )

    template_repository = providers.Factory(
        TemplateRepository,
        session=providers.Callable(get_current_session),
    )

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

    # ===== Service Factories =====
    # Pattern: Services depend on session + repositories
    # All services use Factory providers (new instance per request)
    # FastAPI + dependency-injector integration:
    # https://python-dependency-injector.ets-labs.io/examples/fastapi.html

    # Issue Services
    create_issue_service = providers.Factory(
        CreateIssueService,
        session=providers.Callable(get_current_session),
        issue_repository=issue_repository,
        activity_repository=activity_repository,
        label_repository=label_repository,
    )

    update_issue_service = providers.Factory(
        UpdateIssueService,
        session=providers.Callable(get_current_session),
        issue_repository=issue_repository,
        activity_repository=activity_repository,
        label_repository=label_repository,
    )

    get_issue_service = providers.Factory(
        GetIssueService,
        issue_repository=issue_repository,
    )

    list_issues_service = providers.Factory(
        ListIssuesService,
        issue_repository=issue_repository,
    )

    activity_service = providers.Factory(
        ActivityService,
        activity_repository=activity_repository,
    )

    # Note Services
    create_note_service = providers.Factory(
        CreateNoteService,
        session=providers.Callable(get_current_session),
        note_repository=note_repository,
        template_repository=template_repository,
    )

    update_note_service = providers.Factory(
        UpdateNoteService,
        session=providers.Callable(get_current_session),
        note_repository=note_repository,
        activity_repository=activity_repository,
    )

    get_note_service = providers.Factory(
        GetNoteService,
        session=providers.Callable(get_current_session),
        note_repository=note_repository,
    )

    create_note_from_chat_service = providers.Factory(
        CreateNoteFromChatService,
        session=providers.Callable(get_current_session),
        note_repository=note_repository,
    )

    ai_update_note_service = providers.Factory(
        NoteAIUpdateService,
        session=providers.Callable(get_current_session),
        note_repository=note_repository,
        activity_repository=activity_repository,
    )

    list_notes_service = providers.Factory(
        ListNotesService,
        session=providers.Callable(get_current_session),
        note_repository=note_repository,
    )

    delete_note_service = providers.Factory(
        DeleteNoteService,
        session=providers.Callable(get_current_session),
        note_repository=note_repository,
        activity_repository=activity_repository,
    )

    pin_note_service = providers.Factory(
        PinNoteService,
        session=providers.Callable(get_current_session),
        note_repository=note_repository,
    )

    list_annotations_service = providers.Factory(
        ListAnnotationsService,
        session=providers.Callable(get_current_session),
        annotation_repository=note_annotation_repository,
    )

    update_annotation_service = providers.Factory(
        UpdateAnnotationService,
        session=providers.Callable(get_current_session),
        annotation_repository=note_annotation_repository,
    )

    # Issue Delete Service
    delete_issue_service = providers.Factory(
        DeleteIssueService,
        session=providers.Callable(get_current_session),
        issue_repository=issue_repository,
        activity_repository=activity_repository,
    )

    # Cycle Services
    create_cycle_service = providers.Factory(
        CreateCycleService,
        session=providers.Callable(get_current_session),
        cycle_repository=cycle_repository,
    )

    update_cycle_service = providers.Factory(
        UpdateCycleService,
        session=providers.Callable(get_current_session),
        cycle_repository=cycle_repository,
    )

    get_cycle_service = providers.Factory(
        GetCycleService,
        session=providers.Callable(get_current_session),
        cycle_repository=cycle_repository,
    )

    add_issue_to_cycle_service = providers.Factory(
        AddIssueToCycleService,
        session=providers.Callable(get_current_session),
        issue_repository=issue_repository,
        cycle_repository=cycle_repository,
    )

    rollover_cycle_service = providers.Factory(
        RolloverCycleService,
        session=providers.Callable(get_current_session),
        cycle_repository=cycle_repository,
        issue_repository=issue_repository,
    )

    # AI Context Services
    generate_ai_context_service = providers.Factory(
        GenerateAIContextService,
        session=providers.Callable(get_current_session),
        ai_context_repository=ai_context_repository,
        issue_repository=issue_repository,
        note_repository=note_repository,
        integration_link_repository=integration_link_repository,
        pilotspace_agent=pilotspace_agent,
        tool_registry=tool_registry,
        provider_selector=provider_selector,
        cost_tracker=providers.Callable(
            lambda: None
        ),  # Cost tracker requires request-scoped session
        resilient_executor=resilient_executor,
    )

    refine_ai_context_service = providers.Factory(
        RefineAIContextService,
        session=providers.Callable(get_current_session),
        ai_context_repository=ai_context_repository,
        issue_repository=issue_repository,
        pilotspace_agent=pilotspace_agent,
        tool_registry=tool_registry,
        provider_selector=provider_selector,
        cost_tracker=providers.Callable(lambda: None),
        resilient_executor=resilient_executor,
    )

    export_ai_context_service = providers.Factory(
        ExportAIContextService,
        session=providers.Callable(get_current_session),
        ai_context_repository=ai_context_repository,
        issue_repository=issue_repository,
    )

    # Annotation Services
    create_annotation_service = providers.Factory(
        CreateAnnotationService,
        session=providers.Callable(get_current_session),
    )

    # Discussion Services
    create_discussion_service = providers.Factory(
        CreateDiscussionService,
        session=providers.Callable(get_current_session),
    )

    # Integration Services
    connect_github_service = providers.Factory(
        ConnectGitHubService,
        session=providers.Callable(get_current_session),
        integration_repo=integration_repository,
    )

    process_github_webhook_service = providers.Factory(
        ProcessGitHubWebhookService,
        session=providers.Callable(get_current_session),
        integration_repo=integration_repository,
        integration_link_repo=integration_link_repository,
        issue_repo=issue_repository,
        activity_repo=activity_repository,
        webhook_handler=providers.Callable(
            lambda: None
        ),  # GitHubWebhookHandler instantiated per request
        sync_service=providers.Callable(lambda: None),  # GitHubSyncService per request
    )

    link_commit_service = providers.Factory(
        LinkCommitService,
        session=providers.Callable(get_current_session),
        integration_repo=integration_repository,
        integration_link_repo=integration_link_repository,
        issue_repo=issue_repository,
        activity_repo=activity_repository,
    )

    auto_transition_service = providers.Factory(
        AutoTransitionService,
        session=providers.Callable(get_current_session),
        issue_repo=issue_repository,
        activity_repo=activity_repository,
    )

    # Onboarding Services
    create_guided_note_service = providers.Factory(
        CreateGuidedNoteService,
        session=providers.Callable(get_current_session),
        onboarding_repository=onboarding_repository,
        note_repository=note_repository,
    )

    get_onboarding_service = providers.Factory(
        GetOnboardingService,
        session=providers.Callable(get_current_session),
        onboarding_repository=onboarding_repository,
    )

    update_onboarding_service = providers.Factory(
        UpdateOnboardingService,
        session=providers.Callable(get_current_session),
        onboarding_repository=onboarding_repository,
    )

    # Role Skill Services
    create_role_skill_service = providers.Factory(
        CreateRoleSkillService,
        session=providers.Callable(get_current_session),
    )

    update_role_skill_service = providers.Factory(
        UpdateRoleSkillService,
        session=providers.Callable(get_current_session),
    )

    delete_role_skill_service = providers.Factory(
        DeleteRoleSkillService,
        session=providers.Callable(get_current_session),
    )

    list_role_skills_service = providers.Factory(
        ListRoleSkillsService,
        session=providers.Callable(get_current_session),
    )

    generate_role_skill_service = providers.Factory(
        GenerateRoleSkillService,
        session=providers.Callable(get_current_session),
    )

    # Homepage Services
    get_activity_service = providers.Factory(
        GetActivityService,
        session=providers.Callable(get_current_session),
        homepage_repository=homepage_repository,
    )

    get_digest_service = providers.Factory(
        GetDigestService,
        session=providers.Callable(get_current_session),
        digest_repository=digest_repository,
    )

    dismiss_suggestion_service = providers.Factory(
        DismissSuggestionService,
        session=providers.Callable(get_current_session),
    )

    # Workspace Services
    workspace_service = providers.Factory(
        WorkspaceService,
        workspace_repo=workspace_repository,
        user_repo=user_repository,
        invitation_repo=invitation_repository,
        label_repo=label_repository,
    )

    workspace_member_service = providers.Factory(
        WorkspaceMemberService,
        workspace_repo=workspace_repository,
    )

    workspace_invitation_service = providers.Factory(
        WorkspaceInvitationService,
        workspace_repo=workspace_repository,
        invitation_repo=invitation_repository,
    )

    # AI Services (PR Review)
    trigger_pr_review_service = providers.Factory(
        TriggerPRReviewService,
        session=providers.Callable(get_current_session),
        queue_client=queue_client,
        integration_repo=integration_repository,
        cache_client=redis_client,
    )

    get_pr_review_status_service = providers.Factory(
        GetPRReviewStatusService,
        cache_client=redis_client,
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


# Global container instance (lazy-loaded to avoid circular imports)
_container: Container | None = None


def get_container() -> Container:
    """Get the global container instance (lazy-loaded).

    Creates the container on first access to avoid circular import issues.

    Returns:
        Global Container instance.
    """
    global _container  # noqa: PLW0603
    if _container is None:
        _container = create_container()
    return _container


__all__ = ["Container", "create_container", "get_container"]
