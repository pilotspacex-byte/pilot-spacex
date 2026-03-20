"""Prompt templates for AI agents.

Each agent has a corresponding prompt module:
- ghost_text: Ghost text completion prompts
- margin_annotation: Clarification and suggestion prompts
- issue_extraction: Issue detection and categorization prompts
- issue_enhancement: Title/description/label enhancement prompts
- duplicate_detection: Semantic similarity detection prompts
- pr_review: Code review prompts (architecture, security, quality)
- ai_context: Context aggregation and task generation prompts
"""

from pilot_space.ai.prompts.ai_context import (
    AI_CONTEXT_SYSTEM_PROMPT,
    CLAUDE_CODE_PROMPT_TEMPLATE,
    ParsedAIContext,
    build_claude_code_prompt,
    build_context_generation_prompt,
    build_refinement_prompt,
    extract_refinement_updates,
    parse_context_response,
)
from pilot_space.ai.prompts.ghost_text import (
    GHOST_TEXT_CODE_SYSTEM_PROMPT,
    GHOST_TEXT_SYSTEM_PROMPT,
    GhostTextPromptConfig,
    build_code_ghost_text_prompt,
    build_ghost_text_prompt,
)
from pilot_space.ai.prompts.issue_extraction import (
    ConfidenceTag,
    IssueExtractionPromptConfig,
    IssuePriority,
    build_issue_extraction_prompt,
    get_confidence_tag,
)
from pilot_space.ai.prompts.margin_annotation import (
    AnnotationType,
    MarginAnnotationPromptConfig,
    build_batch_annotation_prompt,
    build_margin_annotation_prompt,
)
from pilot_space.ai.prompts.pr_review import (
    build_pr_review_prompt,
    format_review_as_markdown,
    parse_pr_review_response,
)
from pilot_space.ai.prompts.skill_generation import (
    SKILL_GENERATION_PROMPT_TEMPLATE,
    build_skill_generation_prompt,
)

__all__ = [  # noqa: RUF022 — grouped by prompt module, not global alphabetical order
    # AI Context
    "AI_CONTEXT_SYSTEM_PROMPT",
    "CLAUDE_CODE_PROMPT_TEMPLATE",
    # Ghost Text
    "GHOST_TEXT_CODE_SYSTEM_PROMPT",
    "GHOST_TEXT_SYSTEM_PROMPT",
    # Margin Annotation
    "AnnotationType",
    # Issue Extraction
    "ConfidenceTag",
    "GhostTextPromptConfig",
    "IssueExtractionPromptConfig",
    "IssuePriority",
    "MarginAnnotationPromptConfig",
    "ParsedAIContext",
    "build_batch_annotation_prompt",
    "build_claude_code_prompt",
    "build_code_ghost_text_prompt",
    "build_context_generation_prompt",
    "build_ghost_text_prompt",
    "build_issue_extraction_prompt",
    "build_margin_annotation_prompt",
    # PR Review
    "build_pr_review_prompt",
    "build_refinement_prompt",
    "extract_refinement_updates",
    "format_review_as_markdown",
    "get_confidence_tag",
    "parse_context_response",
    "parse_pr_review_response",
    # Skill Generation
    "SKILL_GENERATION_PROMPT_TEMPLATE",
    "build_skill_generation_prompt",
]
