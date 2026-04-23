"""Type aliases for service dependency injection via dependency-injector + FastAPI."""

from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import Depends

from pilot_space.ai.infrastructure.approval import ApprovalService
from pilot_space.api.v1.repository_deps import (
    ActivityRepositoryDep,
    CycleRepositoryDep,
    InvitationRepositoryDep,
    IssueRepositoryDep,
    NoteIssueLinkRepositoryDep,
    NoteRepositoryDep,
    ProjectRepositoryDep,
    UserRepositoryDep,
    WorkspaceRepositoryDep,
)
from pilot_space.application.services.action_button import ActionButtonService
from pilot_space.application.services.admin_dashboard import AdminDashboardService
from pilot_space.application.services.ai_configuration import AIConfigurationService
from pilot_space.application.services.ai_context import (
    ExportAIContextService,
    GenerateAIContextService,
    GenerateImplementationPlanService,
    RefineAIContextService,
)
from pilot_space.application.services.ai_extraction import CreateExtractedIssuesService
from pilot_space.application.services.ai_governance import GovernanceRollbackService
from pilot_space.application.services.annotation import (
    CreateAnnotationService,
)
from pilot_space.application.services.artifact.artifact_content_service import (
    ArtifactContentService,
)
from pilot_space.application.services.attachment_management import AttachmentManagementService
from pilot_space.application.services.auth import AuthService
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
from pilot_space.application.services.discussion import (
    CreateDiscussionService,
)
from pilot_space.application.services.feature_toggle import FeatureToggleService
from pilot_space.application.services.homepage import (
    DismissSuggestionService,
    GetActivityService,
    GetDigestService,
)
from pilot_space.application.services.hooks.hook_rule_service import HookRuleService
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
from pilot_space.application.services.mcp_oauth import McpOAuthService
from pilot_space.application.services.mcp_server import McpServerService
from pilot_space.application.services.mcp_tool_execution import MCPToolExecutionService
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
from pilot_space.application.services.ocr_configuration import OcrConfigurationService
from pilot_space.application.services.onboarding import (
    CreateGuidedNoteService,
    GetOnboardingService,
    UpdateOnboardingService,
)
from pilot_space.application.services.permissions.permission_service import PermissionService
from pilot_space.application.services.plugin_lifecycle import PluginLifecycleService
from pilot_space.application.services.pm_block_insight_service import PMBlockInsightService
from pilot_space.application.services.project_detail import ProjectDetailService
from pilot_space.application.services.project_member import ProjectMemberService
from pilot_space.application.services.project_rbac import ProjectRbacService
from pilot_space.application.services.rate_limit import RateLimitService
from pilot_space.application.services.rbac_service import RbacService
from pilot_space.application.services.related_issues import RelatedIssuesSuggestionService
from pilot_space.application.services.role_skill import (
    CreateRoleSkillService,
    DeleteRoleSkillService,
    GenerateRoleSkillService,
    ListRoleSkillsService,
    UpdateRoleSkillService,
)
from pilot_space.application.services.scim_service import ScimService
from pilot_space.application.services.sprint_board import SprintBoardService
from pilot_space.application.services.task_service import TaskService
from pilot_space.application.services.transcription import TranscriptionService
from pilot_space.application.services.workspace import WorkspaceService
from pilot_space.application.services.workspace_ai_settings import WorkspaceAISettingsService
from pilot_space.application.services.workspace_invitation import WorkspaceInvitationService
from pilot_space.application.services.workspace_member import (
    MemberProfileService,
    WorkspaceMemberService,
)
from pilot_space.container import Container
from pilot_space.dependencies.ai import get_key_storage
from pilot_space.infrastructure.cache.invite_rate_limiter import InviteRateLimiter

# ===== Action Button Service Dependencies =====


@inject
def _get_action_button_service(
    svc: ActionButtonService = Depends(Provide[Container.action_button_service]),
) -> ActionButtonService:
    return svc


ActionButtonServiceDep = Annotated[ActionButtonService, Depends(_get_action_button_service)]

# ===== Block Ownership Service Dependencies =====


@inject
def _get_block_ownership_service(
    svc: BlockOwnershipService = Depends(Provide[Container.block_ownership_service]),
) -> BlockOwnershipService:
    return svc


BlockOwnershipServiceDep = Annotated[BlockOwnershipService, Depends(_get_block_ownership_service)]

# ===== Dependency Graph Service Dependencies =====


@inject
def _get_dependency_graph_service(
    svc: DependencyGraphService = Depends(Provide[Container.dependency_graph_service]),
) -> DependencyGraphService:
    return svc


DependencyGraphServiceDep = Annotated[
    DependencyGraphService, Depends(_get_dependency_graph_service)
]

# ===== Note Template Service Dependencies =====


@inject
def _get_note_template_service(
    svc: NoteTemplateService = Depends(Provide[Container.note_template_service]),
) -> NoteTemplateService:
    return svc


NoteTemplateServiceDep = Annotated[NoteTemplateService, Depends(_get_note_template_service)]

# ===== Related Issues Suggestion Service Dependencies =====


@inject
def _get_related_issues_suggestion_service(
    svc: RelatedIssuesSuggestionService = Depends(
        Provide[Container.related_issues_suggestion_service]
    ),
) -> RelatedIssuesSuggestionService:
    return svc


RelatedIssuesSuggestionServiceDep = Annotated[
    RelatedIssuesSuggestionService, Depends(_get_related_issues_suggestion_service)
]

# ===== Issue Service Dependencies =====


@inject
def _get_create_issue_service(
    svc: CreateIssueService = Depends(Provide[Container.create_issue_service]),
) -> CreateIssueService:
    return svc


CreateIssueServiceDep = Annotated[CreateIssueService, Depends(_get_create_issue_service)]


@inject
def _get_update_issue_service(
    svc: UpdateIssueService = Depends(Provide[Container.update_issue_service]),
) -> UpdateIssueService:
    return svc


UpdateIssueServiceDep = Annotated[UpdateIssueService, Depends(_get_update_issue_service)]


@inject
def _get_get_issue_service(
    svc: GetIssueService = Depends(Provide[Container.get_issue_service]),
) -> GetIssueService:
    return svc


GetIssueServiceDep = Annotated[GetIssueService, Depends(_get_get_issue_service)]


@inject
def _get_list_issues_service(
    svc: ListIssuesService = Depends(Provide[Container.list_issues_service]),
) -> ListIssuesService:
    return svc


ListIssuesServiceDep = Annotated[ListIssuesService, Depends(_get_list_issues_service)]


@inject
def _get_activity_service(
    svc: ActivityService = Depends(Provide[Container.activity_service]),
) -> ActivityService:
    return svc


ActivityServiceDep = Annotated[ActivityService, Depends(_get_activity_service)]

# ===== Note Service Dependencies =====


@inject
def _get_create_note_service(
    svc: CreateNoteService = Depends(Provide[Container.create_note_service]),
) -> CreateNoteService:
    return svc


CreateNoteServiceDep = Annotated[CreateNoteService, Depends(_get_create_note_service)]


@inject
def _get_update_note_service(
    svc: UpdateNoteService = Depends(Provide[Container.update_note_service]),
) -> UpdateNoteService:
    return svc


UpdateNoteServiceDep = Annotated[UpdateNoteService, Depends(_get_update_note_service)]


@inject
def _get_get_note_service(
    svc: GetNoteService = Depends(Provide[Container.get_note_service]),
) -> GetNoteService:
    return svc


GetNoteServiceDep = Annotated[GetNoteService, Depends(_get_get_note_service)]


@inject
def _get_create_note_from_chat_service(
    svc: CreateNoteFromChatService = Depends(Provide[Container.create_note_from_chat_service]),
) -> CreateNoteFromChatService:
    return svc


CreateNoteFromChatServiceDep = Annotated[
    CreateNoteFromChatService, Depends(_get_create_note_from_chat_service)
]


@inject
def _get_note_ai_update_service(
    svc: NoteAIUpdateService = Depends(Provide[Container.ai_update_note_service]),
) -> NoteAIUpdateService:
    return svc


NoteAIUpdateServiceDep = Annotated[NoteAIUpdateService, Depends(_get_note_ai_update_service)]


@inject
def _get_list_notes_service(
    svc: ListNotesService = Depends(Provide[Container.list_notes_service]),
) -> ListNotesService:
    return svc


ListNotesServiceDep = Annotated[ListNotesService, Depends(_get_list_notes_service)]


@inject
def _get_delete_note_service(
    svc: DeleteNoteService = Depends(Provide[Container.delete_note_service]),
) -> DeleteNoteService:
    return svc


DeleteNoteServiceDep = Annotated[DeleteNoteService, Depends(_get_delete_note_service)]


@inject
def _get_pin_note_service(
    svc: PinNoteService = Depends(Provide[Container.pin_note_service]),
) -> PinNoteService:
    return svc


PinNoteServiceDep = Annotated[PinNoteService, Depends(_get_pin_note_service)]


@inject
def _get_list_annotations_service(
    svc: ListAnnotationsService = Depends(Provide[Container.list_annotations_service]),
) -> ListAnnotationsService:
    return svc


ListAnnotationsServiceDep = Annotated[
    ListAnnotationsService, Depends(_get_list_annotations_service)
]


@inject
def _get_update_annotation_service(
    svc: UpdateAnnotationService = Depends(Provide[Container.update_annotation_service]),
) -> UpdateAnnotationService:
    return svc


UpdateAnnotationServiceDep = Annotated[
    UpdateAnnotationService, Depends(_get_update_annotation_service)
]

# ===== Issue Delete Service =====


@inject
def _get_delete_issue_service(
    svc: DeleteIssueService = Depends(Provide[Container.delete_issue_service]),
) -> DeleteIssueService:
    return svc


DeleteIssueServiceDep = Annotated[DeleteIssueService, Depends(_get_delete_issue_service)]


# ===== Cycle Service Dependencies =====


@inject
def _get_create_cycle_service(
    svc: CreateCycleService = Depends(Provide[Container.create_cycle_service]),
) -> CreateCycleService:
    return svc


CreateCycleServiceDep = Annotated[CreateCycleService, Depends(_get_create_cycle_service)]


@inject
def _get_update_cycle_service(
    svc: UpdateCycleService = Depends(Provide[Container.update_cycle_service]),
) -> UpdateCycleService:
    return svc


UpdateCycleServiceDep = Annotated[UpdateCycleService, Depends(_get_update_cycle_service)]


@inject
def _get_get_cycle_service(
    svc: GetCycleService = Depends(Provide[Container.get_cycle_service]),
) -> GetCycleService:
    return svc


GetCycleServiceDep = Annotated[GetCycleService, Depends(_get_get_cycle_service)]


@inject
def _get_add_issue_to_cycle_service(
    svc: AddIssueToCycleService = Depends(Provide[Container.add_issue_to_cycle_service]),
) -> AddIssueToCycleService:
    return svc


AddIssueToCycleServiceDep = Annotated[
    AddIssueToCycleService, Depends(_get_add_issue_to_cycle_service)
]


@inject
def _get_rollover_cycle_service(
    svc: RolloverCycleService = Depends(Provide[Container.rollover_cycle_service]),
) -> RolloverCycleService:
    return svc


RolloverCycleServiceDep = Annotated[RolloverCycleService, Depends(_get_rollover_cycle_service)]

# ===== AI Context Service Dependencies =====


@inject
def _get_generate_ai_context_service(
    svc: GenerateAIContextService = Depends(Provide[Container.generate_ai_context_service]),
) -> GenerateAIContextService:
    return svc


GenerateAIContextServiceDep = Annotated[
    GenerateAIContextService, Depends(_get_generate_ai_context_service)
]


@inject
def _get_generate_plan_service(
    svc: GenerateImplementationPlanService = Depends(Provide[Container.generate_plan_service]),
) -> GenerateImplementationPlanService:
    return svc


GeneratePlanServiceDep = Annotated[
    GenerateImplementationPlanService, Depends(_get_generate_plan_service)
]


@inject
def _get_refine_ai_context_service(
    svc: RefineAIContextService = Depends(Provide[Container.refine_ai_context_service]),
) -> RefineAIContextService:
    return svc


RefineAIContextServiceDep = Annotated[
    RefineAIContextService, Depends(_get_refine_ai_context_service)
]


@inject
def _get_export_ai_context_service(
    svc: ExportAIContextService = Depends(Provide[Container.export_ai_context_service]),
) -> ExportAIContextService:
    return svc


ExportAIContextServiceDep = Annotated[
    ExportAIContextService, Depends(_get_export_ai_context_service)
]

# ===== Annotation Service Dependencies =====


@inject
def _get_create_annotation_service(
    svc: CreateAnnotationService = Depends(Provide[Container.create_annotation_service]),
) -> CreateAnnotationService:
    return svc


CreateAnnotationServiceDep = Annotated[
    CreateAnnotationService, Depends(_get_create_annotation_service)
]

# ===== Discussion Service Dependencies =====


@inject
def _get_create_discussion_service(
    svc: CreateDiscussionService = Depends(Provide[Container.create_discussion_service]),
) -> CreateDiscussionService:
    return svc


CreateDiscussionServiceDep = Annotated[
    CreateDiscussionService, Depends(_get_create_discussion_service)
]

# ===== Integration Service Dependencies =====


@inject
def _get_connect_github_service(
    svc: ConnectGitHubService = Depends(Provide[Container.connect_github_service]),
) -> ConnectGitHubService:
    return svc


ConnectGitHubServiceDep = Annotated[ConnectGitHubService, Depends(_get_connect_github_service)]


@inject
def _get_process_github_webhook_service(
    svc: ProcessGitHubWebhookService = Depends(Provide[Container.process_github_webhook_service]),
) -> ProcessGitHubWebhookService:
    return svc


ProcessGitHubWebhookServiceDep = Annotated[
    ProcessGitHubWebhookService, Depends(_get_process_github_webhook_service)
]


@inject
def _get_link_commit_service(
    svc: LinkCommitService = Depends(Provide[Container.link_commit_service]),
) -> LinkCommitService:
    return svc


LinkCommitServiceDep = Annotated[LinkCommitService, Depends(_get_link_commit_service)]


@inject
def _get_auto_transition_service(
    svc: AutoTransitionService = Depends(Provide[Container.auto_transition_service]),
) -> AutoTransitionService:
    return svc


AutoTransitionServiceDep = Annotated[AutoTransitionService, Depends(_get_auto_transition_service)]

# ===== Onboarding Service Dependencies =====


@inject
def _get_create_guided_note_service(
    svc: CreateGuidedNoteService = Depends(Provide[Container.create_guided_note_service]),
) -> CreateGuidedNoteService:
    return svc


CreateGuidedNoteServiceDep = Annotated[
    CreateGuidedNoteService, Depends(_get_create_guided_note_service)
]


@inject
def _get_get_onboarding_service(
    svc: GetOnboardingService = Depends(Provide[Container.get_onboarding_service]),
) -> GetOnboardingService:
    return svc


GetOnboardingServiceDep = Annotated[GetOnboardingService, Depends(_get_get_onboarding_service)]


@inject
def _get_update_onboarding_service(
    svc: UpdateOnboardingService = Depends(Provide[Container.update_onboarding_service]),
) -> UpdateOnboardingService:
    return svc


UpdateOnboardingServiceDep = Annotated[
    UpdateOnboardingService, Depends(_get_update_onboarding_service)
]

# ===== Role Skill Service Dependencies =====


@inject
def _get_create_role_skill_service(
    svc: CreateRoleSkillService = Depends(Provide[Container.create_role_skill_service]),
) -> CreateRoleSkillService:
    return svc


CreateRoleSkillServiceDep = Annotated[
    CreateRoleSkillService, Depends(_get_create_role_skill_service)
]


@inject
def _get_update_role_skill_service(
    svc: UpdateRoleSkillService = Depends(Provide[Container.update_role_skill_service]),
) -> UpdateRoleSkillService:
    return svc


UpdateRoleSkillServiceDep = Annotated[
    UpdateRoleSkillService, Depends(_get_update_role_skill_service)
]


@inject
def _get_delete_role_skill_service(
    svc: DeleteRoleSkillService = Depends(Provide[Container.delete_role_skill_service]),
) -> DeleteRoleSkillService:
    return svc


DeleteRoleSkillServiceDep = Annotated[
    DeleteRoleSkillService, Depends(_get_delete_role_skill_service)
]


@inject
def _get_list_role_skills_service(
    svc: ListRoleSkillsService = Depends(Provide[Container.list_role_skills_service]),
) -> ListRoleSkillsService:
    return svc


ListRoleSkillsServiceDep = Annotated[ListRoleSkillsService, Depends(_get_list_role_skills_service)]


@inject
def _get_generate_role_skill_service(
    svc: GenerateRoleSkillService = Depends(Provide[Container.generate_role_skill_service]),
) -> GenerateRoleSkillService:
    return svc


GenerateRoleSkillServiceDep = Annotated[
    GenerateRoleSkillService, Depends(_get_generate_role_skill_service)
]

# ===== Homepage Service Dependencies =====


@inject
def _get_get_activity_service(
    svc: GetActivityService = Depends(Provide[Container.get_activity_service]),
) -> GetActivityService:
    return svc


GetActivityServiceDep = Annotated[GetActivityService, Depends(_get_get_activity_service)]


@inject
def _get_get_digest_service(
    svc: GetDigestService = Depends(Provide[Container.get_digest_service]),
) -> GetDigestService:
    return svc


GetDigestServiceDep = Annotated[GetDigestService, Depends(_get_get_digest_service)]


@inject
def _get_dismiss_suggestion_service(
    svc: DismissSuggestionService = Depends(Provide[Container.dismiss_suggestion_service]),
) -> DismissSuggestionService:
    return svc


DismissSuggestionServiceDep = Annotated[
    DismissSuggestionService, Depends(_get_dismiss_suggestion_service)
]

# ===== Workspace Service Dependencies =====


@inject
def _get_workspace_service(
    svc: WorkspaceService = Depends(Provide[Container.workspace_service]),
) -> WorkspaceService:
    return svc


WorkspaceServiceDep = Annotated[WorkspaceService, Depends(_get_workspace_service)]


@inject
def _get_workspace_member_service(
    svc: WorkspaceMemberService = Depends(Provide[Container.workspace_member_service]),
) -> WorkspaceMemberService:
    return svc


WorkspaceMemberServiceDep = Annotated[
    WorkspaceMemberService, Depends(_get_workspace_member_service)
]


@inject
def _get_member_profile_service(
    svc: MemberProfileService = Depends(Provide[Container.member_profile_service]),
) -> MemberProfileService:
    return svc


MemberProfileServiceDep = Annotated[MemberProfileService, Depends(_get_member_profile_service)]


@inject
def _get_workspace_invitation_service(
    svc: WorkspaceInvitationService = Depends(Provide[Container.workspace_invitation_service]),
) -> WorkspaceInvitationService:
    return svc


WorkspaceInvitationServiceDep = Annotated[
    WorkspaceInvitationService, Depends(_get_workspace_invitation_service)
]

# ===== Invite Rate Limiter Dependency =====


@inject
def _get_invite_rate_limiter(
    limiter: InviteRateLimiter = Depends(Provide[Container.invite_rate_limiter]),
) -> InviteRateLimiter:
    return limiter


InviteRateLimiterDep = Annotated[InviteRateLimiter, Depends(_get_invite_rate_limiter)]

# ===== Auth Service Dependencies =====


@inject
def _get_auth_service(
    svc: AuthService = Depends(Provide[Container.auth_service]),
) -> AuthService:
    return svc


AuthServiceDep = Annotated[AuthService, Depends(_get_auth_service)]

# ===== Task Service Dependencies =====


@inject
def _get_task_service(
    svc: TaskService = Depends(Provide[Container.task_service]),
) -> TaskService:
    return svc


TaskServiceDep = Annotated[TaskService, Depends(_get_task_service)]


@inject
def _get_rbac_service(
    svc: RbacService = Depends(Provide[Container.rbac_service]),
) -> RbacService:
    return svc


RbacServiceDep = Annotated[RbacService, Depends(_get_rbac_service)]

# ===== Tree Page Service Dependencies =====


@inject
def _get_move_page_service(
    svc: MovePageService = Depends(Provide[Container.move_page_service]),
) -> MovePageService:
    return svc


MovePageServiceDep = Annotated[MovePageService, Depends(_get_move_page_service)]


@inject
def _get_reorder_page_service(
    svc: ReorderPageService = Depends(Provide[Container.reorder_page_service]),
) -> ReorderPageService:
    return svc


ReorderPageServiceDep = Annotated[ReorderPageService, Depends(_get_reorder_page_service)]

# ===== Knowledge Graph Service Dependencies =====


@inject
def _get_knowledge_graph_query_service(
    svc: KnowledgeGraphQueryService = Depends(Provide[Container.knowledge_graph_query_service]),
) -> KnowledgeGraphQueryService:
    return svc


KnowledgeGraphQueryServiceDep = Annotated[
    KnowledgeGraphQueryService, Depends(_get_knowledge_graph_query_service)
]

# ===== Rate Limit Service Dependencies =====


@inject
def _get_rate_limit_service(
    svc: RateLimitService = Depends(Provide[Container.rate_limit_service]),
) -> RateLimitService:
    return svc


RateLimitServiceDep = Annotated[RateLimitService, Depends(_get_rate_limit_service)]

# ===== Feature Toggle Service Dependencies =====


@inject
def _get_feature_toggle_service(
    svc: FeatureToggleService = Depends(Provide[Container.feature_toggle_service]),
) -> FeatureToggleService:
    return svc


FeatureToggleServiceDep = Annotated[FeatureToggleService, Depends(_get_feature_toggle_service)]

# ===== SCIM Service Dependencies =====


@inject
def _get_scim_service(
    svc: ScimService = Depends(Provide[Container.scim_service]),
) -> ScimService:
    return svc


ScimServiceDep = Annotated[ScimService, Depends(_get_scim_service)]

# ===== Workspace AI Settings Service Dependencies =====


@inject
def _get_workspace_ai_settings_service(
    svc: WorkspaceAISettingsService = Depends(Provide[Container.workspace_ai_settings_service]),
) -> WorkspaceAISettingsService:
    return svc


WorkspaceAISettingsServiceDep = Annotated[
    WorkspaceAISettingsService, Depends(_get_workspace_ai_settings_service)
]

# ===== Approval Service Dependencies =====


@inject
def _get_approval_service(
    svc: ApprovalService = Depends(Provide[Container.approval_service]),
) -> ApprovalService:
    return svc


ApprovalServiceDep = Annotated[ApprovalService, Depends(_get_approval_service)]

# ===== Sprint Board Service Dependencies =====


@inject
def _get_sprint_board_service(
    svc: SprintBoardService = Depends(Provide[Container.sprint_board_service]),
) -> SprintBoardService:
    return svc


SprintBoardServiceDep = Annotated[SprintBoardService, Depends(_get_sprint_board_service)]

# ===== Capacity Plan Service Dependencies =====


@inject
def _get_capacity_plan_service(
    svc: CapacityPlanService = Depends(Provide[Container.capacity_plan_service]),
) -> CapacityPlanService:
    return svc


CapacityPlanServiceDep = Annotated[CapacityPlanService, Depends(_get_capacity_plan_service)]

# ===== PM Block Insight Service Dependencies =====


@inject
def _get_pm_block_insight_service(
    svc: PMBlockInsightService = Depends(Provide[Container.pm_block_insight_service]),
) -> PMBlockInsightService:
    return svc


PMBlockInsightServiceDep = Annotated[PMBlockInsightService, Depends(_get_pm_block_insight_service)]

# ===== Admin Dashboard Service Dependencies =====


@inject
def _get_admin_dashboard_service(
    svc: AdminDashboardService = Depends(Provide[Container.admin_dashboard_service]),
) -> AdminDashboardService:
    return svc


AdminDashboardServiceDep = Annotated[AdminDashboardService, Depends(_get_admin_dashboard_service)]

# ===== AI Configuration Service Dependencies =====


@inject
def _get_ai_configuration_service(
    svc: AIConfigurationService = Depends(Provide[Container.ai_configuration_service]),
) -> AIConfigurationService:
    return svc


AIConfigurationServiceDep = Annotated[
    AIConfigurationService, Depends(_get_ai_configuration_service)
]

# ===== Create Extracted Issues Service Dependencies =====


@inject
def _get_create_extracted_issues_service(
    svc: CreateExtractedIssuesService = Depends(Provide[Container.create_extracted_issues_service]),
) -> CreateExtractedIssuesService:
    return svc


CreateExtractedIssuesServiceDep = Annotated[
    CreateExtractedIssuesService, Depends(_get_create_extracted_issues_service)
]

# ===== Governance Rollback Service Dependencies =====


@inject
def _get_governance_rollback_service(
    svc: GovernanceRollbackService = Depends(Provide[Container.governance_rollback_service]),
) -> GovernanceRollbackService:
    return svc


GovernanceRollbackServiceDep = Annotated[
    GovernanceRollbackService, Depends(_get_governance_rollback_service)
]

# ===== Plugin Lifecycle Service Dependencies =====


@inject
def _get_plugin_lifecycle_service(
    svc: PluginLifecycleService = Depends(Provide[Container.plugin_lifecycle_service]),
) -> PluginLifecycleService:
    return svc


PluginLifecycleServiceDep = Annotated[
    PluginLifecycleService, Depends(_get_plugin_lifecycle_service)
]

# ===== OCR Configuration Service Dependencies =====
# OcrConfigurationService takes key_storage which is request-scoped (built from
# encryption_key + session). We compose it here using get_key_storage directly.


def _get_ocr_configuration_service(
    key_storage: Annotated[object, Depends(get_key_storage)],
) -> OcrConfigurationService:
    return OcrConfigurationService(key_storage=key_storage)  # type: ignore[arg-type]


OcrConfigurationServiceDep = Annotated[
    OcrConfigurationService, Depends(_get_ocr_configuration_service)
]


# ===== Phase 69 Memory Services =====


@inject
def _get_memory_recall_service(
    svc: MemoryRecallService = Depends(Provide[Container.memory_recall_service]),
) -> MemoryRecallService:
    return svc


MemoryRecallServiceDep = Annotated[MemoryRecallService, Depends(_get_memory_recall_service)]


@inject
def _get_memory_lifecycle_service(
    svc: MemoryLifecycleService = Depends(Provide[Container.memory_lifecycle_service]),
) -> MemoryLifecycleService:
    return svc


MemoryLifecycleServiceDep = Annotated[
    MemoryLifecycleService, Depends(_get_memory_lifecycle_service)
]


@inject
def _get_memory_list_service(
    svc: MemoryListService = Depends(Provide[Container.memory_list_service]),
) -> MemoryListService:
    return svc


MemoryListServiceDep = Annotated[MemoryListService, Depends(_get_memory_list_service)]


__all__ = [  # noqa: RUF022
    "ActionButtonServiceDep",
    "ActivityRepositoryDep",
    "ApprovalServiceDep",
    "CycleRepositoryDep",
    "InvitationRepositoryDep",
    "IssueRepositoryDep",
    "NoteIssueLinkRepositoryDep",
    "NoteRepositoryDep",
    "ProjectRepositoryDep",
    "UserRepositoryDep",
    "WorkspaceRepositoryDep",
    "AuthServiceDep",
    "ActivityServiceDep",
    "BlockOwnershipServiceDep",
    "DependencyGraphServiceDep",
    "NoteTemplateServiceDep",
    "RelatedIssuesSuggestionServiceDep",
    "AddIssueToCycleServiceDep",
    "AutoTransitionServiceDep",
    "ConnectGitHubServiceDep",
    "CreateAnnotationServiceDep",
    "CreateCycleServiceDep",
    "CreateDiscussionServiceDep",
    "CreateGuidedNoteServiceDep",
    "CreateIssueServiceDep",
    "CreateNoteFromChatServiceDep",
    "CreateNoteServiceDep",
    "CreateRoleSkillServiceDep",
    "DeleteIssueServiceDep",
    "DeleteNoteServiceDep",
    "DeleteRoleSkillServiceDep",
    "DismissSuggestionServiceDep",
    "ExportAIContextServiceDep",
    "GenerateAIContextServiceDep",
    "GeneratePlanServiceDep",
    "GenerateRoleSkillServiceDep",
    "GetActivityServiceDep",
    "GetCycleServiceDep",
    "GetDigestServiceDep",
    "GetIssueServiceDep",
    "GetNoteServiceDep",
    "GetOnboardingServiceDep",
    "KnowledgeGraphQueryServiceDep",
    "LinkCommitServiceDep",
    "ListAnnotationsServiceDep",
    "ListIssuesServiceDep",
    "ListNotesServiceDep",
    "ListRoleSkillsServiceDep",
    "NoteAIUpdateServiceDep",
    "PinNoteServiceDep",
    "ProcessGitHubWebhookServiceDep",
    "RefineAIContextServiceDep",
    "RolloverCycleServiceDep",
    "UpdateAnnotationServiceDep",
    "UpdateCycleServiceDep",
    "UpdateIssueServiceDep",
    "UpdateNoteServiceDep",
    "UpdateOnboardingServiceDep",
    "UpdateRoleSkillServiceDep",
    "MemberProfileServiceDep",
    "WorkspaceServiceDep",
    "WorkspaceMemberServiceDep",
    "WorkspaceInvitationServiceDep",
    "InviteRateLimiterDep",
    "TaskServiceDep",
    "RbacServiceDep",
    "MovePageServiceDep",
    "ReorderPageServiceDep",
    "TranscriptionServiceDep",
    "ProjectMemberServiceDep",
    "require_project_membership",
    "RateLimitServiceDep",
    "FeatureToggleServiceDep",
    "ScimServiceDep",
    "MCPToolExecutionServiceDep",
    "McpServerServiceDep",
    "McpOAuthServiceDep",
    "ProjectDetailServiceDep",
    "ProjectRbacServiceDep",
    "AttachmentManagementServiceDep",
    "WorkspaceAISettingsServiceDep",
    "SprintBoardServiceDep",
    "CapacityPlanServiceDep",
    "PMBlockInsightServiceDep",
    "AdminDashboardServiceDep",
    "AIConfigurationServiceDep",
    "CreateExtractedIssuesServiceDep",
    "GovernanceRollbackServiceDep",
    "OcrConfigurationServiceDep",
    "PluginLifecycleServiceDep",
    "ArtifactContentServiceDep",
    "PermissionServiceDep",
    "HookRuleServiceDep",
    "MemoryRecallServiceDep",
    "MemoryLifecycleServiceDep",
    "MemoryListServiceDep",
]


# ===== Transcription Service Dependencies =====


@inject
def _get_transcription_service(
    svc: TranscriptionService = Depends(Provide[Container.transcription_service]),
) -> TranscriptionService:
    return svc


TranscriptionServiceDep = Annotated[TranscriptionService, Depends(_get_transcription_service)]


# ===== Project Member Service Dependencies =====


@inject
def _get_project_member_service(
    svc: ProjectMemberService = Depends(Provide[Container.project_member_service]),
) -> ProjectMemberService:
    return svc


ProjectMemberServiceDep = Annotated[ProjectMemberService, Depends(_get_project_member_service)]


# ===== require_project_membership dependency (US6 — T037) =====


from uuid import UUID as _UUID  # noqa: E402

from pilot_space.dependencies.auth import (  # noqa: E402
    CurrentUserId as _CurrentUserId,
    SessionDep as _SessionDep,
)
from pilot_space.domain.exceptions import (  # noqa: E402
    ForbiddenError as _ForbiddenError,
    NotFoundError as _NotFoundError,
)
from pilot_space.infrastructure.database.models.workspace_member import (  # noqa: E402
    WorkspaceRole as _WorkspaceRole,
)
from pilot_space.infrastructure.database.repositories.workspace_member_repository import (  # noqa: E402
    WorkspaceMemberRepository,
)


@inject
async def require_project_membership(
    workspace_id: _UUID,
    project_id: _UUID,
    current_user_id: _CurrentUserId,
    session: _SessionDep,  # populates session ContextVar before DI resolves services
    project_member_svc: ProjectMemberService = Depends(Provide[Container.project_member_service]),
    workspace_member_repo: WorkspaceMemberRepository = Depends(
        Provide[Container.workspace_member_rbac_repository]
    ),
) -> None:
    """FastAPI dependency — ensure current user is a project member OR admin/owner.

    Validates the project belongs to the workspace before performing membership checks
    to prevent cross-workspace authorization bypass.

    Raises ForbiddenError (403) when not authorized.
    Raises NotFoundError (404) when the project does not belong to this workspace.
    """
    from sqlalchemy import select

    from pilot_space.infrastructure.database.models.project import Project

    # Validate that the project actually belongs to this workspace (prevents cross-workspace bypass)
    result = await session.execute(
        select(Project.id).where(
            Project.id == project_id,
            Project.workspace_id == workspace_id,
            Project.is_deleted == False,  # noqa: E712
        )
    )
    if result.scalar_one_or_none() is None:
        raise _NotFoundError("Project not found in this workspace")

    # Admins and Owners bypass project-level membership check
    wm = await workspace_member_repo.get_by_user_workspace(current_user_id, workspace_id)
    if wm and wm.role in (_WorkspaceRole.ADMIN, _WorkspaceRole.OWNER):
        return

    # Check explicit project membership
    repo = project_member_svc._repo  # type: ignore[attr-defined]  # noqa: SLF001
    membership = await repo.get_active_membership(project_id, current_user_id)
    if not membership:
        raise _ForbiddenError(
            "You do not have access to this project.",
            error_code="project_access_denied",
        )


# ===== MCP Server Service Dependencies =====


@inject
def _get_mcp_server_service(
    svc: McpServerService = Depends(Provide[Container.mcp_server_service]),
) -> McpServerService:
    return svc


McpServerServiceDep = Annotated[McpServerService, Depends(_get_mcp_server_service)]


# ===== MCP Tool Execution Service Dependencies =====


@inject
def _get_mcp_tool_execution_service(
    svc: MCPToolExecutionService = Depends(Provide[Container.mcp_tool_execution_service]),
) -> MCPToolExecutionService:
    return svc


MCPToolExecutionServiceDep = Annotated[
    MCPToolExecutionService, Depends(_get_mcp_tool_execution_service)
]

# ===== Project Detail Service Dependencies =====


@inject
def _get_project_detail_service(
    svc: ProjectDetailService = Depends(Provide[Container.project_detail_service]),
) -> ProjectDetailService:
    return svc


ProjectDetailServiceDep = Annotated[ProjectDetailService, Depends(_get_project_detail_service)]


# ===== Project RBAC Service Dependencies =====


@inject
def _get_project_rbac_service(
    svc: ProjectRbacService = Depends(Provide[Container.project_rbac_service]),
) -> ProjectRbacService:
    return svc


ProjectRbacServiceDep = Annotated[ProjectRbacService, Depends(_get_project_rbac_service)]


@inject
def _get_mcp_oauth_service(
    svc: McpOAuthService = Depends(Provide[Container.mcp_oauth_service]),
) -> McpOAuthService:
    return svc


McpOAuthServiceDep = Annotated[McpOAuthService, Depends(_get_mcp_oauth_service)]


# ===== Attachment Management Service Dependencies =====


@inject
def _get_attachment_management_service(
    svc: AttachmentManagementService = Depends(Provide[Container.attachment_management_service]),
) -> AttachmentManagementService:
    return svc


AttachmentManagementServiceDep = Annotated[
    AttachmentManagementService, Depends(_get_attachment_management_service)
]


# ===== Artifact Content Service Dependencies (Phase 62 — Monaco IDE) =====


@inject
def _get_artifact_content_service(
    svc: ArtifactContentService = Depends(Provide[Container.artifact_content_service]),
) -> ArtifactContentService:
    return svc


ArtifactContentServiceDep = Annotated[
    ArtifactContentService, Depends(_get_artifact_content_service)
]


# ===== Permission Service Dependencies (Phase 69 — 69-03) =====


@inject
def _get_permission_service(
    svc: PermissionService = Depends(Provide[Container.permission_service]),
) -> PermissionService:
    return svc


PermissionServiceDep = Annotated[PermissionService, Depends(_get_permission_service)]


# ===== Phase 83 — Workspace Hook Rule Service =====


@inject
def _get_hook_rule_service(
    svc: HookRuleService = Depends(Provide[Container.hook_rule_service]),
) -> HookRuleService:
    return svc


HookRuleServiceDep = Annotated[HookRuleService, Depends(_get_hook_rule_service)]
