"""Token limit configuration for AI agents.

Defines max_tokens settings per agent to optimize cost
and prevent unnecessarily long responses.

T318: Agent-specific token limits tuning.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, slots=True)
class TokenLimit:
    """Token limit configuration for an agent.

    Attributes:
        max_tokens: Maximum tokens in response.
        description: Rationale for this limit.
    """

    max_tokens: int
    description: str


# Agent-specific token limits
# Values tuned based on typical use cases and cost optimization
AGENT_TOKEN_LIMITS: Final[dict[str, TokenLimit]] = {
    # Ghost text - short completions only
    "ghost_text": TokenLimit(
        max_tokens=50,
        description="Ghost text provides brief inline suggestions",
    ),
    # Margin annotations - concise suggestions
    "margin_annotation": TokenLimit(
        max_tokens=512,
        description="Margin annotations are short sidebar comments",
    ),
    # Issue extraction - moderate output
    "issue_extractor": TokenLimit(
        max_tokens=2048,
        description="Issue extraction creates multiple structured issues",
    ),
    # PR review - can be lengthy
    "pr_review": TokenLimit(
        max_tokens=4096,
        description="PR reviews provide comprehensive analysis across multiple dimensions",
    ),
    # AI context - comprehensive analysis
    "ai_context": TokenLimit(
        max_tokens=8192,
        description="AI context aggregates extensive information and generates Claude Code prompts",
    ),
    # Conversation - extended dialogue
    "conversation": TokenLimit(
        max_tokens=4096,
        description="Conversation supports back-and-forth discussion",
    ),
    # Task decomposition - detailed breakdown
    "task_decomposer": TokenLimit(
        max_tokens=3072,
        description="Task decomposition creates structured task hierarchies",
    ),
    # Documentation generation - moderate length
    "doc_generator": TokenLimit(
        max_tokens=2048,
        description="Documentation generation creates concise technical docs",
    ),
    # Diagram generation - metadata only
    "diagram_generator": TokenLimit(
        max_tokens=1024,
        description="Diagram generation returns Mermaid syntax",
    ),
    # Issue enhancement - brief additions
    "issue_enhancer": TokenLimit(
        max_tokens=512,
        description="Issue enhancement adds acceptance criteria and context",
    ),
    # Assignee recommendation - short response
    "assignee_recommender": TokenLimit(
        max_tokens=256,
        description="Assignee recommendation returns ranked list with brief rationale",
    ),
    # Duplicate detection - structured output
    "duplicate_detector": TokenLimit(
        max_tokens=512,
        description="Duplicate detection returns similarity scores and matches",
    ),
    # Commit linking - brief analysis
    "commit_linker": TokenLimit(
        max_tokens=256,
        description="Commit linking returns relevant commit IDs with brief reasoning",
    ),
}


def get_token_limit(agent_name: str) -> int:
    """Get max_tokens for an agent.

    Args:
        agent_name: Name of the agent.

    Returns:
        Maximum token limit for the agent.
        Returns 2048 as default if agent not found.
    """
    limit = AGENT_TOKEN_LIMITS.get(agent_name)
    if limit:
        return limit.max_tokens

    # Default for unknown agents
    return 2048


def get_all_limits() -> dict[str, int]:
    """Get all agent token limits as a simple dict.

    Returns:
        Dictionary mapping agent names to max_tokens values.
    """
    return {name: limit.max_tokens for name, limit in AGENT_TOKEN_LIMITS.items()}


def validate_token_request(agent_name: str, requested_tokens: int) -> int:
    """Validate and cap token request for an agent.

    Args:
        agent_name: Name of the agent.
        requested_tokens: Requested max_tokens.

    Returns:
        Capped token count (minimum of requested and agent limit).
    """
    limit = get_token_limit(agent_name)
    return min(requested_tokens, limit)


__all__ = [
    "AGENT_TOKEN_LIMITS",
    "TokenLimit",
    "get_all_limits",
    "get_token_limit",
    "validate_token_request",
]
