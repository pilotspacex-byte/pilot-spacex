"""Pydantic models for the prompt assembly pipeline with static/dynamic split.

Defines the data structures used across prompt assembly:
- PromptLayerConfig: input configuration for prompt assembly
- AssembledPrompt: output of the assembly pipeline with static/dynamic split and metadata
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PromptLayerConfig(BaseModel):
    """Input configuration for prompt assembly pipeline with static/dynamic split.

    Collects all context needed to build a system prompt. Static layers
    (identity, safety, role) are KV-cache eligible. Dynamic layers
    (workspace, skills, disabled features, mention resolution) are
    assembled per-request.

    Attributes:
        base_prompt: Optional override for the identity layer. When empty
            (default), the assembler loads from template files or uses a
            hardcoded fallback.
        role_type: User's primary workspace role (e.g. 'developer').
        workspace_name: Current workspace name for context injection.
        project_names: Active project names in the workspace.
        user_message: The current user message.
        has_mention_context: Whether @[Type:uuid] mention tokens are present in the message.
        user_skills: Active skills for the user in the workspace. Each entry
            is a dict with keys ``name`` (str) and ``description`` (str).
            Used to populate the "Your Skills" section in the assembled prompt
            so the agent can proactively suggest relevant skills.
        feature_toggles: Feature toggle states for the workspace.
    """

    base_prompt: str = ""
    role_type: str | None = None
    workspace_name: str | None = None
    project_names: list[str] | None = None
    user_message: str = ""
    has_mention_context: bool = False
    user_skills: list[dict[str, str]] = Field(default_factory=list)
    feature_toggles: dict[str, bool] = Field(default_factory=dict)


class AssembledPrompt(BaseModel):
    """Output of the prompt assembly pipeline with static/dynamic split.

    Contains the final assembled prompt string plus metadata about
    which layers were included, useful for debugging and token budget
    tracking. The static_prefix and dynamic_suffix fields support
    KV-cache optimization by separating cache-eligible content from
    per-request content.

    Attributes:
        prompt: The fully assembled system prompt string.
        layers_loaded: Names of layers that were included.
        estimated_tokens: Rough token estimate (chars / 4).
        static_prefix: KV-cache eligible static portion of the prompt.
        dynamic_suffix: Per-request dynamic portion of the prompt.
    """

    prompt: str
    layers_loaded: list[str] = Field(default_factory=list)
    estimated_tokens: int = 0
    static_prefix: str = ""
    dynamic_suffix: str = ""
