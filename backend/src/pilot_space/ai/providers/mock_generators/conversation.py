"""Mock conversation generator.

Provides deterministic conversation responses based on
intent detection from message content.
"""

from pilot_space.ai.agents import (
    ConversationInput,
    ConversationMessage,
    ConversationOutput,
    MessageRole,
)
from pilot_space.ai.providers.mock import MockResponseRegistry

# Response templates by detected intent
RESPONSES: dict[str, str] = {
    "greeting": "Hello! I'm here to help with your project. What would you like to work on?",
    "help": """I can help you with:
- Writing and refining notes
- Extracting issues from your notes
- Enhancing issue descriptions
- General project questions

What would you like to do?""",
    "issue": """I can help you create an issue from this. Would you like me to:
1. Extract key requirements
2. Suggest labels and priority
3. Generate acceptance criteria

Just let me know!""",
    "clarify": "Could you provide more details about what you're trying to accomplish? This will help me give you a more targeted response.",
    "code": """For code-related questions:
1. Provide context about the codebase
2. Share relevant code snippets
3. Describe the expected vs actual behavior

I'll help you troubleshoot!""",
    "planning": """Let's break this down into smaller, manageable tasks:
1. Define the core requirements
2. Identify dependencies
3. Create a step-by-step implementation plan

Should we start with requirements?""",
    "default": """I understand. Here are some suggestions:

1. Break this down into smaller tasks
2. Document the key requirements
3. Identify any dependencies

Would you like me to elaborate on any of these?""",
}

# Intent detection keywords
INTENT_KEYWORDS: dict[str, list[str]] = {
    "greeting": ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"],
    "help": ["help", "what can you", "how do i", "guide", "assist", "capabilities"],
    "issue": ["issue", "task", "ticket", "bug", "feature", "create issue", "make issue"],
    "clarify": ["what do you mean", "explain", "clarify", "confused", "unclear"],
    "code": ["code", "function", "class", "method", "debug", "error", "exception"],
    "planning": ["plan", "strategy", "approach", "how should", "best way"],
}


def _detect_intent(message: str) -> str:
    """Detect user intent from message content.

    Args:
        message: User message text.

    Returns:
        Intent key (defaults to "default").
    """
    message_lower = message.lower()

    # Check for question marks (common in clarification requests)
    if "?" in message and any(
        kw in message_lower for kw in ["what", "how", "why", "when", "where"]
    ):
        return "clarify"

    # Check keyword-based intents
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(kw in message_lower for kw in keywords):
            return intent

    return "default"


@MockResponseRegistry.register("ConversationAgent")
def generate_conversation(input_data: ConversationInput) -> ConversationOutput:
    """Generate mock conversation response.

    Detects intent from message and returns appropriate response:
    1. Greetings → Friendly introduction
    2. Help requests → Capability summary
    3. Issue-related → Issue creation guidance
    4. Code questions → Troubleshooting help
    5. Planning → Task breakdown assistance
    6. Questions → Request for clarification
    7. Default → General helpful response

    Args:
        input_data: Conversation input with message and history.

    Returns:
        ConversationOutput with response and updated history.
    """
    message = input_data.message

    # Detect intent
    intent = _detect_intent(message)

    # Get response template
    response = RESPONSES[intent]

    # Add context awareness if system context provided
    if input_data.system_context:
        context_snippet = input_data.system_context[:100]
        if len(input_data.system_context) > 100:
            context_snippet += "..."
        response = f"{response}\n\n(Context: {context_snippet})"

    # Build updated history
    updated_history = list(input_data.history)
    updated_history.append(ConversationMessage(role=MessageRole.USER, content=message))
    updated_history.append(ConversationMessage(role=MessageRole.ASSISTANT, content=response))

    # Truncate history if needed (keep last N messages)
    max_messages = input_data.max_history_messages
    if len(updated_history) > max_messages:
        # Keep system message if present, truncate middle
        updated_history = updated_history[-max_messages:]
        truncated = True
    else:
        truncated = False

    return ConversationOutput(
        response=response,
        updated_history=updated_history,
        truncated=truncated,
    )


__all__ = ["generate_conversation"]
