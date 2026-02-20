"""Prompt assembly pipeline for PilotSpace AI agent.

Provides a 6-layer dynamic prompt builder that assembles system prompts
based on user intent, role, workspace context, and conversation state.

Usage::

    from pilot_space.ai.prompt import assemble_system_prompt, PromptLayerConfig

    config = PromptLayerConfig(base_prompt="...", user_message="...")
    result = await assemble_system_prompt(config)
    print(result.prompt)
"""

from __future__ import annotations

from pilot_space.ai.prompt.models import AssembledPrompt, PromptLayerConfig
from pilot_space.ai.prompt.prompt_assembler import assemble_system_prompt

__all__ = [
    "AssembledPrompt",
    "PromptLayerConfig",
    "assemble_system_prompt",
]
