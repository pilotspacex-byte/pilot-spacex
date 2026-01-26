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
- All agents now use Claude Agent SDK for MCP tool integration
- SDK agents have _sdk suffix in module name (e.g., conversation_agent_sdk)
- Both legacy names and SDK-prefixed names are exported for compatibility
- Legacy agent files have been migrated to SDK versions (Wave 11)
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

# ===== SDK Agents (Claude Agent SDK) =====
# Import SDK versions - legacy names now map to SDK implementations
# SDK aliases for explicit SDK usage
from pilot_space.ai.agents.assignee_recommender_agent_sdk import (
    AssigneeRecommendation,
    AssigneeRecommendation as SDKAssigneeRecommendation,
    AssigneeRecommendationInput,
    AssigneeRecommendationInput as SDKAssigneeRecommendationInput,
    AssigneeRecommendationOutput,
    AssigneeRecommendationOutput as SDKAssigneeRecommendationOutput,
    AssigneeRecommenderAgent,
    AssigneeRecommenderAgent as AssigneeRecommenderAgentSDK,
    TeamMember,
    TeamMember as SDKTeamMember,
)

# Legacy base - deprecated, use SDK base instead
from pilot_space.ai.agents.base import (
    AgentContext as LegacyAgentContext,
    AgentResult as LegacyAgentResult,
    BaseAgent,
    Provider,
    TaskType,
    get_default_model,
    get_provider_for_task,
)

# SDK aliases
from pilot_space.ai.agents.commit_linker_agent_sdk import (
    CommitLinkerAgent,
    CommitLinkerAgent as CommitLinkerAgentSDK,
    CommitLinkerInput,
    CommitLinkerInput as SDKCommitLinkerInput,
    CommitLinkerOutput,
    CommitLinkerOutput as SDKCommitLinkerOutput,
    IssueLink,
    IssueLink as SDKIssueLink,
)

# SDK aliases
from pilot_space.ai.agents.conversation_agent_sdk import (
    ConversationAgent,
    ConversationAgent as ConversationAgentSDK,
    ConversationInput,
    ConversationInput as SDKConversationInput,
    ConversationManager,
    ConversationManager as ConversationManagerSDK,
    ConversationMessage,
    ConversationMessage as SDKConversationMessage,
    ConversationOutput,
    ConversationOutput as SDKConversationOutput,
    MessageRole,
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

# SDK aliases
from pilot_space.ai.agents.duplicate_detector_agent_sdk import (
    DuplicateCandidate,
    DuplicateCandidate as SDKDuplicateCandidate,
    DuplicateDetectionInput,
    DuplicateDetectionInput as SDKDuplicateDetectionInput,
    DuplicateDetectionOutput,
    DuplicateDetectionOutput as SDKDuplicateDetectionOutput,
    DuplicateDetectorAgent,
    DuplicateDetectorAgent as DuplicateDetectorAgentSDK,
)
from pilot_space.ai.agents.ghost_text_agent import (
    GhostTextAgent,
    GhostTextInput,
    GhostTextOutput,
    GhostTextStreamingAgent,
)

# SDK aliases
from pilot_space.ai.agents.issue_enhancer_agent_sdk import (
    IssueEnhancementInput,
    IssueEnhancementInput as SDKIssueEnhancementInput,
    IssueEnhancementOutput,
    IssueEnhancementOutput as SDKIssueEnhancementOutput,
    IssueEnhancerAgent,
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

# SDK Base Classes (Primary)
from pilot_space.ai.agents.sdk_base import (
    AgentContext,
    AgentResult,
    SDKBaseAgent,
    StreamingSDKBaseAgent,
)
from pilot_space.ai.agents.task_decomposer_agent import (
    SubTask,
    TaskDecomposerAgent,
    TaskDecomposerInput,
    TaskDecomposerOutput,
)


# Legacy helper function - reimplemented for backward compatibility
def extract_issue_refs(text: str) -> list[str]:
    """Extract issue references from text (legacy compatibility).

    Args:
        text: Text to scan for issue references.

    Returns:
        List of issue reference strings (e.g., ["#123", "ABC-456"]).
    """
    import re

    # Match #123 or PROJECT-123 patterns
    pattern = r"(?:#(\d+)|([A-Z]+-\d+))"
    matches = re.findall(pattern, text)
    return [f"#{m[0]}" if m[0] else m[1] for m in matches]


__all__ = [  # noqa: RUF022 - Grouped logically, not alphabetically
    "MAX_FILES_FULL_REVIEW",
    "MAX_LINES_FULL_REVIEW",
    "PRIORITY_FILE_PATTERNS",
    # ===== Legacy Agents =====
    # AI Context
    "AICodeReference",
    "AIContextAgent",
    "AIContextInput",
    "AIContextOutput",
    # ===== SDK Base Classes (Primary) =====
    # SDK Base - now the primary context and result types
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
    # Legacy base classes (deprecated)
    "BaseAgent",
    "BatchMarginAnnotationAgent",
    "LegacyAgentContext",
    "LegacyAgentResult",
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
