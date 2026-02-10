"""Type aliases for service dependency injection.

Provides clean, reusable type hints for FastAPI router endpoints using
the dependency-injector + FastAPI integration pattern.

Pattern: Each dependency gets an @inject wrapper function that resolves
the container provider, then an Annotated type alias wrapping it in Depends().
This eliminates the need for @inject on router endpoints.

Usage:
    @router.post("/issues")
    async def create_issue(
        request: IssueCreateRequest,
        session: SessionDep,  # Trigger session context
        service: CreateIssueServiceDep,  # Auto-injected from container
    ):
        result = await service.execute(payload)
        return IssueResponse.from_issue(result.issue)
"""

from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import Depends

from pilot_space.application.services.ai_context import (
    ExportAIContextService,
    GenerateAIContextService,
    RefineAIContextService,
)
from pilot_space.application.services.annotation import (
    CreateAnnotationService,
)
from pilot_space.application.services.cycle import (
    AddIssueToCycleService,
    CreateCycleService,
    GetCycleService,
    RolloverCycleService,
    UpdateCycleService,
)
from pilot_space.application.services.discussion import (
    CreateDiscussionService,
)
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
from pilot_space.container import Container
from pilot_space.dependencies.auth import SessionDep
from pilot_space.infrastructure.database.repositories.activity_repository import (
    ActivityRepository,
)
from pilot_space.infrastructure.database.repositories.cycle_repository import (
    CycleRepository,
)
from pilot_space.infrastructure.database.repositories.invitation_repository import (
    InvitationRepository,
)
from pilot_space.infrastructure.database.repositories.issue_repository import (
    IssueRepository,
)
from pilot_space.infrastructure.database.repositories.note_issue_link_repository import (
    NoteIssueLinkRepository,
)
from pilot_space.infrastructure.database.repositories.note_repository import (
    NoteRepository,
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

# ===== Repository Dependencies =====


@inject
def _get_activity_repository(
    repo: ActivityRepository = Depends(Provide[Container.activity_repository]),
) -> ActivityRepository:
    return repo


ActivityRepositoryDep = Annotated[ActivityRepository, Depends(_get_activity_repository)]


@inject
def _get_cycle_repository(
    repo: CycleRepository = Depends(Provide[Container.cycle_repository]),
) -> CycleRepository:
    return repo


CycleRepositoryDep = Annotated[CycleRepository, Depends(_get_cycle_repository)]


@inject
def _get_invitation_repository(
    repo: InvitationRepository = Depends(Provide[Container.invitation_repository]),
) -> InvitationRepository:
    return repo


InvitationRepositoryDep = Annotated[InvitationRepository, Depends(_get_invitation_repository)]


@inject
def _get_issue_repository(
    repo: IssueRepository = Depends(Provide[Container.issue_repository]),
) -> IssueRepository:
    return repo


IssueRepositoryDep = Annotated[IssueRepository, Depends(_get_issue_repository)]


@inject
def _get_note_issue_link_repository(
    repo: NoteIssueLinkRepository = Depends(Provide[Container.note_issue_link_repository]),
) -> NoteIssueLinkRepository:
    return repo


NoteIssueLinkRepositoryDep = Annotated[
    NoteIssueLinkRepository, Depends(_get_note_issue_link_repository)
]


@inject
def _get_note_repository(
    repo: NoteRepository = Depends(Provide[Container.note_repository]),
) -> NoteRepository:
    return repo


NoteRepositoryDep = Annotated[NoteRepository, Depends(_get_note_repository)]


@inject
def _get_project_repository(
    repo: ProjectRepository = Depends(Provide[Container.project_repository]),
) -> ProjectRepository:
    return repo


ProjectRepositoryDep = Annotated[ProjectRepository, Depends(_get_project_repository)]


@inject
def _get_user_repository(
    repo: UserRepository = Depends(Provide[Container.user_repository]),
) -> UserRepository:
    return repo


UserRepositoryDep = Annotated[UserRepository, Depends(_get_user_repository)]


@inject
def _get_workspace_repository(
    repo: WorkspaceRepository = Depends(Provide[Container.workspace_repository]),
) -> WorkspaceRepository:
    return repo


WorkspaceRepositoryDep = Annotated[WorkspaceRepository, Depends(_get_workspace_repository)]

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
    _: SessionDep,
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
def _get_workspace_invitation_service(
    svc: WorkspaceInvitationService = Depends(Provide[Container.workspace_invitation_service]),
) -> WorkspaceInvitationService:
    return svc


WorkspaceInvitationServiceDep = Annotated[
    WorkspaceInvitationService, Depends(_get_workspace_invitation_service)
]

__all__ = [  # noqa: RUF022
    # Repository Dependencies
    "ActivityRepositoryDep",
    "CycleRepositoryDep",
    "InvitationRepositoryDep",
    "IssueRepositoryDep",
    "NoteIssueLinkRepositoryDep",
    "NoteRepositoryDep",
    "ProjectRepositoryDep",
    "UserRepositoryDep",
    "WorkspaceRepositoryDep",
    # Service Dependencies
    "ActivityServiceDep",
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
    "GenerateRoleSkillServiceDep",
    "GetActivityServiceDep",
    "GetCycleServiceDep",
    "GetDigestServiceDep",
    "GetIssueServiceDep",
    "GetNoteServiceDep",
    "GetOnboardingServiceDep",
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
    "WorkspaceServiceDep",
    "WorkspaceMemberServiceDep",
    "WorkspaceInvitationServiceDep",
]
