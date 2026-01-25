"""Margin annotation prompt templates.

Prompts for AI-powered margin annotations that provide
suggestions, clarifications, and enhancements for notes.

T088: Margin annotation prompt template.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# Annotation type definitions
ANNOTATION_TYPES_DESCRIPTION = """
Annotation Types:
- clarification: Suggests making the text clearer or more specific
- expansion: Suggests adding more detail or context
- simplification: Suggests simplifying complex language
- action_item: Identifies a potential task or action
- issue_candidate: Text that could become a tracked issue
- question: Raises a question for consideration
- reference: Suggests linking to related documentation
- technical_review: Technical accuracy or improvement suggestion
"""


class AnnotationType(Enum):
    """Types of margin annotations."""

    CLARIFICATION = "clarification"
    EXPANSION = "expansion"
    SIMPLIFICATION = "simplification"
    ACTION_ITEM = "action_item"
    ISSUE_CANDIDATE = "issue_candidate"
    QUESTION = "question"
    REFERENCE = "reference"
    TECHNICAL_REVIEW = "technical_review"


# System prompt for margin annotation generation
MARGIN_ANNOTATION_SYSTEM_PROMPT = """You are an AI assistant for a project management platform.
Your task is to analyze note content and provide helpful margin annotations.

You should identify:
1. Opportunities to clarify or expand on ideas
2. Potential action items or tasks
3. Text that could become tracked issues
4. Questions that should be addressed
5. Technical improvements or corrections

{annotation_types}

OUTPUT FORMAT:
Return a JSON array of annotation objects. Each object must have:
- "type": One of the annotation types listed above
- "block_id": The block ID this annotation relates to
- "content": Your suggestion (2-3 sentences max)
- "confidence": Number 0.0-1.0 indicating confidence
- "highlight_start": Character position where highlight starts (optional)
- "highlight_end": Character position where highlight ends (optional)

Example output:
[
  {{
    "type": "issue_candidate",
    "block_id": "block-123",
    "content": "This feature request is well-defined and could be tracked as an issue.",
    "confidence": 0.85
  }},
  {{
    "type": "clarification",
    "block_id": "block-456",
    "content": "Consider specifying the expected behavior when the API times out.",
    "confidence": 0.7
  }}
]

IMPORTANT:
- Only annotate where genuinely helpful
- Keep suggestions concise and actionable
- Higher confidence = stronger recommendation
- Return empty array [] if no annotations needed"""

# User prompt for margin annotation
MARGIN_ANNOTATION_USER_PROMPT = """Analyze this note content and provide margin annotations:

Note Title: {note_title}

Workspace Context: {workspace_context}

Note Content (with block IDs):
{note_content}

Provide your analysis as a JSON array of annotations."""


@dataclass
class MarginAnnotationPromptConfig:
    """Configuration for margin annotation prompts.

    Attributes:
        max_content_chars: Maximum characters of note content.
        include_workspace_context: Whether to include workspace info.
        min_confidence_threshold: Minimum confidence to include.
    """

    max_content_chars: int = 8000
    include_workspace_context: bool = True
    min_confidence_threshold: float = 0.5


def format_note_content_with_blocks(
    blocks: list[dict[str, str]],
    max_chars: int = 8000,
) -> str:
    """Format note blocks for the prompt.

    Args:
        blocks: List of block dicts with 'id' and 'content' keys.
        max_chars: Maximum total characters.

    Returns:
        Formatted string with block IDs.
    """
    formatted_blocks: list[str] = []
    total_chars = 0

    for block in blocks:
        block_id = block.get("id", "unknown")
        content = block.get("content", "")

        # Format: [block-id] content
        formatted = f"[{block_id}] {content}"

        if total_chars + len(formatted) > max_chars:
            # Truncate this block if needed
            remaining = max_chars - total_chars
            if remaining > 50:  # Only add if meaningful space remaining
                formatted = formatted[:remaining] + "..."
                formatted_blocks.append(formatted)
            break

        formatted_blocks.append(formatted)
        total_chars += len(formatted) + 1  # +1 for newline

    return "\n\n".join(formatted_blocks)


def build_margin_annotation_prompt(
    note_title: str,
    blocks: list[dict[str, str]],
    workspace_context: str | None = None,
    config: MarginAnnotationPromptConfig | None = None,
) -> tuple[str, str]:
    """Build system and user prompts for margin annotations.

    Args:
        note_title: Title of the note being analyzed.
        blocks: Note content as list of blocks.
        workspace_context: Optional workspace/project context.
        config: Prompt configuration.

    Returns:
        Tuple of (system_prompt, user_prompt).
    """
    config = config or MarginAnnotationPromptConfig()

    # Build system prompt with annotation types
    system_prompt = MARGIN_ANNOTATION_SYSTEM_PROMPT.format(
        annotation_types=ANNOTATION_TYPES_DESCRIPTION,
    )

    # Format note content
    formatted_content = format_note_content_with_blocks(
        blocks,
        max_chars=config.max_content_chars,
    )

    # Build user prompt
    user_prompt = MARGIN_ANNOTATION_USER_PROMPT.format(
        note_title=note_title,
        workspace_context=workspace_context or "(No additional context)",
        note_content=formatted_content,
    )

    return system_prompt, user_prompt


# Batch annotation prompt for processing multiple blocks efficiently
BATCH_ANNOTATION_SYSTEM_PROMPT = """You are an AI assistant analyzing multiple text blocks for annotation.
Process each block and provide relevant annotations.

{annotation_types}

OUTPUT FORMAT:
Return a JSON object with block IDs as keys and annotation arrays as values:
{{
  "block-123": [
    {{"type": "clarification", "content": "...", "confidence": 0.8}}
  ],
  "block-456": []
}}

Return empty array for blocks that don't need annotation."""

BATCH_ANNOTATION_USER_PROMPT = """Analyze these blocks and provide annotations:

{blocks}

Return annotations as JSON object with block IDs as keys."""


def build_batch_annotation_prompt(
    blocks: list[dict[str, str]],
) -> tuple[str, str]:
    """Build prompts for batch annotation processing.

    Args:
        blocks: List of blocks to annotate.

    Returns:
        Tuple of (system_prompt, user_prompt).
    """
    system_prompt = BATCH_ANNOTATION_SYSTEM_PROMPT.format(
        annotation_types=ANNOTATION_TYPES_DESCRIPTION,
    )

    # Format blocks
    formatted_blocks = "\n\n".join(
        f"[{b.get('id', 'unknown')}]\n{b.get('content', '')}" for b in blocks
    )

    user_prompt = BATCH_ANNOTATION_USER_PROMPT.format(blocks=formatted_blocks)

    return system_prompt, user_prompt


__all__ = [
    "ANNOTATION_TYPES_DESCRIPTION",
    "BATCH_ANNOTATION_SYSTEM_PROMPT",
    "BATCH_ANNOTATION_USER_PROMPT",
    "MARGIN_ANNOTATION_SYSTEM_PROMPT",
    "MARGIN_ANNOTATION_USER_PROMPT",
    "AnnotationType",
    "MarginAnnotationPromptConfig",
    "build_batch_annotation_prompt",
    "build_margin_annotation_prompt",
    "format_note_content_with_blocks",
]
