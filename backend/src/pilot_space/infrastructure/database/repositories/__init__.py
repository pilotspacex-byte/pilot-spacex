"""Repository layer for database access.

Provides data access patterns with CRUD, soft delete, and pagination.
"""

from pilot_space.infrastructure.database.repositories.activity_repository import (
    ActivityRepository,
)
from pilot_space.infrastructure.database.repositories.ai_configuration_repository import (
    AIConfigurationRepository,
)
from pilot_space.infrastructure.database.repositories.ai_context_repository import (
    AIContextRepository,
)
from pilot_space.infrastructure.database.repositories.audit_log_repository import (
    AuditLogPage,
    AuditLogRepository,
    compute_diff,
    write_audit_nonfatal,
)
from pilot_space.infrastructure.database.repositories.base import (
    BaseRepository,
    CursorPage,
)
from pilot_space.infrastructure.database.repositories.chat_attachment_repository import (
    ChatAttachmentRepository,
)
from pilot_space.infrastructure.database.repositories.cycle_repository import (
    CycleFilters,
    CycleMetrics,
    CycleRepository,
)
from pilot_space.infrastructure.database.repositories.digest_repository import (
    DigestRepository,
    DismissalRepository,
)
from pilot_space.infrastructure.database.repositories.discussion_repository import (
    DiscussionCommentRepository,
    DiscussionRepository,
)
from pilot_space.infrastructure.database.repositories.drive_credential_repository import (
    DriveCredentialRepository,
)
from pilot_space.infrastructure.database.repositories.homepage_repository import (
    HomepageRepository,
    IssueActivityRow,
    NoteActivityRow,
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
    IssueFilters,
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
from pilot_space.infrastructure.database.repositories.pilot_api_key_repository import (
    PilotAPIKeyRepository,
)
from pilot_space.infrastructure.database.repositories.project_repository import (
    ProjectRepository,
)
from pilot_space.infrastructure.database.repositories.role_skill_repository import (
    RoleSkillRepository,
    RoleTemplateRepository,
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
from pilot_space.infrastructure.database.repositories.workspace_repository import (
    WorkspaceRepository,
)

__all__ = [
    "AIConfigurationRepository",
    "AIContextRepository",
    "ActivityRepository",
    "AuditLogPage",
    "AuditLogRepository",
    "BaseRepository",
    "ChatAttachmentRepository",
    "CursorPage",
    "CycleFilters",
    "CycleMetrics",
    "CycleRepository",
    "DigestRepository",
    "DiscussionCommentRepository",
    "DiscussionRepository",
    "DismissalRepository",
    "DriveCredentialRepository",
    "HomepageRepository",
    "IntegrationLinkRepository",
    "IntegrationRepository",
    "IntentArtifactRepository",
    "InvitationRepository",
    "IssueActivityRow",
    "IssueFilters",
    "IssueLinkRepository",
    "IssueRepository",
    "LabelRepository",
    "NoteActivityRow",
    "NoteAnnotationRepository",
    "NoteIssueLinkRepository",
    "NoteRepository",
    "PilotAPIKeyRepository",
    "ProjectRepository",
    "RoleSkillRepository",
    "RoleTemplateRepository",
    "SkillExecutionRepository",
    "TaskRepository",
    "TemplateRepository",
    "UserRepository",
    "WorkIntentRepository",
    "WorkspaceRepository",
    "compute_diff",
    "write_audit_nonfatal",
]
