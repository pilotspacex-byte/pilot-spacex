"""Infrastructure container with config, auth, repositories, and clients.

InfraContainer is the base container inherited by Container.
It holds all infrastructure-level providers (config, DB, auth, repositories,
and external clients like Redis and queue).
"""

from __future__ import annotations

from dependency_injector import containers, providers

from pilot_space.config import get_settings
from pilot_space.container._factories import (
    create_queue_client,
    create_redis_client,
    get_encryption_key_from_config,
)
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
from pilot_space.infrastructure.database.repositories.artifact_annotation_repository import (
    ArtifactAnnotationRepository,
)
from pilot_space.infrastructure.database.repositories.artifact_repository import (
    ArtifactRepository,
)
from pilot_space.infrastructure.database.repositories.chat_attachment_repository import (
    ChatAttachmentRepository,
)
from pilot_space.infrastructure.database.repositories.constitution_repository import (
    ConstitutionRuleRepository,
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
from pilot_space.infrastructure.database.repositories.drive_credential_repository import (
    DriveCredentialRepository,
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
from pilot_space.infrastructure.database.repositories.intent_artifact_repository import (
    IntentArtifactRepository,
)
from pilot_space.infrastructure.database.repositories.intent_repository import (
    WorkIntentRepository,
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
from pilot_space.infrastructure.database.repositories.issue_suggestion_dismissal_repository import (
    IssueSuggestionDismissalRepository,
)
from pilot_space.infrastructure.database.repositories.knowledge_graph_repository import (
    KnowledgeGraphRepository,
)
from pilot_space.infrastructure.database.repositories.label_repository import (
    LabelRepository,
)
from pilot_space.infrastructure.database.repositories.memory_repository import (
    MemoryEntryRepository,
)
from pilot_space.infrastructure.database.repositories.note_annotation_repository import (
    NoteAnnotationRepository,
)
from pilot_space.infrastructure.database.repositories.note_issue_link_repository import (
    NoteIssueLinkRepository,
)
from pilot_space.infrastructure.database.repositories.note_note_link_repository import (
    NoteNoteLinkRepository,
)
from pilot_space.infrastructure.database.repositories.note_repository import (
    NoteRepository,
)
from pilot_space.infrastructure.database.repositories.note_version_repository import (
    NoteVersionRepository,
)
from pilot_space.infrastructure.database.repositories.note_yjs_state_repository import (
    NoteYjsStateRepository,
)
from pilot_space.infrastructure.database.repositories.ocr_result_repository import (
    OcrResultRepository,
)
from pilot_space.infrastructure.database.repositories.onboarding_repository import (
    OnboardingRepository,
)
from pilot_space.infrastructure.database.repositories.pilot_api_key_repository import (
    PilotAPIKeyRepository,
)
from pilot_space.infrastructure.database.repositories.pm_block_insight_repository import (
    PMBlockInsightRepository,
)
from pilot_space.infrastructure.database.repositories.pm_block_queries_repository import (
    PMBlockQueriesRepository,
)
from pilot_space.infrastructure.database.repositories.project_repository import (
    ProjectRepository,
)
from pilot_space.infrastructure.database.repositories.role_skill_repository import (
    RoleSkillRepository,
)
from pilot_space.infrastructure.database.repositories.skill_action_button_repository import (
    SkillActionButtonRepository,
)
from pilot_space.infrastructure.database.repositories.skill_execution_repository import (
    SkillExecutionRepository,
)
from pilot_space.infrastructure.database.repositories.task_repository import (
    TaskRepository,
)
from pilot_space.infrastructure.database.repositories.template_repository import (
    TemplateRepository,
)
from pilot_space.infrastructure.database.repositories.user_repository import (
    UserRepository,
)
from pilot_space.infrastructure.database.repositories.workspace_github_credential_repository import (
    WorkspaceGithubCredentialRepository,
)
from pilot_space.infrastructure.database.repositories.workspace_mcp_server_repository import (
    WorkspaceMcpServerRepository,
)
from pilot_space.infrastructure.database.repositories.workspace_member_repository import (
    WorkspaceMemberRepository,
)
from pilot_space.infrastructure.database.repositories.workspace_plugin_repository import (
    WorkspacePluginRepository,
)
from pilot_space.infrastructure.database.repositories.workspace_repository import (
    WorkspaceRepository,
)
from pilot_space.infrastructure.storage.client import SupabaseStorageClient


class InfraContainer(containers.DeclarativeContainer):
    """Infrastructure-level DI container.

    Provides config, database, auth, repositories, and infrastructure clients.
    Inherited by Container which adds services, AI providers, and wiring.
    """

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

    artifact_repository = providers.Factory(
        ArtifactRepository,
        session=providers.Callable(get_current_session),
    )

    artifact_annotation_repository = providers.Factory(
        ArtifactAnnotationRepository,
        session=providers.Callable(get_current_session),
    )

    chat_attachment_repository = providers.Factory(
        ChatAttachmentRepository,
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

    drive_credential_repository = providers.Factory(
        DriveCredentialRepository,
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

    note_version_repository = providers.Factory(
        NoteVersionRepository,
        session=providers.Callable(get_current_session),
    )

    note_yjs_state_repository = providers.Factory(
        NoteYjsStateRepository,
        session=providers.Callable(get_current_session),
    )

    pm_block_insight_repository = providers.Factory(
        PMBlockInsightRepository,
        session=providers.Callable(get_current_session),
    )

    pm_block_queries_repository = providers.Factory(
        PMBlockQueriesRepository,
        session=providers.Callable(get_current_session),
    )

    note_issue_link_repository = providers.Factory(
        NoteIssueLinkRepository,
        session=providers.Callable(get_current_session),
    )

    note_note_link_repository = providers.Factory(
        NoteNoteLinkRepository,
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

    task_repository = providers.Factory(
        TaskRepository,
        session=providers.Callable(get_current_session),
    )

    work_intent_repository = providers.Factory(
        WorkIntentRepository,
        session=providers.Callable(get_current_session),
    )

    intent_artifact_repository = providers.Factory(
        IntentArtifactRepository,
        session=providers.Callable(get_current_session),
    )

    skill_execution_repository = providers.Factory(
        SkillExecutionRepository,
        session=providers.Callable(get_current_session),
    )

    memory_entry_repository = providers.Factory(
        MemoryEntryRepository,
        session=providers.Callable(get_current_session),
    )

    knowledge_graph_repository = providers.Factory(
        KnowledgeGraphRepository,
        session=providers.Callable(get_current_session),
    )

    issue_suggestion_dismissal_repository = providers.Factory(
        IssueSuggestionDismissalRepository,
        session=providers.Callable(get_current_session),
    )

    constitution_rule_repository = providers.Factory(
        ConstitutionRuleRepository,
        session=providers.Callable(get_current_session),
    )

    pilot_api_key_repository = providers.Factory(
        PilotAPIKeyRepository,
        session=providers.Callable(get_current_session),
    )

    workspace_member_repository = providers.Factory(
        WorkspaceMemberRepository,
        session=providers.Callable(get_current_session),
    )

    ocr_result_repository = providers.Factory(
        OcrResultRepository,
        session=providers.Callable(get_current_session),
    )

    workspace_github_credential_repository = providers.Factory(
        WorkspaceGithubCredentialRepository,
        session=providers.Callable(get_current_session),
    )

    workspace_mcp_server_repository = providers.Factory(
        WorkspaceMcpServerRepository,
        session=providers.Callable(get_current_session),
    )

    workspace_plugin_repository = providers.Factory(
        WorkspacePluginRepository,
        session=providers.Callable(get_current_session),
    )

    skill_action_button_repository = providers.Factory(
        SkillActionButtonRepository,
        session=providers.Callable(get_current_session),
    )

    # Infrastructure clients

    queue_client = providers.Singleton(create_queue_client)
    redis_client = providers.Singleton(create_redis_client)
    storage_client = providers.Singleton(SupabaseStorageClient)

    encryption_key = providers.Factory(
        get_encryption_key_from_config,
        settings=config,
    )
