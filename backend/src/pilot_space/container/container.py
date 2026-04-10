"""Main DI container with services, AI providers, and wiring configuration.

Container inherits SkillContainer and PluginContainer (both inherit InfraContainer)
to compose all providers while keeping each module under 700 lines.
See _skill_providers.py and _plugin_providers.py for extracted groups.
"""

from __future__ import annotations

from dependency_injector import containers, providers

from pilot_space.ai.infrastructure.approval import ApprovalService
from pilot_space.ai.infrastructure.cost_tracker import CostTracker
from pilot_space.application.services.action_button import ActionButtonService
from pilot_space.application.services.admin_dashboard import AdminDashboardService
from pilot_space.application.services.ai import (
    AttachmentContentService,
    AttachmentUploadService,
    GetPRReviewStatusService,
    TriggerPRReviewService,
)
from pilot_space.application.services.ai.ocr_service import OcrService
from pilot_space.application.services.ai_configuration import AIConfigurationService
from pilot_space.application.services.ai_context import (
    ExportAIContextService,
    GenerateAIContextService,
    GenerateImplementationPlanService,
    RefineAIContextService,
)
from pilot_space.application.services.ai_extraction import CreateExtractedIssuesService
from pilot_space.application.services.ai_governance import GovernanceRollbackService
from pilot_space.application.services.annotation import CreateAnnotationService
from pilot_space.application.services.artifact.artifact_content_service import (
    ArtifactContentService,
)
from pilot_space.application.services.artifact.artifact_upload_service import (
    ArtifactUploadService,
)
from pilot_space.application.services.attachment_management import AttachmentManagementService
from pilot_space.application.services.auth import AuthService, ValidateAPIKeyService
from pilot_space.application.services.block_ownership import BlockOwnershipService
from pilot_space.application.services.capacity_plan import CapacityPlanService
from pilot_space.application.services.cycle import (
    AddIssueToCycleService,
    CreateCycleService,
    GetCycleService,
    RolloverCycleService,
    UpdateCycleService,
)
from pilot_space.application.services.dependency_graph import DependencyGraphService
from pilot_space.application.services.discussion import CreateDiscussionService
from pilot_space.application.services.document.office_extraction_service import (
    OfficeExtractionService,
)
from pilot_space.application.services.feature_toggle import FeatureToggleService
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
from pilot_space.application.services.intent import (
    IntentDetectionService,
    IntentService,
)
from pilot_space.application.services.issue import (
    ActivityService,
    CreateIssueService,
    DeleteIssueService,
    GetImplementContextService,
    GetIssueService,
    ListIssuesService,
    UpdateIssueService,
)
from pilot_space.application.services.mcp_oauth import McpOAuthService
from pilot_space.application.services.mcp_server import McpServerService
from pilot_space.application.services.mcp_tool_execution import MCPToolExecutionService
from pilot_space.application.services.memory.constitution_service import (
    ConstitutionIngestService,
)
from pilot_space.application.services.memory.knowledge_graph_query_service import (
    KnowledgeGraphQueryService,
)
from pilot_space.application.services.memory.memory_lifecycle_service import (
    MemoryLifecycleService,
)
from pilot_space.application.services.memory.memory_list_service import (
    MemoryListService,
)
from pilot_space.application.services.memory.memory_recall_service import (
    MemoryRecallService,
)
from pilot_space.application.services.memory.memory_save_service import (
    MemorySaveService,
)
from pilot_space.application.services.memory.memory_search_service import (
    MemorySearchService,
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
from pilot_space.application.services.note.ai_update_service import NoteAIUpdateService
from pilot_space.application.services.note.move_page_service import MovePageService
from pilot_space.application.services.note.reorder_page_service import ReorderPageService
from pilot_space.application.services.note_template import NoteTemplateService
from pilot_space.application.services.note_write_lock import NoteWriteLock
from pilot_space.application.services.onboarding import (
    CreateGuidedNoteService,
    GetOnboardingService,
    UpdateOnboardingService,
)
from pilot_space.application.services.permissions.permission_cache import PermissionCache
from pilot_space.application.services.permissions.permission_service import PermissionService
from pilot_space.application.services.plugin_lifecycle import PluginLifecycleService
from pilot_space.application.services.pm_block_insight_service import PMBlockInsightService
from pilot_space.application.services.project_detail import ProjectDetailService
from pilot_space.application.services.project_member import ProjectMemberService
from pilot_space.application.services.project_rbac import ProjectRbacService
from pilot_space.application.services.rate_limit import RateLimitService
from pilot_space.application.services.rbac_service import RbacService
from pilot_space.application.services.related_issues import RelatedIssuesSuggestionService
from pilot_space.application.services.role_skill import GenerateRoleSkillService
from pilot_space.application.services.scim_service import ScimService
from pilot_space.application.services.sprint_board import SprintBoardService
from pilot_space.application.services.sso_service import SsoService
from pilot_space.application.services.task_service import TaskService
from pilot_space.application.services.transcription import TranscriptionService
from pilot_space.application.services.version.diff_service import VersionDiffService
from pilot_space.application.services.version.digest_service import VersionDigestService
from pilot_space.application.services.version.impact_service import (
    ImpactAnalysisService,
)
from pilot_space.application.services.version.restore_service import (
    VersionRestoreService,
)
from pilot_space.application.services.version.retention_service import RetentionService
from pilot_space.application.services.version.snapshot_service import (
    VersionSnapshotService,
)
from pilot_space.application.services.workspace import WorkspaceService
from pilot_space.application.services.workspace_ai_settings import WorkspaceAISettingsService
from pilot_space.application.services.workspace_invitation import (
    WorkspaceInvitationService,
)
from pilot_space.application.services.workspace_member import (
    MemberProfileService,
    WorkspaceMemberService,
)
from pilot_space.config import Settings
from pilot_space.container._base import InfraContainer
from pilot_space.container._factories import (
    create_anthropic_client_pool,
    create_llm_gateway,
    create_pilotspace_agent,
    create_provider_selector,
    create_resilient_executor,
    create_secure_key_storage,
    create_session_manager,
    create_space_manager,
    create_tool_registry,
    get_default_redirect_origin,
)
from pilot_space.container._plugin_providers import PluginContainer
from pilot_space.container._skill_providers import SkillContainer
from pilot_space.dependencies.auth import get_current_session
from pilot_space.infrastructure.cache.invite_rate_limiter import InviteRateLimiter
from pilot_space.infrastructure.database.repositories.audit_log_repository import (
    AuditLogRepository,
)
from pilot_space.infrastructure.database.repositories.custom_role_repository import (
    CustomRoleRepository,
)
from pilot_space.infrastructure.database.repositories.issue_link_repository import (
    IssueLinkRepository,
)
from pilot_space.infrastructure.database.repositories.issue_repository import (
    IssueRepository,
)
from pilot_space.infrastructure.database.repositories.note_template_repository import (
    NoteTemplateRepository,
)
from pilot_space.infrastructure.database.repositories.project_member import (
    ProjectMemberRepository,
)
from pilot_space.infrastructure.database.repositories.project_repository import (
    ProjectRepository,
)
from pilot_space.infrastructure.database.repositories.workspace_ai_policy_repository import (
    WorkspaceAIPolicyRepository,
)
from pilot_space.infrastructure.database.repositories.workspace_member_repository import (
    WorkspaceMemberRepository as WorkspaceMemberRbacRepository,
)


def _build_memory_recall_service(
    session: object,
    redis_client: object,
    llm_gateway: object,
) -> MemoryRecallService:
    """Factory for MemoryRecallService that assembles its dependency chain.

    Kept as a free function rather than a web of top-level providers so
    the GraphSearchService / EmbeddingService / AIResponseCache triple
    doesn't leak into the container surface until a route actually needs
    it. Phase 69 Wave 3 will wire this into the agent recall seam.
    """
    from pilot_space.ai.infrastructure.cache import AIResponseCache
    from pilot_space.application.services.embedding_service import (
        EmbeddingConfig,
        EmbeddingService,
    )
    from pilot_space.application.services.memory.graph_search_service import (
        GraphSearchService,
    )
    from pilot_space.infrastructure.database.repositories.knowledge_graph_repository import (
        KnowledgeGraphRepository,
    )

    repo = KnowledgeGraphRepository(session)  # type: ignore[arg-type]
    embedding = EmbeddingService(EmbeddingConfig(), llm_gateway=llm_gateway)  # type: ignore[arg-type]
    graph_search = GraphSearchService(repo, embedding_service=embedding)
    cache = AIResponseCache(redis_client, ttl_seconds=30) if redis_client is not None else None  # type: ignore[arg-type]
    return MemoryRecallService(graph_search=graph_search, embedding=embedding, cache=cache)


class Container(SkillContainer, PluginContainer):
    """Main application DI container.

    Inherits skill providers (SkillContainer) and plugin/seeding providers
    (PluginContainer). Both intermediate containers inherit InfraContainer,
    so all infrastructure providers are available here via MRO.

    Usage:
        container = Container()
        container.wire(modules=[...])

        # Access dependencies
        user_repo = container.user_repository()
    """

    wiring_config = containers.WiringConfiguration(
        modules=[
            "pilot_space.dependencies",
            "pilot_space.api.v1.dependencies",
            "pilot_space.api.v1.dependencies_pilot",
            "pilot_space.api.v1.repository_deps",
            "pilot_space.api.v1.intent_deps",
            "pilot_space.api.v1.dependencies_workspace_skills",
            "pilot_space.api.v1.routers.project_artifacts",
            "pilot_space.api.v1.routers.artifact_annotations",
            "pilot_space.api.v1.routers.notes_ai",
            "pilot_space.api.v1.routers.ai_extraction",
            # LLMGateway migration targets (Plan 47-02)
            "pilot_space.application.services.note.contextual_enrichment",
            "pilot_space.application.services.extraction.extract_issues_service",
            "pilot_space.application.services.memory.graph_extraction_service",
            "pilot_space.application.services.intent.detection_service",
            "pilot_space.application.services.role_skill.generate_role_skill_service",
            "pilot_space.application.services.version.digest_service",
            "pilot_space.ai.jobs.digest_job",
            "pilot_space.application.services.embedding_service",
            "pilot_space.application.services.permissions.permission_service",
            "pilot_space.api.v1.routers.workspace_members",
            "pilot_space.api.v1.routers.workspace_invitations",
            "pilot_space.api.v1.routers.project_members",
            "pilot_space.api.v1.routers.my_projects",
            "pilot_space.api.v1.routers.invitations_public",
            # Phase 69 — AI memory services
            "pilot_space.application.services.memory.memory_recall_service",
            "pilot_space.application.services.memory.memory_lifecycle_service",
        ],
    )

    # AI Infrastructure

    session_manager = providers.Singleton(
        create_session_manager,
        redis_client=InfraContainer.redis_client,
    )

    provider_selector = providers.Singleton(create_provider_selector)

    resilient_executor = providers.Singleton(create_resilient_executor)

    anthropic_client_pool = providers.Singleton(create_anthropic_client_pool)

    tool_registry = providers.Singleton(create_tool_registry)

    space_manager = providers.Singleton(create_space_manager)

    pilotspace_agent = providers.Singleton(
        create_pilotspace_agent,
        tool_registry=tool_registry,
        provider_selector=provider_selector,
        resilient_executor=resilient_executor,
        session_manager=session_manager,
        space_manager=space_manager,
        queue_client=InfraContainer.queue_client,
        session_factory=InfraContainer.session_factory,
    )

    # AI Cost Tracker (AIGOV-06) — Factory so each request gets a session-bound instance
    cost_tracker = providers.Factory(
        CostTracker,
        session=providers.Callable(get_current_session),
    )

    # Secure Key Storage — Factory per request (session-bound)
    secure_key_storage = providers.Factory(create_secure_key_storage)

    # LLM Gateway (Plan 47) — Factory per request (cost_tracker + key_storage are session-bound)
    llm_gateway = providers.Factory(
        create_llm_gateway,
        executor=resilient_executor,
        cost_tracker=cost_tracker,
        key_storage=secure_key_storage,
    )

    # AI Approval Service (DD-003) — Factory per request
    approval_service = providers.Factory(
        ApprovalService,
        session=providers.Callable(get_current_session),
    )

    # AI Policy Repository (AIGOV-01) — Factory per request
    workspace_ai_policy_repository = providers.Factory(
        WorkspaceAIPolicyRepository,
        session=providers.Callable(get_current_session),
    )

    # Audit Log Repository (AUDIT-01) — Factory per request
    audit_log_repository = providers.Factory(
        AuditLogRepository,
        session=providers.Callable(get_current_session),
    )

    # Project Member Repository (RBAC) — Factory per request
    project_member_repository = providers.Factory(
        ProjectMemberRepository,
        session=providers.Callable(get_current_session),
    )

    # Project Member Service (RBAC) — Factory per request
    project_member_service = providers.Factory(
        ProjectMemberService,
        project_member_repository=project_member_repository,
    )

    # Project RBAC Service — centralized permission gates
    project_rbac_service = providers.Factory(
        ProjectRbacService,
        session=providers.Callable(get_current_session),
        project_member_repository=project_member_repository,
    )

    # Action Button Service
    action_button_service = providers.Factory(
        ActionButtonService,
        session=providers.Callable(get_current_session),
    )

    # Block Ownership Service
    block_ownership_service = providers.Factory(
        BlockOwnershipService,
        session=providers.Callable(get_current_session),
        note_repository=InfraContainer.note_repository,
    )

    # Repositories required by refactored services
    project_repository = providers.Factory(
        ProjectRepository,
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

    note_template_repository = providers.Factory(
        NoteTemplateRepository,
        session=providers.Callable(get_current_session),
    )

    # Dependency Graph Service
    dependency_graph_service = providers.Factory(
        DependencyGraphService,
        project_repository=project_repository,
        issue_repository=issue_repository,
        issue_link_repository=issue_link_repository,
    )

    # Note Template Service
    note_template_service = providers.Factory(
        NoteTemplateService,
        session=providers.Callable(get_current_session),
        note_template_repository=note_template_repository,
        workspace_member_repository=InfraContainer.workspace_member_repository,
    )

    # Related Issues Suggestion Service
    related_issues_suggestion_service = providers.Factory(
        RelatedIssuesSuggestionService,
        session=providers.Callable(get_current_session),
        issue_repository=InfraContainer.issue_repository,
        knowledge_graph_repository=InfraContainer.knowledge_graph_repository,
        issue_suggestion_dismissal_repository=InfraContainer.issue_suggestion_dismissal_repository,
    )

    # Workspace AI Settings Service
    workspace_ai_settings_service = providers.Factory(
        WorkspaceAISettingsService,
        session=providers.Callable(get_current_session),
        workspace_repository=InfraContainer.workspace_repository,
    )

    # Sprint Board Service
    sprint_board_service = providers.Factory(
        SprintBoardService,
        session=providers.Callable(get_current_session),
        pm_block_queries_repository=InfraContainer.pm_block_queries_repository,
    )

    # Capacity Plan Service
    capacity_plan_service = providers.Factory(
        CapacityPlanService,
        session=providers.Callable(get_current_session),
        pm_block_queries_repository=InfraContainer.pm_block_queries_repository,
    )

    # Rate Limit Service — Redis-backed INCR+EXPIRE
    rate_limit_service = providers.Factory(
        RateLimitService,
        redis=InfraContainer.redis_client,
    )

    # MCP Server Service — CRUD, validation, encryption, status probing
    mcp_server_service = providers.Factory(
        McpServerService,
        session=providers.Callable(get_current_session),
        workspace_mcp_server_repository=InfraContainer.workspace_mcp_server_repository,
    )

    # MCP Tool Execution Service — tool discovery and execution
    mcp_tool_execution_service = providers.Factory(
        MCPToolExecutionService,
        session=providers.Callable(get_current_session),
    )

    # Project Detail Service — aggregation, validation, KG enqueue
    project_detail_service = providers.Factory(
        ProjectDetailService,
        session=providers.Callable(get_current_session),
        project_repository=InfraContainer.project_repository,
        workspace_repository=InfraContainer.workspace_repository,
    )

    # MCP OAuth Service — OAuth 2.0 authorization flows
    mcp_oauth_service = providers.Factory(
        McpOAuthService,
        session=providers.Callable(get_current_session),
        redis=InfraContainer.redis_client,
        workspace_mcp_server_repository=InfraContainer.workspace_mcp_server_repository,
    )

    # Attachment Management Service — quota, extraction, ingest
    attachment_management_service = providers.Factory(
        AttachmentManagementService,
        session=providers.Callable(get_current_session),
        storage_client=InfraContainer.storage_client,
        workspace_member_repository=InfraContainer.workspace_member_repository,
        chat_attachment_repository=InfraContainer.chat_attachment_repository,
        ocr_result_repository=InfraContainer.ocr_result_repository,
    )

    # Feature Toggle Service
    feature_toggle_service = providers.Factory(
        FeatureToggleService,
        session=providers.Callable(get_current_session),
    )

    # SCIM Service (AUTH-07)
    scim_service = providers.Factory(
        ScimService,
        workspace_repo=InfraContainer.workspace_repository,
        user_repo=InfraContainer.user_repository,
        supabase_admin_client=InfraContainer.supabase_auth,
    )

    # ===== Service Factories =====

    # Issue Services
    create_issue_service = providers.Factory(
        CreateIssueService,
        session=providers.Callable(get_current_session),
        issue_repository=InfraContainer.issue_repository,
        activity_repository=InfraContainer.activity_repository,
        label_repository=InfraContainer.label_repository,
        queue=InfraContainer.queue_client,
        audit_log_repository=audit_log_repository,
    )

    update_issue_service = providers.Factory(
        UpdateIssueService,
        session=providers.Callable(get_current_session),
        issue_repository=InfraContainer.issue_repository,
        activity_repository=InfraContainer.activity_repository,
        label_repository=InfraContainer.label_repository,
        queue=InfraContainer.queue_client,
        audit_log_repository=audit_log_repository,
    )

    get_issue_service = providers.Factory(
        GetIssueService,
        issue_repository=InfraContainer.issue_repository,
    )

    list_issues_service = providers.Factory(
        ListIssuesService,
        issue_repository=InfraContainer.issue_repository,
    )

    activity_service = providers.Factory(
        ActivityService,
        activity_repository=InfraContainer.activity_repository,
    )

    # Note Services
    create_note_service = providers.Factory(
        CreateNoteService,
        session=providers.Callable(get_current_session),
        note_repository=InfraContainer.note_repository,
        template_repository=InfraContainer.template_repository,
        queue=InfraContainer.queue_client,
        audit_log_repository=audit_log_repository,
    )

    update_note_service = providers.Factory(
        UpdateNoteService,
        session=providers.Callable(get_current_session),
        note_repository=InfraContainer.note_repository,
        queue=InfraContainer.queue_client,
        audit_log_repository=audit_log_repository,
    )

    get_note_service = providers.Factory(
        GetNoteService,
        session=providers.Callable(get_current_session),
        note_repository=InfraContainer.note_repository,
    )

    create_note_from_chat_service = providers.Factory(
        CreateNoteFromChatService,
        session=providers.Callable(get_current_session),
        note_repository=InfraContainer.note_repository,
    )

    ai_update_note_service = providers.Factory(
        NoteAIUpdateService,
        session=providers.Callable(get_current_session),
        note_repository=InfraContainer.note_repository,
    )

    list_notes_service = providers.Factory(
        ListNotesService,
        session=providers.Callable(get_current_session),
        note_repository=InfraContainer.note_repository,
    )

    delete_note_service = providers.Factory(
        DeleteNoteService,
        session=providers.Callable(get_current_session),
        note_repository=InfraContainer.note_repository,
        audit_log_repository=audit_log_repository,
    )

    pin_note_service = providers.Factory(
        PinNoteService,
        session=providers.Callable(get_current_session),
        note_repository=InfraContainer.note_repository,
    )

    move_page_service = providers.Factory(
        MovePageService,
        session=providers.Callable(get_current_session),
        note_repository=InfraContainer.note_repository,
    )

    reorder_page_service = providers.Factory(
        ReorderPageService,
        session=providers.Callable(get_current_session),
        note_repository=InfraContainer.note_repository,
    )

    list_annotations_service = providers.Factory(
        ListAnnotationsService,
        session=providers.Callable(get_current_session),
        annotation_repository=InfraContainer.note_annotation_repository,
    )

    update_annotation_service = providers.Factory(
        UpdateAnnotationService,
        session=providers.Callable(get_current_session),
        annotation_repository=InfraContainer.note_annotation_repository,
    )

    # Issue Delete Service
    delete_issue_service = providers.Factory(
        DeleteIssueService,
        session=providers.Callable(get_current_session),
        issue_repository=InfraContainer.issue_repository,
        activity_repository=InfraContainer.activity_repository,
        audit_log_repository=audit_log_repository,
    )

    # Issue Implement Context Service
    get_implement_context_service = providers.Factory(
        GetImplementContextService,
        issue_repository=InfraContainer.issue_repository,
        note_issue_link_repository=InfraContainer.note_issue_link_repository,
        note_repository=InfraContainer.note_repository,
        integration_repository=InfraContainer.integration_repository,
        workspace_repository=InfraContainer.workspace_repository,
    )

    # Cycle Services
    create_cycle_service = providers.Factory(
        CreateCycleService,
        session=providers.Callable(get_current_session),
        cycle_repository=InfraContainer.cycle_repository,
        queue=InfraContainer.queue_client,
        audit_log_repository=audit_log_repository,
    )

    update_cycle_service = providers.Factory(
        UpdateCycleService,
        session=providers.Callable(get_current_session),
        cycle_repository=InfraContainer.cycle_repository,
        queue=InfraContainer.queue_client,
        audit_log_repository=audit_log_repository,
    )

    get_cycle_service = providers.Factory(
        GetCycleService,
        cycle_repository=InfraContainer.cycle_repository,
    )

    add_issue_to_cycle_service = providers.Factory(
        AddIssueToCycleService,
        session=providers.Callable(get_current_session),
        issue_repository=InfraContainer.issue_repository,
        cycle_repository=InfraContainer.cycle_repository,
        activity_repository=InfraContainer.activity_repository,
        audit_log_repository=audit_log_repository,
    )

    rollover_cycle_service = providers.Factory(
        RolloverCycleService,
        session=providers.Callable(get_current_session),
        cycle_repository=InfraContainer.cycle_repository,
        issue_repository=InfraContainer.issue_repository,
    )

    # AI Context Services
    generate_ai_context_service = providers.Factory(
        GenerateAIContextService,
        session=providers.Callable(get_current_session),
        ai_context_repository=InfraContainer.ai_context_repository,
        issue_repository=InfraContainer.issue_repository,
        note_repository=InfraContainer.note_repository,
        integration_link_repository=InfraContainer.integration_link_repository,
        pilotspace_agent=pilotspace_agent,
        tool_registry=tool_registry,
        provider_selector=provider_selector,
        cost_tracker=cost_tracker,
        resilient_executor=resilient_executor,
    )

    refine_ai_context_service = providers.Factory(
        RefineAIContextService,
        session=providers.Callable(get_current_session),
        ai_context_repository=InfraContainer.ai_context_repository,
        issue_repository=InfraContainer.issue_repository,
        pilotspace_agent=pilotspace_agent,
        tool_registry=tool_registry,
        provider_selector=provider_selector,
        cost_tracker=cost_tracker,
        resilient_executor=resilient_executor,
    )

    export_ai_context_service = providers.Factory(
        ExportAIContextService,
        session=providers.Callable(get_current_session),
        ai_context_repository=InfraContainer.ai_context_repository,
        issue_repository=InfraContainer.issue_repository,
    )

    generate_plan_service = providers.Factory(
        GenerateImplementationPlanService,
        session=providers.Callable(get_current_session),
        ai_context_repository=InfraContainer.ai_context_repository,
        issue_repository=InfraContainer.issue_repository,
        pilotspace_agent=pilotspace_agent,
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
        integration_repo=InfraContainer.integration_repository,
    )

    process_github_webhook_service = providers.Factory(
        ProcessGitHubWebhookService,
        session=providers.Callable(get_current_session),
        integration_repo=InfraContainer.integration_repository,
        integration_link_repo=InfraContainer.integration_link_repository,
        issue_repo=InfraContainer.issue_repository,
        activity_repo=InfraContainer.activity_repository,
        webhook_handler=providers.Callable(
            lambda: None
        ),  # GitHubWebhookHandler instantiated per request
        sync_service=providers.Callable(lambda: None),  # GitHubSyncService per request
    )

    link_commit_service = providers.Factory(
        LinkCommitService,
        session=providers.Callable(get_current_session),
        integration_repo=InfraContainer.integration_repository,
        integration_link_repo=InfraContainer.integration_link_repository,
        issue_repo=InfraContainer.issue_repository,
        activity_repo=InfraContainer.activity_repository,
    )

    auto_transition_service = providers.Factory(
        AutoTransitionService,
        session=providers.Callable(get_current_session),
        issue_repo=InfraContainer.issue_repository,
        activity_repo=InfraContainer.activity_repository,
    )

    # Onboarding Services
    create_guided_note_service = providers.Factory(
        CreateGuidedNoteService,
        session=providers.Callable(get_current_session),
        onboarding_repository=InfraContainer.onboarding_repository,
        note_repository=InfraContainer.note_repository,
    )

    get_onboarding_service = providers.Factory(
        GetOnboardingService,
        session=providers.Callable(get_current_session),
        onboarding_repository=InfraContainer.onboarding_repository,
    )

    update_onboarding_service = providers.Factory(
        UpdateOnboardingService,
        session=providers.Callable(get_current_session),
        onboarding_repository=InfraContainer.onboarding_repository,
    )

    # Homepage Services
    get_activity_service = providers.Factory(
        GetActivityService,
        session=providers.Callable(get_current_session),
        homepage_repository=InfraContainer.homepage_repository,
    )

    get_digest_service = providers.Factory(
        GetDigestService,
        session=providers.Callable(get_current_session),
        digest_repository=InfraContainer.digest_repository,
    )

    dismiss_suggestion_service = providers.Factory(
        DismissSuggestionService,
        session=providers.Callable(get_current_session),
    )

    # Workspace Services
    workspace_service = providers.Factory(
        WorkspaceService,
        workspace_repo=InfraContainer.workspace_repository,
        user_repo=InfraContainer.user_repository,
        invitation_repo=InfraContainer.invitation_repository,
        label_repo=InfraContainer.label_repository,
        queue=InfraContainer.queue_client,
    )

    workspace_member_service = providers.Factory(
        WorkspaceMemberService,
        workspace_repo=InfraContainer.workspace_repository,
    )

    member_profile_service = providers.Factory(
        MemberProfileService,
        session=providers.Callable(get_current_session),
        workspace_repo=InfraContainer.workspace_repository,
    )

    workspace_invitation_service = providers.Factory(
        WorkspaceInvitationService,
        workspace_repo=InfraContainer.workspace_repository,
        invitation_repo=InfraContainer.invitation_repository,
    )

    # Auth Service
    auth_service = providers.Factory(
        AuthService,
        user_repo=InfraContainer.user_repository,
        supabase_url=providers.Callable(lambda s: s.supabase_url, InfraContainer.config),
        default_redirect_origin=providers.Callable(
            get_default_redirect_origin,
            InfraContainer.config,
        ),
    )

    # CLI API Key Validation Service
    validate_api_key_service = providers.Factory(
        ValidateAPIKeyService,
        api_key_repository=InfraContainer.pilot_api_key_repository,
        workspace_repository=InfraContainer.workspace_repository,
    )

    # AI Services (PR Review)
    trigger_pr_review_service = providers.Factory(
        TriggerPRReviewService,
        session=providers.Callable(get_current_session),
        queue_client=InfraContainer.queue_client,
        integration_repo=InfraContainer.integration_repository,
        cache_client=InfraContainer.redis_client,
    )

    get_pr_review_status_service = providers.Factory(
        GetPRReviewStatusService,
        cache_client=InfraContainer.redis_client,
    )

    # Attachment Services
    attachment_upload_service = providers.Factory(
        AttachmentUploadService,
        session=providers.Callable(get_current_session),
        storage_client=InfraContainer.storage_client,
        attachment_repo=InfraContainer.chat_attachment_repository,
    )

    office_extraction_service = providers.Factory(
        OfficeExtractionService,
    )

    ocr_service = providers.Factory(
        OcrService,
        master_secret=InfraContainer.encryption_key,
    )

    attachment_content_service = providers.Factory(
        AttachmentContentService,
        storage_client=InfraContainer.storage_client,
        office_extraction=office_extraction_service,
        ocr_service=ocr_service,
        session=providers.Callable(get_current_session),
    )

    # Transcription Service (ElevenLabs STT with cache + storage)
    transcription_service = providers.Factory(
        TranscriptionService,
        session=providers.Callable(get_current_session),
        storage_client=InfraContainer.storage_client,
        encryption_key=InfraContainer.encryption_key,
    )

    # Artifact Services (v1.1 — note file uploads; ARTF-04, ARTF-05, ARTF-06)
    artifact_upload_service = providers.Factory(
        ArtifactUploadService,
        session=providers.Callable(get_current_session),
        storage_client=InfraContainer.storage_client,
        artifact_repo=InfraContainer.artifact_repository,
    )

    # Artifact Content Service (Phase 62 — Monaco IDE; IDE-03)
    artifact_content_service = providers.Factory(
        ArtifactContentService,
        session=providers.Callable(get_current_session),
        storage_client=InfraContainer.storage_client,
    )

    # Task Services
    task_service = providers.Factory(
        TaskService,
        session=providers.Callable(get_current_session),
        task_repository=InfraContainer.task_repository,
        issue_repository=InfraContainer.issue_repository,
    )

    # Intent Services
    intent_detection_service = providers.Factory(
        IntentDetectionService,
        session=providers.Callable(get_current_session),
        intent_repository=InfraContainer.work_intent_repository,
        redis_client=InfraContainer.redis_client,
        llm_gateway=llm_gateway,
    )

    # Override SkillContainer's generate_role_skill_service to inject llm_gateway
    generate_role_skill_service = providers.Factory(
        GenerateRoleSkillService,
        session=providers.Callable(get_current_session),
        llm_gateway=llm_gateway,
    )

    intent_service = providers.Factory(
        IntentService,
        session=providers.Callable(get_current_session),
        intent_repository=InfraContainer.work_intent_repository,
    )

    # Note Write Lock (C-3) — Redis-backed mutex, one per process
    note_write_lock = providers.Singleton(
        NoteWriteLock,
        redis_client=InfraContainer.redis_client,
    )

    # Invite Rate Limiter (028-invite-magic-link) — Redis fixed-window counter
    invite_rate_limiter = providers.Singleton(
        InviteRateLimiter,
        redis_client=InfraContainer.redis_client,
    )

    # Note Version Services
    version_snapshot_service = providers.Factory(
        VersionSnapshotService,
        session=providers.Callable(get_current_session),
        note_repo=InfraContainer.note_repository,
        version_repo=InfraContainer.note_version_repository,
    )

    version_diff_service = providers.Factory(
        VersionDiffService,
        session=providers.Callable(get_current_session),
        version_repo=InfraContainer.note_version_repository,
    )

    version_digest_service = providers.Factory(
        VersionDigestService,
        session=providers.Callable(get_current_session),
        version_repo=InfraContainer.note_version_repository,
        llm_gateway=llm_gateway,
    )

    version_restore_service = providers.Factory(
        VersionRestoreService,
        session=providers.Callable(get_current_session),
        note_repo=InfraContainer.note_repository,
        version_repo=InfraContainer.note_version_repository,
    )

    version_retention_service = providers.Factory(
        RetentionService,
        session=providers.Callable(get_current_session),
        version_repo=InfraContainer.note_version_repository,
    )

    version_impact_service = providers.Factory(
        ImpactAnalysisService,
        session=providers.Callable(get_current_session),
        version_repo=InfraContainer.note_version_repository,
    )

    # PM Block Insight Service
    pm_block_insight_service = providers.Factory(
        PMBlockInsightService,
        session=providers.Callable(get_current_session),
        repository=InfraContainer.pm_block_insight_repository,
    )

    # Memory Services
    memory_search_service = providers.Factory(
        MemorySearchService,
        session=providers.Callable(get_current_session),
        memory_repository=InfraContainer.memory_entry_repository,
    )

    memory_save_service = providers.Factory(
        MemorySaveService,
        session=providers.Callable(get_current_session),
        memory_repository=InfraContainer.memory_entry_repository,
        queue=InfraContainer.queue_client,
    )

    constitution_service = providers.Factory(
        ConstitutionIngestService,
        session=providers.Callable(get_current_session),
        constitution_repository=InfraContainer.constitution_rule_repository,
        queue=InfraContainer.queue_client,
    )

    # --- Phase 69: MemoryRecallService + MemoryLifecycleService ---
    # Both services are request-scoped because they wrap a session-bound
    # repository. They use factory functions (_build_*) to assemble the
    # dependency chain (GraphSearchService / GraphWriteService / etc.) without
    # promoting those to top-level providers yet.
    memory_recall_service = providers.Factory(
        _build_memory_recall_service,
        session=providers.Callable(get_current_session),
        redis_client=InfraContainer.redis_client,
        llm_gateway=llm_gateway,
    )

    memory_lifecycle_service = providers.Factory(
        MemoryLifecycleService,
        session=providers.Callable(get_current_session),
    )

    memory_list_service = providers.Factory(
        MemoryListService,
        session=providers.Callable(get_current_session),
        recall_service=memory_recall_service,
        lifecycle_service=memory_lifecycle_service,
    )

    # Knowledge Graph Query Service
    knowledge_graph_query_service = providers.Factory(
        KnowledgeGraphQueryService,
        knowledge_graph_repository=InfraContainer.knowledge_graph_repository,
        integration_link_repository=InfraContainer.integration_link_repository,
        issue_repository=InfraContainer.issue_repository,
        project_repository=InfraContainer.project_repository,
    )

    # SSO Service (AUTH-01 through AUTH-04)
    sso_service = providers.Factory(
        SsoService,
        workspace_repo=InfraContainer.workspace_repository,
        supabase_admin_client=InfraContainer.supabase_auth,
    )

    # RBAC repositories and service (AUTH-05)
    custom_role_repository = providers.Factory(
        CustomRoleRepository,
        session=providers.Callable(get_current_session),
    )

    workspace_member_rbac_repository = providers.Factory(
        WorkspaceMemberRbacRepository,
        session=providers.Callable(get_current_session),
    )

    rbac_service = providers.Factory(
        RbacService,
        custom_role_repo=custom_role_repository,
        workspace_member_repo=workspace_member_rbac_repository,
        audit_log_repository=audit_log_repository,
    )

    # Admin Dashboard Service (TENANT-04) — Redis optional, no session needed
    admin_dashboard_service = providers.Factory(
        AdminDashboardService,
        redis=InfraContainer.redis_client,
    )

    # AI Extraction Service — creates issues from AI extraction results
    create_extracted_issues_service = providers.Factory(
        CreateExtractedIssuesService,
        session=providers.Callable(get_current_session),
        project_repository=InfraContainer.project_repository,
        issue_repository=InfraContainer.issue_repository,
        activity_repository=InfraContainer.activity_repository,
        label_repository=InfraContainer.label_repository,
        note_issue_link_repository=InfraContainer.note_issue_link_repository,
    )

    # AI Governance Service — rollback, policy CRUD, BYOK status
    governance_rollback_service = providers.Factory(
        GovernanceRollbackService,
        session=providers.Callable(get_current_session),
        workspace_repository=InfraContainer.workspace_repository,
        audit_log_repository=audit_log_repository,
        workspace_ai_policy_repository=workspace_ai_policy_repository,
        update_issue_service=update_issue_service,
        update_note_service=update_note_service,
    )

    # Plugin Lifecycle Service — browse, toggle, uninstall, update checks
    plugin_lifecycle_service = providers.Factory(
        PluginLifecycleService,
        session=providers.Callable(get_current_session),
        redis=InfraContainer.redis_client,
        workspace_github_credential_repository=InfraContainer.workspace_github_credential_repository,
        workspace_plugin_repository=InfraContainer.workspace_plugin_repository,
        skill_action_button_repository=InfraContainer.skill_action_button_repository,
    )

    # AI Configuration Service — workspace-level LLM provider management
    ai_configuration_service = providers.Factory(
        AIConfigurationService,
        session=providers.Callable(get_current_session),
        workspace_repository=InfraContainer.workspace_repository,
    )

    # Phase 69 — Granular AI Tool Permissions (69-03)
    # Singleton cache + singleton service; the service reads the
    # request-scoped AsyncSession via get_current_session() at call time.
    permission_cache = providers.Singleton(PermissionCache)
    permission_service = providers.Singleton(
        PermissionService,
        cache=permission_cache,
        redis_client=InfraContainer.redis_client,
    )


def create_container(settings: Settings | None = None) -> Container:
    """Create and configure the DI container (settings override for testing)."""
    container = Container()
    if settings is not None:
        container.config.override(providers.Object(settings))  # type: ignore[no-untyped-call]
    return container


# Global container instance (lazy-loaded to avoid circular imports)
# Uses a list to avoid `global` statement (PLW0603)
_container: list[Container] = []


def get_container() -> Container:
    """Get or create the global container instance."""
    if not _container:
        _container.append(create_container())
    return _container[0]
