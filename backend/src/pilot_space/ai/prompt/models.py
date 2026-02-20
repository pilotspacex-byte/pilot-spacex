"""Pydantic models and enums for the prompt assembly pipeline.

Defines the data structures used across all prompt layers:
- UserIntent: classifies user messages into actionable categories
- IntentClassification: result of intent detection with confidence
- PromptLayerConfig: input configuration for prompt assembly
- AssembledPrompt: output of the assembly pipeline with metadata
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class UserIntent(str, Enum):
    """Classifies user messages for intent-aware prompt assembly.

    Each intent maps to specific rule files and behavioral layers
    that get injected into the system prompt.
    """

    NOTE_WRITING = "note_writing"
    NOTE_READING = "note_reading"
    ISSUE_MGMT = "issue_mgmt"
    PM_BLOCKS = "pm_blocks"
    PROJECT_MGMT = "project_mgmt"
    COMMENT = "comment"
    GENERAL = "general"


class IntentClassification(BaseModel):
    """Result of classifying a user message into intents.

    Attributes:
        primary: The dominant intent detected in the message.
        secondary: An optional secondary intent for multi-intent messages.
        confidence: Model confidence in the primary classification (0.0-1.0).
    """

    primary: UserIntent
    secondary: UserIntent | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class PromptLayerConfig(BaseModel):
    """Input configuration for the 6-layer prompt assembly pipeline.

    Collects all context needed to build a dynamic system prompt:
    layers 1-2 are static templates, layers 3-6 use these fields.

    Attributes:
        base_prompt: Optional override for the identity layer. When empty
            (default), the assembler loads from template files or uses a
            hardcoded fallback.
        role_type: User's primary workspace role (e.g. 'developer').
        workspace_name: Current workspace name for context injection.
        project_names: Active project names in the workspace.
        user_message: The current user message for intent classification.
        has_note_context: Whether note context is present in the conversation.
        memory_entries: Retrieved memory entries for context.
        pending_approvals: Count of pending approval requests.
        budget_warning: Optional budget/token warning message.
        conversation_summary: Optional summary of prior conversation turns.
    """

    base_prompt: str = ""
    role_type: str | None = None
    workspace_name: str | None = None
    project_names: list[str] | None = None
    user_message: str = ""
    has_note_context: bool = False
    memory_entries: list[dict[str, Any]] = Field(default_factory=list)
    pending_approvals: int = 0
    budget_warning: str | None = None
    conversation_summary: str | None = None


class AssembledPrompt(BaseModel):
    """Output of the prompt assembly pipeline.

    Contains the final assembled prompt string plus metadata about
    which layers and rules were included, useful for debugging and
    token budget tracking.

    Attributes:
        prompt: The fully assembled system prompt string.
        layers_loaded: Names of layers that were included.
        rules_loaded: Names of rule files that were injected.
        estimated_tokens: Rough token estimate (chars / 4).
    """

    prompt: str
    layers_loaded: list[str] = Field(default_factory=list)
    rules_loaded: list[str] = Field(default_factory=list)
    estimated_tokens: int = 0
