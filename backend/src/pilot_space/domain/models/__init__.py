"""Domain models for Pilot Space.

Re-exports database models for domain layer access.
This allows domain services to import from domain.models
while actual implementations live in infrastructure.database.models.

Core entities:
- User: Platform user (synced with Supabase Auth)
- Workspace: Organization container
- Project: Issue/note container within workspace
- Issue: Work item with state machine and AI metadata
- Note: Block-based document with annotations
- Cycle: Sprint/iteration container
- Module: Epic-level grouping
"""

from pilot_space.infrastructure.database.models import (
    DEFAULT_STATES as DEFAULT_STATES,
    Activity as Activity,
    ActivityType as ActivityType,
    AIApprovalRequest as AIApprovalRequest,
    AIConfiguration as AIConfiguration,
    # AI entities
    AIContext as AIContext,
    AICostRecord as AICostRecord,
    AIMessage as AIMessage,
    AISession as AISession,
    AITask as AITask,
    AIToolCall as AIToolCall,
    AnnotationStatus as AnnotationStatus,
    AnnotationType as AnnotationType,
    ApprovalStatus as ApprovalStatus,
    # Base classes and mixins
    Base as Base,
    BaseModel as BaseModel,
    Cycle as Cycle,
    CycleStatus as CycleStatus,
    DiscussionComment as DiscussionComment,
    DiscussionStatus as DiscussionStatus,
    # Embedding entities
    Embedding as Embedding,
    EmbeddingType as EmbeddingType,
    EntityId as EntityId,
    # Integration entities
    Integration as Integration,
    IntegrationLink as IntegrationLink,
    IntegrationLinkType as IntegrationLinkType,
    IntegrationProvider as IntegrationProvider,
    Issue as Issue,
    IssuePriority as IssuePriority,
    Label as Label,
    LLMProvider as LLMProvider,
    MessageRole as MessageRole,
    Module as Module,
    ModuleStatus as ModuleStatus,
    Note as Note,
    NoteAnnotation as NoteAnnotation,
    # Links and associations
    NoteIssueLink as NoteIssueLink,
    NoteLinkType as NoteLinkType,
    Project as Project,
    SlugMixin as SlugMixin,
    SoftDeleteMixin as SoftDeleteMixin,
    State as State,
    StateGroup as StateGroup,
    TaskStatus as TaskStatus,
    Template as Template,
    # Discussion entities
    ThreadedDiscussion as ThreadedDiscussion,
    TimestampMixin as TimestampMixin,
    ToolCallStatus as ToolCallStatus,
    # Core entities
    User as User,
    Workspace as Workspace,
    WorkspaceAPIKey as WorkspaceAPIKey,
    WorkspaceMember as WorkspaceMember,
    WorkspaceRole as WorkspaceRole,
    WorkspaceScopedMixin as WorkspaceScopedMixin,
    WorkspaceScopedModel as WorkspaceScopedModel,
    issue_labels as issue_labels,
)

__all__ = [
    # Base classes
    "Base",
    "BaseModel",
    "EntityId",
    "SlugMixin",
    "SoftDeleteMixin",
    "TimestampMixin",
    "WorkspaceScopedMixin",
    "WorkspaceScopedModel",
    # Core entities
    "User",
    "Workspace",
    "WorkspaceMember",
    "WorkspaceRole",
    "WorkspaceAPIKey",
    "Project",
    "Issue",
    "IssuePriority",
    "Label",
    "State",
    "StateGroup",
    "DEFAULT_STATES",
    "Note",
    "NoteAnnotation",
    "AnnotationType",
    "AnnotationStatus",
    "Cycle",
    "CycleStatus",
    "Module",
    "ModuleStatus",
    "Activity",
    "ActivityType",
    "Template",
    # Discussion entities
    "ThreadedDiscussion",
    "DiscussionStatus",
    "DiscussionComment",
    # Links
    "NoteIssueLink",
    "NoteLinkType",
    "issue_labels",
    # AI entities
    "AIContext",
    "AIConfiguration",
    "LLMProvider",
    "AISession",
    "AIMessage",
    "MessageRole",
    "AIApprovalRequest",
    "ApprovalStatus",
    "AITask",
    "TaskStatus",
    "AIToolCall",
    "ToolCallStatus",
    "AICostRecord",
    # Integration entities
    "Integration",
    "IntegrationLink",
    "IntegrationProvider",
    "IntegrationLinkType",
    # Embedding entities
    "Embedding",
    "EmbeddingType",
]
