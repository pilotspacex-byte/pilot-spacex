"""Mock ghost text generator.

Provides deterministic ghost text completions based on
text patterns and content type (code vs prose).
"""

from pilot_space.ai.agents.ghost_text_agent import GhostTextInput, GhostTextOutput
from pilot_space.ai.providers.mock import MockResponseRegistry

# Pattern-based completions for code
CODE_COMPLETIONS: dict[str, str] = {
    "def ": 'function_name(self):\n        """Docstring."""\n        pass',
    "class ": '""" Class docstring."""\n\n    def __init__(self):\n        pass',
    "async def ": "async_function():\n        await asyncio.sleep(0)",
    "import ": "os\nimport sys",
    "from ": "typing import Any",
    "if ": "condition:\n        pass",
    "for ": "item in items:\n        print(item)",
    "while ": "True:\n        break",
    "try:": "\n        pass\n    except Exception as e:\n        logger.error(e)",
    "with ": "open('file.txt') as f:\n        content = f.read()",
    "return ": "result",
    "raise ": "ValueError('Invalid input')",
    "@": "property\n    def name(self) -> str:",
    "self.": "_value = None",
    "async with ": "session.begin():\n        await session.execute(query)",
}

# Code bracket completions
CODE_BRACKET_COMPLETIONS: dict[str, str] = {
    "(": ")",
    "[": "]",
    "{": "}",
}

# Pattern-based completions for natural language
TEXT_COMPLETIONS: dict[str, str] = {
    "The ": "system processes the request and returns a response.",
    "This ": "feature enables users to manage their workflows efficiently.",
    "We need to ": "implement the following changes to improve performance.",
    "Users can ": "access this functionality through the settings panel.",
    "To ": "accomplish this, follow the steps outlined below.",
    "In order to ": "maintain consistency, follow the established patterns.",
    "First, ": "we need to analyze the current state of the system.",
    "Finally, ": "we should validate the results and clean up resources.",
    "However, ": "there are some edge cases to consider.",
    "When ": "the condition is met, the system triggers the workflow.",
    "If ": "the user is authenticated, they can access this feature.",
    "As ": "part of this implementation, we should consider...",
    # Common conversational patterns
    "I want to ": "implement this feature with proper error handling.",
    "I wanna ": "add support for this use case in the next sprint.",
    "I need to ": "review the implementation details before proceeding.",
    "I think ": "we should prioritize this task based on user feedback.",
    "We should ": "consider the implications before making changes.",
    "Let's ": "start by defining the requirements clearly.",
    "Please ": "review the proposed changes and provide feedback.",
    "Can we ": "discuss the technical approach for this feature?",
    "TODO: ": "Implement this functionality",
    "FIXME: ": "Address this issue before release",
    "NOTE: ": "Important consideration for future development",
}

# Word-based continuations for prose
WORD_CONTINUATIONS: dict[str, str] = {
    "i": " think we should consider the following approach.",
    "we": " need to implement this feature carefully.",
    "the": " system should handle this case appropriately.",
    "this": " approach will help us achieve our goals.",
    "it": " is important to validate the requirements first.",
    "that": " would be the best solution for this problem.",
    "but": " we should also consider alternative approaches.",
    "and": " we can iterate on this based on feedback.",
    "or": " alternatively, we could use a different method.",
}


def _match_pattern(text: str, completions: dict[str, str]) -> GhostTextOutput | None:
    """Try to match text against completion patterns."""
    for prefix, completion in completions.items():
        if text.endswith(prefix.rstrip()):
            return GhostTextOutput(
                suggestion=completion,
                cursor_offset=len(completion),
                is_empty=False,
            )
    return None


def _get_code_fallback(text: str) -> GhostTextOutput | None:
    """Get code-specific fallback completions."""
    if not text:
        return None

    last_char = text[-1]
    if last_char == ".":
        return GhostTextOutput(suggestion="", cursor_offset=0, is_empty=True)

    completion = CODE_BRACKET_COMPLETIONS.get(last_char)
    if completion:
        return GhostTextOutput(
            suggestion=completion,
            cursor_offset=len(completion),
            is_empty=False,
        )
    return None


def _get_prose_fallback(text: str) -> GhostTextOutput | None:
    """Get prose fallback based on last word."""
    words = text.split()
    if not words:
        return None

    last_word = words[-1].lower()
    continuation = WORD_CONTINUATIONS.get(last_word)
    if continuation:
        return GhostTextOutput(
            suggestion=continuation,
            cursor_offset=len(continuation),
            is_empty=False,
        )
    return None


@MockResponseRegistry.register("GhostTextAgent")
def generate_ghost_text(input_data: GhostTextInput) -> GhostTextOutput:
    """Generate mock ghost text completion.

    Uses pattern matching to provide contextual completions:
    1. Empty input -> empty suggestion
    2. Code context -> code completions
    3. Text context -> prose completions
    4. Fallback completions based on context type

    Args:
        input_data: Ghost text input with current text and context.

    Returns:
        GhostTextOutput with suggestion or empty.
    """
    text = input_data.current_text.strip()
    is_code = input_data.is_code or bool(input_data.language)

    # Empty input
    if not text:
        return GhostTextOutput.empty()

    # Select completion dictionary based on context
    completions = CODE_COMPLETIONS if is_code else TEXT_COMPLETIONS

    # Try pattern matching first
    result = _match_pattern(text, completions)
    if result:
        return result

    # Try context-specific fallbacks
    result = _get_code_fallback(text) if is_code else _get_prose_fallback(text)
    return result if result else GhostTextOutput.empty()


__all__ = ["generate_ghost_text"]
