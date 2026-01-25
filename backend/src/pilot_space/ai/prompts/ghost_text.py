"""Ghost text prompt templates.

Prompts for inline text completion suggestions.
Optimized for low latency with Gemini Flash.

T087: Ghost text prompt template.
"""

from __future__ import annotations

from dataclasses import dataclass

# System prompt for ghost text generation
GHOST_TEXT_SYSTEM_PROMPT = """You are an AI writing assistant for a project management platform.
Your task is to provide SHORT inline text completions that help users write faster.

CRITICAL RULES:
1. Output ONLY the completion text - no explanations, no quotes, no formatting
2. Maximum 50 tokens - keep suggestions brief
3. Match the user's writing style and tone
4. Be context-aware - understand what the user is writing about
5. If the context is unclear or completion isn't helpful, output NOTHING

You are completing text for notes, issue descriptions, and project documentation.
Focus on productivity and natural language flow."""

# User prompt template for ghost text
GHOST_TEXT_USER_PROMPT = """Complete this text naturally:

Context (previous paragraphs):
{context}

Current text to complete:
{current_text}

Cursor position: {cursor_position}

IMPORTANT: Output ONLY the completion text (max 50 tokens). No explanations."""


@dataclass
class GhostTextPromptConfig:
    """Configuration for ghost text prompts.

    Attributes:
        max_context_chars: Maximum characters of context to include.
        max_current_text_chars: Maximum characters of current text.
        max_output_tokens: Maximum tokens in completion.
    """

    max_context_chars: int = 1500
    max_current_text_chars: int = 500
    max_output_tokens: int = 50


def build_ghost_text_prompt(
    current_text: str,
    cursor_position: int,
    context: str | None = None,
    config: GhostTextPromptConfig | None = None,
) -> str:
    """Build the user prompt for ghost text generation.

    Args:
        current_text: The text being typed.
        cursor_position: Position of cursor in the text.
        context: Optional surrounding context (previous paragraphs).
        config: Prompt configuration.

    Returns:
        Formatted user prompt.
    """
    config = config or GhostTextPromptConfig()

    # Truncate context if needed
    truncated_context = ""
    if context:
        if len(context) > config.max_context_chars:
            truncated_context = "..." + context[-config.max_context_chars :]
        else:
            truncated_context = context

    # Truncate current text if needed (keep text before cursor)
    text_before_cursor = current_text[:cursor_position]
    if len(text_before_cursor) > config.max_current_text_chars:
        text_before_cursor = "..." + text_before_cursor[-config.max_current_text_chars :]

    return GHOST_TEXT_USER_PROMPT.format(
        context=truncated_context or "(No previous context)",
        current_text=text_before_cursor,
        cursor_position=cursor_position,
    )


# Code-aware ghost text prompts
GHOST_TEXT_CODE_SYSTEM_PROMPT = """You are an AI assistant helping users write technical documentation and code comments.
Your task is to provide SHORT inline completions for code-related text.

CRITICAL RULES:
1. Output ONLY the completion text - no explanations, no formatting
2. Maximum 50 tokens
3. Be technically accurate
4. Use appropriate terminology
5. If completing code, follow the language conventions
6. If the context is unclear, output NOTHING

You understand:
- Programming concepts and patterns
- Technical documentation conventions
- API descriptions and docstrings"""

GHOST_TEXT_CODE_USER_PROMPT = """Complete this technical text:

Language/Context: {language}

Previous text:
{context}

Current text to complete:
{current_text}

Output ONLY the completion (max 50 tokens)."""


def build_code_ghost_text_prompt(
    current_text: str,
    cursor_position: int,
    language: str | None = None,
    context: str | None = None,
    config: GhostTextPromptConfig | None = None,
) -> str:
    """Build prompt for code-aware ghost text.

    Args:
        current_text: The text being typed.
        cursor_position: Position of cursor.
        language: Programming language context.
        context: Surrounding code/text context.
        config: Prompt configuration.

    Returns:
        Formatted user prompt.
    """
    config = config or GhostTextPromptConfig()

    truncated_context = ""
    if context:
        if len(context) > config.max_context_chars:
            truncated_context = "..." + context[-config.max_context_chars :]
        else:
            truncated_context = context

    text_before_cursor = current_text[:cursor_position]
    if len(text_before_cursor) > config.max_current_text_chars:
        text_before_cursor = "..." + text_before_cursor[-config.max_current_text_chars :]

    return GHOST_TEXT_CODE_USER_PROMPT.format(
        language=language or "General",
        context=truncated_context or "(No previous context)",
        current_text=text_before_cursor,
    )


__all__ = [
    "GHOST_TEXT_CODE_SYSTEM_PROMPT",
    "GHOST_TEXT_CODE_USER_PROMPT",
    "GHOST_TEXT_SYSTEM_PROMPT",
    "GHOST_TEXT_USER_PROMPT",
    "GhostTextPromptConfig",
    "build_code_ghost_text_prompt",
    "build_ghost_text_prompt",
]
