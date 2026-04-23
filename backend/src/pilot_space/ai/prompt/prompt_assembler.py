"""Static/dynamic prompt assembler for PilotSpace AI agent.

Assembles system prompts with a static/dynamic boundary for KV-cache
eligibility. Static prefix (identity, safety, role) is identical across
requests for the same workspace+role. Dynamic suffix (workspace context,
skills, disabled features, mentions) varies per request.
"""

from __future__ import annotations

import logging
import re

from pilot_space.ai.prompt.layer_loaders import (
    load_role_template,
    load_static_layer,
)
from pilot_space.ai.prompt.models import (
    AssembledPrompt,
    PromptLayerConfig,
)
from pilot_space.ai.proxy.tracing import observe  # pyright: ignore[reportAttributeAccessIssue]

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
    "- Be concise. No filler phrases. Reference blocks using \u00b6N notation."
)


@observe(name="prompt-assembly")  # pyright: ignore[reportUntypedFunctionDecorator]
async def assemble_system_prompt(config: PromptLayerConfig) -> AssembledPrompt:
    """Assemble a system prompt with static/dynamic split for KV-cache eligibility.

    The static prefix (identity + safety + role) is identical across requests
    for the same workspace+role combination and is eligible for KV-cache reuse.
    The dynamic suffix (workspace context, skills, disabled features, mentions)
    varies per request.

    Args:
        config: All inputs needed for prompt assembly.

    Returns:
        An ``AssembledPrompt`` with static_prefix, dynamic_suffix, the combined
        prompt, loaded layer names, and an estimated token count.
    """
    static_sections: list[str] = []
    dynamic_sections: list[str] = []
    layers_loaded: list[str] = []

    # --- STATIC PREFIX (KV-cache eligible) ---

    # Layer 1: Identity (always)
    identity = await load_static_layer("layer1_identity.md")
    if identity:
        static_sections.append(identity)
        layers_loaded.append("identity")
    else:
        logger.warning("layer1_identity.md missing — using hardcoded fallback")
        static_sections.append(config.base_prompt or _FALLBACK_IDENTITY)
        layers_loaded.append("identity:fallback")

    # Layer 2: Safety + tools + style (always)
    safety = await load_static_layer("layer2_safety_tools_style.md")
    if safety:
        static_sections.append(safety)
        layers_loaded.append("safety_tools_style")
    else:
        logger.warning("layer2_safety_tools_style.md missing — using hardcoded fallback")
        static_sections.append(_FALLBACK_SAFETY)
        layers_loaded.append("safety_tools_style:fallback")

    # Layer 3: Role adaptation (stable per workspace+role)
    if config.role_type:
        role_content = await load_role_template(config.role_type)
        if role_content:
            static_sections.append(f"## Your User's Role\n{role_content}")
            layers_loaded.append(f"role:{config.role_type}")

    # --- DYNAMIC SUFFIX (per-request) ---

    # Workspace context
    workspace_section = _build_workspace_section(config)
    if workspace_section:
        dynamic_sections.append(workspace_section)
        layers_loaded.append("workspace")

    # User skills (skip entirely when empty -- PROM-03)
    skills_section = _build_skills_section(config)
    if skills_section:
        dynamic_sections.append(skills_section)
        layers_loaded.append("skills")

    # Disabled features (skip entirely when empty -- PROM-03)
    disabled_section = _build_disabled_features_section(config)
    if disabled_section:
        dynamic_sections.append(disabled_section)
        layers_loaded.append("disabled_features")

    # Mention resolution (conditional on @[Type:uuid] tokens in message)
    if config.has_mention_context:
        dynamic_sections.append(_build_mention_resolution_rule())
        layers_loaded.append("mention_resolution")

    # --- COMBINE ---
    static_prefix = "\n\n".join(static_sections)
    dynamic_suffix = "\n\n".join(dynamic_sections) if dynamic_sections else ""
    combined = f"{static_prefix}\n\n{dynamic_suffix}" if dynamic_suffix else static_prefix
    estimated_tokens = len(combined) // 4

    result = AssembledPrompt(
        prompt=combined,
        static_prefix=static_prefix,
        dynamic_suffix=dynamic_suffix,
        layers_loaded=layers_loaded,
        estimated_tokens=estimated_tokens,
    )

    # PROM-04: Record token metrics for before/after comparison via Langfuse span
    try:
        from langfuse import Langfuse

        langfuse_client = Langfuse()
        langfuse_client.update_current_span(
            metadata={
                "estimated_prompt_tokens": result.estimated_tokens,
                "static_prefix_tokens": len(result.static_prefix) // 4,
                "dynamic_suffix_tokens": len(result.dynamic_suffix) // 4,
                "layers_loaded": result.layers_loaded,
                "context_mode": "slim",
            },
        )
    except Exception:
        pass  # Graceful degradation when Langfuse not configured (T-81-09)

    return result


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
    """Build the user skills section for the dynamic suffix.

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
    """Build the disabled features notice section for the dynamic suffix.

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


def _build_mention_resolution_rule() -> str:
    """Build the mention-resolution instruction for the dynamic suffix.

    Injected when the user message contains @[Type:uuid] entity references.
    Instructs the agent which MCP tools to call for each entity type.
    """
    return (
        "## Entity Reference Resolution\n\n"
        "The user message contains one or more `@[Type:uuid]` entity references. "
        "Before generating your response:\n"
        "1. For each `@[Note:uuid]`: call `mcp__pilot-notes-query__search_notes` with the note's UUID as the query "
        "and `include_content=True` to retrieve the note's title and content preview. "
        "If you need the full note content beyond the preview, follow up with "
        "`mcp__pilot-note-content__search_note_content` using the note UUID and a broad pattern (e.g., `.`) "
        "to retrieve all blocks.\n"
        "2. For each `@[Issue:uuid]`: call `mcp__pilot-issues__get_issue` with the UUID "
        "to retrieve the full issue description and all structured fields.\n"
        "3. For each `@[Project:uuid]`: call `mcp__pilot-projects__get_project_context` "
        "to retrieve project details and the names/titles of related notes and issues.\n\n"
        "If a tool returns an error or the entity is not found or inaccessible, "
        "skip that entity gracefully and continue processing the remaining references. "
        "Do not expose the error to the user.\n"
        "Never include raw `@[Type:uuid]` strings in your response."
    )
