"""AI agents for Pilot Space.

MVP Agents (7):
- GhostTextAgent: Inline text suggestions (Gemini Flash)
- MarginAnnotationAgent: Margin annotations and clarifications (Claude Sonnet)
- IssueExtractorAgent: Issue extraction from notes (Claude Sonnet)
- IssueEnhancerAgent: Issue enhancement suggestions (Claude Sonnet)
- DuplicateDetectorAgent: Duplicate issue detection (Claude + pgvector)
- PRReviewAgent: Automated PR code review (Claude Opus 4.5)
- AIContextAgent: Context aggregation for issues (Claude Opus 4.5)

Supporting Agents (T079-T090):
- ConversationAgent: Multi-turn AI conversations (Claude Opus 4.5)
- DocGeneratorAgent: Documentation generation (Claude Sonnet)
- TaskDecomposerAgent: Task breakdown with dependencies (Claude Opus 4.5)
- DiagramGeneratorAgent: Mermaid diagram generation (Claude Sonnet)
- AssigneeRecommenderAgent: Assignee suggestions (Claude Haiku)
- CommitLinkerAgent: Commit-issue linking (Claude Haiku)

SDK Agent Architecture:
- SDK agents use Claude Agent SDK for MCP tool integration
- SDK agents have _sdk suffix in module name (e.g., conversation_agent_sdk)
- SDK agents are exported with SDK suffix (e.g., ConversationAgentSDK)
- Legacy agents remain for backward compatibility during migration
"""

# SDK Base Classes
# Legacy Base Classes
from pilot_space.ai.agents.ai_context_agent import (
    AIContextAgent,
    AIContextInput,
    AIContextOutput,
    CodeReference as AICodeReference,
    RelatedItem,
    TaskItem,
)
from pilot_space.ai.agents.assignee_recommender_agent import (
    AssigneeRecommendation,
    AssigneeRecommendationInput,
    AssigneeRecommendationOutput,
    AssigneeRecommenderAgent,
    TeamMember,
)

# ===== SDK Agents (Claude Agent SDK) =====
# Import SDK versions with SDK suffix to allow gradual migration
from pilot_space.ai.agents.assignee_recommender_agent_sdk import (
    AssigneeRecommendation as SDKAssigneeRecommendation,
    AssigneeRecommendationInput as SDKAssigneeRecommendationInput,
    AssigneeRecommendationOutput as SDKAssigneeRecommendationOutput,
    AssigneeRecommenderAgent as AssigneeRecommenderAgentSDK,
    TeamMember as SDKTeamMember,
)
from pilot_space.ai.agents.base import (
    AgentContext,
    AgentResult,
    BaseAgent,
    Provider,
    TaskType,
    get_default_model,
    get_provider_for_task,
)
from pilot_space.ai.agents.commit_linker_agent import (
    CommitLinkerAgent,
    CommitLinkerInput,
    CommitLinkerOutput,
    IssueLink,
    extract_issue_refs,
)
from pilot_space.ai.agents.commit_linker_agent_sdk import (
    CommitLinkerAgent as CommitLinkerAgentSDK,
    CommitLinkerInput as SDKCommitLinkerInput,
    CommitLinkerOutput as SDKCommitLinkerOutput,
    IssueLink as SDKIssueLink,
)
from pilot_space.ai.agents.conversation_agent import (
    ConversationAgent,
    ConversationInput,
    ConversationManager,
    ConversationMessage,
    ConversationOutput,
    MessageRole,
)
from pilot_space.ai.agents.conversation_agent_sdk import (
    ConversationAgent as ConversationAgentSDK,
    ConversationInput as SDKConversationInput,
    ConversationManager as ConversationManagerSDK,
    ConversationMessage as SDKConversationMessage,
    ConversationOutput as SDKConversationOutput,
    MessageRole as SDKMessageRole,
)
from pilot_space.ai.agents.diagram_generator_agent import (
    DiagramGeneratorAgent,
    DiagramGeneratorInput,
    DiagramGeneratorOutput,
    DiagramType,
)
from pilot_space.ai.agents.doc_generator_agent import (
    DocGeneratorAgent,
    DocGeneratorInput,
    DocGeneratorOutput,
    DocType,
)
from pilot_space.ai.agents.duplicate_detector_agent import (
    DuplicateCandidate,
    DuplicateDetectionInput,
    DuplicateDetectionOutput,
    DuplicateDetectorAgent,
)
from pilot_space.ai.agents.duplicate_detector_agent_sdk import (
    DuplicateCandidate as SDKDuplicateCandidate,
    DuplicateDetectionInput as SDKDuplicateDetectionInput,
    DuplicateDetectionOutput as SDKDuplicateDetectionOutput,
    DuplicateDetectorAgent as DuplicateDetectorAgentSDK,
)
from pilot_space.ai.agents.ghost_text_agent import (
    GhostTextAgent,
    GhostTextInput,
    GhostTextOutput,
    GhostTextStreamingAgent,
)
from pilot_space.ai.agents.issue_enhancer_agent import (
    IssueEnhancementInput,
    IssueEnhancementOutput,
    IssueEnhancerAgent,
)
from pilot_space.ai.agents.issue_enhancer_agent_sdk import (
    IssueEnhancementInput as SDKIssueEnhancementInput,
    IssueEnhancementOutput as SDKIssueEnhancementOutput,
    IssueEnhancerAgent as IssueEnhancerAgentSDK,
)
from pilot_space.ai.agents.issue_extractor_agent import (
    ExtractedIssue,
    IssueExtractionInput,
    IssueExtractionOutput,
    IssueExtractorAgent,
    QuickIssueExtractor,
)
from pilot_space.ai.agents.margin_annotation_agent import (
    AnnotationSuggestion,
    BatchMarginAnnotationAgent,
    MarginAnnotationAgent,
    MarginAnnotationInput,
    MarginAnnotationOutput,
)
from pilot_space.ai.agents.margin_annotation_agent_sdk import (
    Annotation as SDKAnnotation,
    AnnotationType as SDKAnnotationType,
    MarginAnnotationAgentSDK,
    MarginAnnotationInput as SDKMarginAnnotationInput,
    MarginAnnotationOutput as SDKMarginAnnotationOutput,
)
from pilot_space.ai.agents.pr_review_agent import (
    MAX_FILES_FULL_REVIEW,
    MAX_LINES_FULL_REVIEW,
    PRIORITY_FILE_PATTERNS,
    PRReviewAgent,
    PRReviewInput,
    PRReviewOutput,
    ReviewCategory,
    ReviewComment,
    ReviewSeverity,
)
from pilot_space.ai.agents.sdk_base import (
    AgentContext as SDKAgentContext,
    AgentResult as SDKAgentResult,
    SDKBaseAgent,
    StreamingSDKBaseAgent,
)
from pilot_space.ai.agents.task_decomposer_agent import (
    SubTask,
    TaskDecomposerAgent,
    TaskDecomposerInput,
    TaskDecomposerOutput,
)

__all__ = [
    "MAX_FILES_FULL_REVIEW",
    "MAX_LINES_FULL_REVIEW",
    "PRIORITY_FILE_PATTERNS",
    # ===== Legacy Agents =====
    # AI Context
    "AICodeReference",
    "AIContextAgent",
    "AIContextInput",
    "AIContextOutput",
    # ===== Legacy Base Classes =====
    # Legacy Base
    "AgentContext",
    "AgentResult",
    # Margin Annotation
    "AnnotationSuggestion",
    # Assignee Recommender (Legacy)
    "AssigneeRecommendation",
    "AssigneeRecommendationInput",
    "AssigneeRecommendationOutput",
    "AssigneeRecommenderAgent",
    # ===== SDK Agents =====
    # Assignee Recommender SDK
    "AssigneeRecommenderAgentSDK",
    "BaseAgent",
    "BatchMarginAnnotationAgent",
    # Commit Linker (Legacy)
    "CommitLinkerAgent",
    # Commit Linker SDK
    "CommitLinkerAgentSDK",
    "CommitLinkerInput",
    "CommitLinkerOutput",
    # Conversation (Legacy)
    "ConversationAgent",
    # Conversation SDK
    "ConversationAgentSDK",
    "ConversationInput",
    "ConversationManager",
    "ConversationManagerSDK",
    "ConversationMessage",
    "ConversationOutput",
    # Diagram Generator (T085-T086)
    "DiagramGeneratorAgent",
    "DiagramGeneratorInput",
    "DiagramGeneratorOutput",
    "DiagramType",
    # Doc Generator (T081-T082)
    "DocGeneratorAgent",
    "DocGeneratorInput",
    "DocGeneratorOutput",
    "DocType",
    # Duplicate Detector (Legacy)
    "DuplicateCandidate",
    "DuplicateDetectionInput",
    "DuplicateDetectionOutput",
    "DuplicateDetectorAgent",
    # Duplicate Detector SDK
    "DuplicateDetectorAgentSDK",
    # Issue Extraction
    "ExtractedIssue",
    # Ghost Text
    "GhostTextAgent",
    "GhostTextInput",
    "GhostTextOutput",
    "GhostTextStreamingAgent",
    # Issue Enhancement (Legacy)
    "IssueEnhancementInput",
    "IssueEnhancementOutput",
    "IssueEnhancerAgent",
    # Issue Enhancer SDK
    "IssueEnhancerAgentSDK",
    "IssueExtractionInput",
    "IssueExtractionOutput",
    "IssueExtractorAgent",
    "IssueLink",
    "MarginAnnotationAgent",
    # Margin Annotation SDK
    "MarginAnnotationAgentSDK",
    "MarginAnnotationInput",
    "MarginAnnotationOutput",
    "MessageRole",
    # PR Review
    "PRReviewAgent",
    "PRReviewInput",
    "PRReviewOutput",
    "Provider",
    "QuickIssueExtractor",
    "RelatedItem",
    "ReviewCategory",
    "ReviewComment",
    "ReviewSeverity",
    # ===== SDK Base Classes =====
    # SDK Base (imported as SDKAgentContext, SDKAgentResult to avoid conflicts)
    "SDKAgentContext",
    "SDKAgentResult",
    "SDKAnnotation",
    "SDKAnnotationType",
    "SDKAssigneeRecommendation",
    "SDKAssigneeRecommendationInput",
    "SDKAssigneeRecommendationOutput",
    "SDKBaseAgent",
    "SDKCommitLinkerInput",
    "SDKCommitLinkerOutput",
    "SDKConversationInput",
    "SDKConversationMessage",
    "SDKConversationOutput",
    "SDKDuplicateCandidate",
    "SDKDuplicateDetectionInput",
    "SDKDuplicateDetectionOutput",
    "SDKIssueEnhancementInput",
    "SDKIssueEnhancementOutput",
    "SDKIssueLink",
    "SDKMarginAnnotationInput",
    "SDKMarginAnnotationOutput",
    "SDKMessageRole",
    "SDKTeamMember",
    "StreamingSDKBaseAgent",
    # Task Decomposer (T083-T084)
    "SubTask",
    "TaskDecomposerAgent",
    "TaskDecomposerInput",
    "TaskDecomposerOutput",
    "TaskItem",
    "TaskType",
    "TeamMember",
    "extract_issue_refs",
    "get_default_model",
    "get_provider_for_task",
]
