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
- WorkspaceDigest, DigestDismissal
- GraphNodeModel, GraphEdgeModel (knowledge graph)
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
from pilot_space.infrastructure.database.models.artifact import Artifact
from pilot_space.infrastructure.database.models.audit_log import ActorType, AuditLog
from pilot_space.infrastructure.database.models.chat_attachment import ChatAttachment
from pilot_space.infrastructure.database.models.custom_role import CustomRole
from pilot_space.infrastructure.database.models.cycle import Cycle, CycleStatus
from pilot_space.infrastructure.database.models.digest_dismissal import DigestDismissal
from pilot_space.infrastructure.database.models.discussion_comment import (
    DiscussionComment,
)
from pilot_space.infrastructure.database.models.drive_credential import DriveCredential
from pilot_space.infrastructure.database.models.embedding import Embedding, EmbeddingType
from pilot_space.infrastructure.database.models.graph_edge import GraphEdgeModel
from pilot_space.infrastructure.database.models.graph_node import GraphNodeModel
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
from pilot_space.infrastructure.database.models.memory_entry import (
    ConstitutionRule,
    MemoryDLQ,
    MemoryEntry,
)
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
from pilot_space.infrastructure.database.models.note_note_link import (
    NoteNoteLink,
    NoteNoteLinkType,
)
from pilot_space.infrastructure.database.models.note_version import NoteVersion, VersionTrigger
from pilot_space.infrastructure.database.models.notification import (
    Notification,
    NotificationPriority,
    NotificationType,
)
from pilot_space.infrastructure.database.models.onboarding import WorkspaceOnboarding
from pilot_space.infrastructure.database.models.pilot_api_key import PilotAPIKey
from pilot_space.infrastructure.database.models.pm_block_insight import PMBlockInsight
from pilot_space.infrastructure.database.models.project import Project
from pilot_space.infrastructure.database.models.skill_action_button import (
    BindingType,
    SkillActionButton,
)
from pilot_space.infrastructure.database.models.skill_execution import (
    SkillApprovalRole,
    SkillApprovalStatus,
    SkillExecution,
)
from pilot_space.infrastructure.database.models.skill_template import SkillTemplate
from pilot_space.infrastructure.database.models.state import (
    DEFAULT_STATES,
    State,
    StateGroup,
)
from pilot_space.infrastructure.database.models.task import Task
from pilot_space.infrastructure.database.models.template import Template
from pilot_space.infrastructure.database.models.threaded_discussion import (
    DiscussionStatus,
    ThreadedDiscussion,
)
from pilot_space.infrastructure.database.models.transcript_cache import TranscriptCache
from pilot_space.infrastructure.database.models.user import User
from pilot_space.infrastructure.database.models.user_role_skill import (
    RoleTemplate,
    UserRoleSkill,
)
from pilot_space.infrastructure.database.models.user_skill import UserSkill
from pilot_space.infrastructure.database.models.work_intent import (
    IntentArtifact,
    WorkIntent,
)
from pilot_space.infrastructure.database.models.workspace import Workspace
from pilot_space.infrastructure.database.models.workspace_ai_policy import WorkspaceAIPolicy
from pilot_space.infrastructure.database.models.workspace_api_key import WorkspaceAPIKey
from pilot_space.infrastructure.database.models.workspace_digest import WorkspaceDigest
from pilot_space.infrastructure.database.models.workspace_encryption_key import (
    WorkspaceEncryptionKey,
)
from pilot_space.infrastructure.database.models.workspace_github_credential import (
    WorkspaceGithubCredential,
)
from pilot_space.infrastructure.database.models.workspace_invitation import (
    InvitationStatus,
    WorkspaceInvitation,
)
from pilot_space.infrastructure.database.models.workspace_member import (
    WorkspaceMember,
    WorkspaceRole,
)
from pilot_space.infrastructure.database.models.workspace_plugin import WorkspacePlugin
from pilot_space.infrastructure.database.models.workspace_role_skill import WorkspaceRoleSkill
from pilot_space.infrastructure.database.models.workspace_session import WorkspaceSession

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
    "ActorType",
    "AnnotationStatus",
    "AnnotationType",
    "ApprovalStatus",
    "Artifact",
    "AuditLog",
    "Base",
    "BaseModel",
    "BindingType",
    "ChatAttachment",
    "ConstitutionRule",
    "CustomRole",
    "Cycle",
    "CycleStatus",
    "DigestDismissal",
    "DiscussionComment",
    "DiscussionStatus",
    "DriveCredential",
    "Embedding",
    "EmbeddingType",
    "EntityId",
    "GraphEdgeModel",
    "GraphNodeModel",
    "Integration",
    "IntegrationLink",
    "IntegrationLinkType",
    "IntegrationProvider",
    "IntentArtifact",
    "InvitationStatus",
    "Issue",
    "IssueLink",
    "IssueLinkType",
    "IssuePriority",
    "LLMProvider",
    "Label",
    "MemoryDLQ",
    "MemoryEntry",
    "MessageRole",
    "Module",
    "ModuleStatus",
    "Note",
    "NoteAnnotation",
    "NoteIssueLink",
    "NoteLinkType",
    "NoteNoteLink",
    "NoteNoteLinkType",
    "NoteVersion",
    "Notification",
    "NotificationPriority",
    "NotificationType",
    "PMBlockInsight",
    "PilotAPIKey",
    "Project",
    "RoleTemplate",
    "SkillActionButton",
    "SkillApprovalRole",
    "SkillApprovalStatus",
    "SkillExecution",
    "SkillTemplate",
    "SlugMixin",
    "SoftDeleteMixin",
    "State",
    "StateGroup",
    "Task",
    "TaskStatus",
    "Template",
    "ThreadedDiscussion",
    "TimestampMixin",
    "ToolCallStatus",
    "TranscriptCache",
    "User",
    "UserRoleSkill",
    "UserSkill",
    "VersionTrigger",
    "WorkIntent",
    "Workspace",
    "WorkspaceAIPolicy",
    "WorkspaceAPIKey",
    "WorkspaceDigest",
    "WorkspaceEncryptionKey",
    "WorkspaceGithubCredential",
    "WorkspaceInvitation",
    "WorkspaceMember",
    "WorkspaceOnboarding",
    "WorkspacePlugin",
    "WorkspaceRole",
    "WorkspaceRoleSkill",
    "WorkspaceScopedMixin",
    "WorkspaceScopedModel",
    "WorkspaceSession",
    "issue_labels",
]
