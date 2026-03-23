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
import re
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

    # Layer 4.5: User skills (between workspace and session)
    skills_section = _build_skills_section(config)
    if skills_section:
        sections.append(skills_section)
        layers_loaded.append("skills")

    # Layer 4.6: Disabled features notice (between skills and session)
    disabled_section = _build_disabled_features_section(config)
    if disabled_section:
        sections.append(disabled_section)
        layers_loaded.append("disabled_features")

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


def _sanitize_skill_text(text: str, max_length: int) -> str:
    """Sanitize user-controlled skill text for safe prompt injection.

    Strips newlines, collapses whitespace, and truncates to max_length.

    Args:
        text: Raw user-provided text.
        max_length: Maximum allowed character count.

    Returns:
        Sanitized text safe for system prompt inclusion.
    """
    cleaned = re.sub(r"\s+", " ", text).strip()
    return cleaned[:max_length]


def _build_skills_section(config: PromptLayerConfig) -> str | None:
    """Build the user skills section for the prompt (layer 4.5).

    Positioned between workspace context (layer 4) and session state (layer 5)
    so the agent can reference available skills when forming responses.

    Returns:
        Formatted "## Your Skills" section, or None if no active skills.
    """
    if not config.user_skills:
        return None
    lines = ["## Your Skills", "", "You have access to the following personalized skills:"]
    for skill in config.user_skills:
        name = _sanitize_skill_text(skill.get("name", "Unknown"), 80) or "Unnamed Skill"
        desc = _sanitize_skill_text(skill.get("description", ""), 240)
        if desc:
            lines.append(f"- **{name}**: {desc}")
        else:
            lines.append(f"- **{name}**")
    lines.append("")
    lines.append("Proactively suggest relevant skills when they match the user's request.")
    return "\n".join(lines)


def _build_disabled_features_section(config: PromptLayerConfig) -> str | None:
    """Build the disabled features notice section for the prompt (layer 4.6).

    When workspace features are disabled, the agent should not attempt to use
    related tools and should politely inform the user.

    Returns:
        Formatted "## Disabled Features" section, or None if all features enabled.
    """
    disable_features = ", ".join([k for k, v in config.feature_toggles.items() if not v])
    if not disable_features:
        return None
    return (
        f"## Disabled Workspace Features\n\n"
        f"The following features are currently disabled in this workspace: {disable_features}.\n"
        f"If the user requests functionality related to a disabled feature, politely inform them "
        f"that the feature is not enabled and suggest they ask a workspace admin to enable it "
        f"in Settings > Features."
    )


def _build_session_section(config: PromptLayerConfig) -> list[str]:
    """Build session state sections (layer 5).

    Returns:
        List of formatted section strings (may be empty).
    """
    parts: list[str] = []

    # Memory context: graph-based context takes precedence over legacy memory entries
    if config.graph_context:
        parts.append(format_graph_context(config.graph_context))
    elif config.memory_entries:
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


def format_graph_context(graph_context: list[dict[str, Any]]) -> str:
    """Format knowledge graph nodes as a system prompt section.

    Args:
        graph_context: List of scored node dicts from recall_graph_context.

    Returns:
        Formatted markdown section, or empty string when graph_context is empty.
    """
    if not graph_context:
        return ""
    lines = ["## Workspace Knowledge Graph Context\n"]
    for entry in graph_context:
        node_type = entry.get("node_type", "unknown")
        label = entry.get("label", "")
        content = entry.get("content", "")
        lines.append(f"- [{node_type}] **{label}**: {content}")
    lines.append("")
    return "\n".join(lines)
