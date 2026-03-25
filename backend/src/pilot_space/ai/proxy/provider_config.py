"""Model alias mapping and LiteLLM configuration.

Maps each TaskType to a LiteLLM model string with provider prefix
(e.g., "anthropic/claude-sonnet-4-20250514") and provides utilities
for resolving model names and extracting provider prefixes.
"""

from __future__ import annotations

from typing import Final

from pilot_space.ai.providers.provider_selector import TaskType

# LiteLLM model strings per task type (DD-011 routing rules).
# Format: "<provider>/<model>" — LiteLLM uses the prefix to select the SDK.
TASK_TYPE_MODEL_MAP: Final[dict[TaskType, str]] = {
    # Code-intensive tasks -> Claude Sonnet 4
    TaskType.PR_REVIEW: "anthropic/claude-sonnet-4-20250514",
    TaskType.AI_CONTEXT: "anthropic/claude-sonnet-4-20250514",
    TaskType.TASK_DECOMPOSITION: "anthropic/claude-sonnet-4-20250514",
    TaskType.PATTERN_DETECTION: "anthropic/claude-sonnet-4-20250514",
    # Standard tasks -> Claude Sonnet 4
    TaskType.CODE_GENERATION: "anthropic/claude-sonnet-4-20250514",
    TaskType.DOC_GENERATION: "anthropic/claude-sonnet-4-20250514",
    TaskType.ISSUE_ENHANCEMENT: "anthropic/claude-sonnet-4-20250514",
    TaskType.ISSUE_EXTRACTION: "anthropic/claude-sonnet-4-20250514",
    TaskType.MARGIN_ANNOTATION: "anthropic/claude-sonnet-4-20250514",
    TaskType.CONVERSATION: "anthropic/claude-sonnet-4-20250514",
    TaskType.DUPLICATE_DETECTION: "anthropic/claude-sonnet-4-20250514",
    TaskType.DIAGRAM_GENERATION: "anthropic/claude-sonnet-4-20250514",
    TaskType.TEMPLATE_FILLING: "anthropic/claude-sonnet-4-20250514",
    # Knowledge graph / contextual tasks
    TaskType.CONTEXTUAL_RETRIEVAL: "anthropic/claude-3-5-haiku-20241022",
    TaskType.GRAPH_EXTRACTION: "anthropic/claude-3-5-haiku-20241022",
    TaskType.INTENT_DETECTION: "anthropic/claude-sonnet-4-20250514",
    TaskType.ROLE_SKILL_GENERATION: "anthropic/claude-sonnet-4-20250514",
    # Latency-sensitive tasks -> Claude 3.5 Haiku
    TaskType.GHOST_TEXT: "anthropic/claude-3-5-haiku-20241022",
    TaskType.NOTIFICATION_PRIORITY: "anthropic/claude-3-5-haiku-20241022",
    TaskType.ASSIGNEE_RECOMMENDATION: "anthropic/claude-3-5-haiku-20241022",
    TaskType.COMMIT_LINKING: "anthropic/claude-3-5-haiku-20241022",
    # Embeddings -> OpenAI text-embedding-3-large
    TaskType.EMBEDDINGS: "openai/text-embedding-3-large",
    TaskType.SEMANTIC_SEARCH: "openai/text-embedding-3-large",
}


def resolve_litellm_model(
    task_type: TaskType,
    model_override: str | None = None,
) -> str:
    """Resolve the LiteLLM model string for a task type.

    Args:
        task_type: The AI task type to resolve.
        model_override: Optional explicit model string that takes precedence.

    Returns:
        LiteLLM model string (e.g., "anthropic/claude-sonnet-4-20250514").

    Raises:
        ValueError: If task_type is not in the routing table and no override given.
    """
    if model_override is not None:
        return model_override
    if task_type not in TASK_TYPE_MODEL_MAP:
        msg = f"No model mapping for task type: {task_type}"
        raise ValueError(msg)
    return TASK_TYPE_MODEL_MAP[task_type]


def extract_provider(model: str) -> str:
    """Extract the provider prefix from a LiteLLM model string.

    Args:
        model: LiteLLM model string (e.g., "anthropic/claude-sonnet-4-20250514").

    Returns:
        Provider name (e.g., "anthropic"). Returns the full string if no prefix.
    """
    if "/" in model:
        return model.split("/", 1)[0]
    return model


__all__ = [
    "TASK_TYPE_MODEL_MAP",
    "extract_provider",
    "resolve_litellm_model",
]
