"""Six-layer dynamic prompt assembler for PilotSpace AI agent.

Assembles system prompts from static templates, role context, workspace
metadata, intent-based rules, and session state. Each layer is loaded
only when relevant, keeping the prompt compact and focused.

Layer order:
1. Identity (always)
2. Safety + tools + style (always)
3. Role adaptation (if role_type set)
4. Workspace context (if workspace/project info available)
5. Session state (memory, conversation summary, approvals, budget)
6. Intent-based operational rules (based on user message classification)
"""

from __future__ import annotations

import logging
from typing import Any

from pilot_space.ai.prompt.intent_classifier import (
    classify_intent,
    get_rules_for_intent,
)
from pilot_space.ai.prompt.layer_loaders import (
    load_role_template,
    load_rule_file,
    load_static_layer,
)
from pilot_space.ai.prompt.models import AssembledPrompt, PromptLayerConfig

logger = logging.getLogger(__name__)

# Hardcoded fallbacks in case template files are missing (bad deployment, etc.)
_FALLBACK_IDENTITY = (
    "You are PilotSpace AI, an embedded assistant in a Note-First SDLC platform. "
    "You help teams capture ideas in notes, extract issues, review PRs, and manage workflows."
)

_FALLBACK_SAFETY = (
    "## Safety reasoning\n"
    "- Confirm destructive actions (remove, unlink, delete) always require approval.\n"
    "- Read-only tools (search, get) auto-execute.\n"
    "- Operations return payloads; never mutate DB directly.\n\n"
    "## Interaction style\n"
    "- Be concise. No filler phrases. Reference blocks using ¶N notation."
)


async def assemble_system_prompt(config: PromptLayerConfig) -> AssembledPrompt:
    """Assemble a dynamic system prompt from the 6-layer pipeline.

    Args:
        config: All inputs needed for prompt assembly.

    Returns:
        An ``AssembledPrompt`` with the final prompt, loaded layer names,
        loaded rule filenames, and an estimated token count.
    """
    sections: list[str] = []
    layers_loaded: list[str] = []
    rules_loaded: list[str] = []

    # Layer 1: Identity (always)
    identity = await load_static_layer("layer1_identity.md")
    if identity:
        sections.append(identity)
        layers_loaded.append("identity")
    else:
        logger.warning("layer1_identity.md missing — using hardcoded fallback")
        sections.append(config.base_prompt or _FALLBACK_IDENTITY)
        layers_loaded.append("identity:fallback")

    # Layer 2: Safety + tools + style (always)
    safety = await load_static_layer("layer2_safety_tools_style.md")
    if safety:
        sections.append(safety)
        layers_loaded.append("safety_tools_style")
    else:
        logger.warning("layer2_safety_tools_style.md missing — using hardcoded fallback")
        sections.append(_FALLBACK_SAFETY)
        layers_loaded.append("safety_tools_style:fallback")

    # Layer 3: Role adaptation
    if config.role_type:
        role_content = await load_role_template(config.role_type)
        if role_content:
            sections.append(f"## Your User's Role\n{role_content}")
            layers_loaded.append(f"role:{config.role_type}")

    # Layer 4: Workspace context
    workspace_section = _build_workspace_section(config)
    if workspace_section:
        sections.append(workspace_section)
        layers_loaded.append("workspace")

    # Layer 5: Session state (memory, summary — placed before rules for recency)
    session_parts = _build_session_section(config)
    if session_parts:
        sections.extend(session_parts)
        layers_loaded.append("session")

    # Layer 6: Intent-based rules (at the end, closest to user message)
    classification = classify_intent(config.user_message, has_note_context=config.has_note_context)
    rule_files, rule_summaries = get_rules_for_intent(classification)

    if rule_files:
        rule_parts: list[str] = []
        for filename in rule_files:
            content = await load_rule_file(filename)
            if content:
                rule_parts.append(content)
                rules_loaded.append(filename)
                layers_loaded.append(f"rules:{filename}")

        if rule_parts:
            sections.append("## Operational Rules\n" + "\n\n".join(rule_parts))

    if rule_summaries:
        sections.append("## Available Rule Domains (not loaded)\n" + "\n".join(rule_summaries))

    prompt = "\n\n".join(sections)
    estimated_tokens = len(prompt) // 4  # ~4 chars per token for English text

    return AssembledPrompt(
        prompt=prompt,
        layers_loaded=layers_loaded,
        rules_loaded=rules_loaded,
        estimated_tokens=estimated_tokens,
    )


def _build_workspace_section(config: PromptLayerConfig) -> str | None:
    """Build workspace context section from config fields.

    Returns:
        Formatted workspace section, or None if no context available.
    """
    if not config.workspace_name and not config.project_names:
        return None

    parts: list[str] = ["## Workspace Context"]
    if config.workspace_name:
        parts.append(f"Workspace: {config.workspace_name}")
    if config.project_names:
        parts.append(f"Active projects: {', '.join(config.project_names[:10])}")

    return "\n".join(parts)


def _build_session_section(config: PromptLayerConfig) -> list[str]:
    """Build session state sections (layer 5).

    Returns:
        List of formatted section strings (may be empty).
    """
    parts: list[str] = []

    # Memory context
    if config.memory_entries:
        parts.append(format_memory_entries(config.memory_entries))

    # Conversation summary
    if config.conversation_summary:
        parts.append(f"## Conversation Summary\n{config.conversation_summary}")

    # Pending approvals
    if config.pending_approvals > 0:
        count = config.pending_approvals
        suffix = "s" if count > 1 else ""
        parts.append(f"\u26a0 {count} pending approval{suffix} awaiting your response.")

    # Budget warning
    if config.budget_warning:
        parts.append(f"\u26a0 Budget: {config.budget_warning}")

    return parts


def format_memory_entries(memory_entries: list[dict[str, Any]]) -> str:
    """Format recalled memory entries as a system prompt section.

    Replicates the logic from ``build_memory_context_prefix`` in
    ``pilotspace_intent_pipeline.py``.
    """
    lines = ["## Workspace Memory Context\n"]
    for entry in memory_entries:
        source = entry.get("source_type", "unknown")
        content = entry.get("content", "")
        lines.append(f"- [{source}] {content}")
    lines.append("")
    return "\n".join(lines)
