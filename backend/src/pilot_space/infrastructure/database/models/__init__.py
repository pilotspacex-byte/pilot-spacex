"""SQLAlchemy ORM models for Pilot Space.

Core Models:
- User, Workspace, WorkspaceMember
- Project, State, Label, Module
- Issue, IssueLabel, Activity
- Note, NoteAnnotation, ThreadedDiscussion, DiscussionComment
- NoteIssueLink, Template
- Cycle
- Integration, IntegrationLink
- AIContext, AIConfiguration
- Embedding
"""

from pilot_space.infrastructure.database.base import (
    Base,
    BaseModel,
    EntityId,
    SlugMixin,
    SoftDeleteMixin,
    TimestampMixin,
    WorkspaceScopedMixin,
    WorkspaceScopedModel,
)
from pilot_space.infrastructure.database.models.activity import Activity, ActivityType
from pilot_space.infrastructure.database.models.ai_approval_request import (
    AIApprovalRequest,
    ApprovalStatus,
)
from pilot_space.infrastructure.database.models.ai_configuration import (
    AIConfiguration,
    LLMProvider,
)
from pilot_space.infrastructure.database.models.ai_context import AIContext
from pilot_space.infrastructure.database.models.ai_cost_record import AICostRecord
from pilot_space.infrastructure.database.models.ai_message import AIMessage, MessageRole
from pilot_space.infrastructure.database.models.ai_session import AISession
from pilot_space.infrastructure.database.models.ai_task import AITask, TaskStatus
from pilot_space.infrastructure.database.models.ai_tool_call import AIToolCall, ToolCallStatus
from pilot_space.infrastructure.database.models.cycle import Cycle, CycleStatus
from pilot_space.infrastructure.database.models.discussion_comment import (
    DiscussionComment,
)
from pilot_space.infrastructure.database.models.embedding import Embedding, EmbeddingType
from pilot_space.infrastructure.database.models.integration import (
    Integration,
    IntegrationLink,
    IntegrationLinkType,
    IntegrationProvider,
)
from pilot_space.infrastructure.database.models.issue import Issue, IssuePriority
from pilot_space.infrastructure.database.models.issue_label import issue_labels
from pilot_space.infrastructure.database.models.issue_link import IssueLink, IssueLinkType
from pilot_space.infrastructure.database.models.label import Label
from pilot_space.infrastructure.database.models.module import Module, ModuleStatus
from pilot_space.infrastructure.database.models.note import Note
from pilot_space.infrastructure.database.models.note_annotation import (
    AnnotationStatus,
    AnnotationType,
    NoteAnnotation,
)
from pilot_space.infrastructure.database.models.note_issue_link import (
    NoteIssueLink,
    NoteLinkType,
)
from pilot_space.infrastructure.database.models.onboarding import WorkspaceOnboarding
from pilot_space.infrastructure.database.models.project import Project
from pilot_space.infrastructure.database.models.state import (
    DEFAULT_STATES,
    State,
    StateGroup,
)
from pilot_space.infrastructure.database.models.template import Template
from pilot_space.infrastructure.database.models.threaded_discussion import (
    DiscussionStatus,
    ThreadedDiscussion,
)
from pilot_space.infrastructure.database.models.user import User
from pilot_space.infrastructure.database.models.user_role_skill import (
    RoleTemplate,
    UserRoleSkill,
)
from pilot_space.infrastructure.database.models.workspace import Workspace
from pilot_space.infrastructure.database.models.workspace_api_key import WorkspaceAPIKey
from pilot_space.infrastructure.database.models.workspace_invitation import (
    InvitationStatus,
    WorkspaceInvitation,
)
from pilot_space.infrastructure.database.models.workspace_member import (
    WorkspaceMember,
    WorkspaceRole,
)

__all__ = [
    "DEFAULT_STATES",
    "AIApprovalRequest",
    "AIConfiguration",
    "AIContext",
    "AICostRecord",
    "AIMessage",
    "AISession",
    "AITask",
    "AIToolCall",
    "Activity",
    "ActivityType",
    "AnnotationStatus",
    "AnnotationType",
    "ApprovalStatus",
    "Base",
    "BaseModel",
    "Cycle",
    "CycleStatus",
    "DiscussionComment",
    "DiscussionStatus",
    "Embedding",
    "EmbeddingType",
    "EntityId",
    "Integration",
    "IntegrationLink",
    "IntegrationLinkType",
    "IntegrationProvider",
    "InvitationStatus",
    "Issue",
    "IssueLink",
    "IssueLinkType",
    "IssuePriority",
    "LLMProvider",
    "Label",
    "MessageRole",
    "Module",
    "ModuleStatus",
    "Note",
    "NoteAnnotation",
    "NoteIssueLink",
    "NoteLinkType",
    "Project",
    "RoleTemplate",
    "SlugMixin",
    "SoftDeleteMixin",
    "State",
    "StateGroup",
    "TaskStatus",
    "Template",
    "ThreadedDiscussion",
    "TimestampMixin",
    "ToolCallStatus",
    "User",
    "UserRoleSkill",
    "Workspace",
    "WorkspaceAPIKey",
    "WorkspaceInvitation",
    "WorkspaceMember",
    "WorkspaceOnboarding",
    "WorkspaceRole",
    "WorkspaceScopedMixin",
    "WorkspaceScopedModel",
    "issue_labels",
]
