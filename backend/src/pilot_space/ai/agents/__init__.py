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
"""

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
from pilot_space.ai.agents.conversation_agent import (
    ConversationAgent,
    ConversationInput,
    ConversationManager,
    ConversationMessage,
    ConversationOutput,
    MessageRole,
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
    # AI Context
    "AICodeReference",
    "AIContextAgent",
    "AIContextInput",
    "AIContextOutput",
    # Base
    "AgentContext",
    "AgentResult",
    # Margin Annotation
    "AnnotationSuggestion",
    # Assignee Recommender
    "AssigneeRecommendation",
    "AssigneeRecommendationInput",
    "AssigneeRecommendationOutput",
    "AssigneeRecommenderAgent",
    "BaseAgent",
    "BatchMarginAnnotationAgent",
    # Commit Linker
    "CommitLinkerAgent",
    "CommitLinkerInput",
    "CommitLinkerOutput",
    # Conversation
    "ConversationAgent",
    "ConversationInput",
    "ConversationManager",
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
    # Duplicate Detector
    "DuplicateCandidate",
    "DuplicateDetectionInput",
    "DuplicateDetectionOutput",
    "DuplicateDetectorAgent",
    # Issue Extraction
    "ExtractedIssue",
    # Ghost Text
    "GhostTextAgent",
    "GhostTextInput",
    "GhostTextOutput",
    "GhostTextStreamingAgent",
    # Issue Enhancement
    "IssueEnhancementInput",
    "IssueEnhancementOutput",
    "IssueEnhancerAgent",
    "IssueExtractionInput",
    "IssueExtractionOutput",
    "IssueExtractorAgent",
    "IssueLink",
    "MarginAnnotationAgent",
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
