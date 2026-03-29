"""Graph compiler prompts for AI-assisted SKILL.md synthesis.

Provides system prompt and formatting helpers for the LLM to transform
topologically-sorted graph nodes into coherent, human-readable SKILL.md content.

Phase 053: Graph-to-Skill Compiler
"""

from __future__ import annotations

from typing import Any


def get_graph_compile_system_prompt() -> str:
    """Return the system prompt for AI-assisted graph compilation.

    Instructs the LLM to synthesize mechanical step-by-step node instructions
    into flowing, professional skill text that reads like human-written documentation.

    Returns:
        System prompt string.
    """
    return """\
You are a skill compiler for Pilot Space, an AI-augmented software development platform.

Your task: Given a workflow graph (nodes + edges in topological order), synthesize them \
into a coherent, human-readable SKILL.md document.

Guidelines:
- Transform mechanical step-by-step node instructions into flowing, professional skill text.
- Preserve ALL semantic meaning from nodes: prompts, conditions, transforms, skill references.
- Use markdown headers (##) for major sections.
- Use code blocks for templates, expressions, and configuration.
- Write in second person ("You should...", "The skill will...") for instructions.
- Group related steps when they form a logical unit.
- Add transitional text between sections so the document flows naturally.
- Include a brief overview paragraph after the frontmatter.
- For condition nodes, describe the branching logic clearly in prose.
- For skill references, explain what the referenced skill does and how its output is used.
- For transform nodes, explain the transformation in plain language before showing the template.

Output format:
- Return ONLY the SKILL.md content as markdown.
- Start with YAML frontmatter (--- delimited) containing description and node_count.
- Do NOT wrap in JSON or code fences.
- Do NOT add explanatory text outside the SKILL.md content."""


def format_graph_for_llm(
    sorted_nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    template_name: str = "Untitled Skill",
) -> str:
    """Format topologically sorted graph data into a structured prompt for the LLM.

    Lists each node with its type, label, configuration, and connections
    so the LLM can understand the workflow and synthesize coherent text.

    Args:
        sorted_nodes: Nodes in topological order (from Kahn's algorithm).
        edges: Graph edges with source/target and optional type/data.
        template_name: Name of the skill template for context.

    Returns:
        Formatted user message string for the LLM.
    """
    lines: list[str] = []
    lines.append(f"# Skill Graph: {template_name}")
    lines.append("")
    lines.append(f"Total nodes: {len(sorted_nodes)}")
    lines.append(f"Total edges: {len(edges)}")
    lines.append("")

    # Build edge lookup for connections
    outgoing: dict[str, list[dict[str, Any]]] = {}
    incoming: dict[str, list[dict[str, Any]]] = {}
    for edge in edges:
        src = edge.get("source", "")
        tgt = edge.get("target", "")
        outgoing.setdefault(src, []).append(edge)
        incoming.setdefault(tgt, []).append(edge)

    lines.append("## Nodes (topological order)")
    lines.append("")

    for i, node in enumerate(sorted_nodes, 1):
        data = node.get("data", {})
        node_id = node.get("id", "?")
        node_type = data.get("nodeType", node.get("type", "unknown"))
        label = data.get("label", "Untitled")
        config = data.get("config", {})

        lines.append(f"### Node {i}: [{node_type}] {label} (id={node_id})")

        # Configuration
        if config:
            lines.append("Configuration:")
            for key, value in sorted(config.items()):
                lines.append(f"  - {key}: {value}")

        # Connections
        node_outgoing = outgoing.get(node_id, [])
        node_incoming = incoming.get(node_id, [])

        if node_incoming:
            from_labels = []
            for e in node_incoming:
                src_id = e.get("source", "?")
                edge_type = e.get("type", "sequential")
                branch = e.get("data", {}).get("branch", "")
                suffix = f" ({edge_type}" + (f":{branch}" if branch else "") + ")" if edge_type != "sequential" else ""
                from_labels.append(f"{src_id}{suffix}")
            lines.append(f"Receives from: {', '.join(from_labels)}")

        if node_outgoing:
            to_labels = []
            for e in node_outgoing:
                tgt_id = e.get("target", "?")
                edge_type = e.get("type", "sequential")
                branch = e.get("data", {}).get("branch", "")
                suffix = f" ({edge_type}" + (f":{branch}" if branch else "") + ")" if edge_type != "sequential" else ""
                to_labels.append(f"{tgt_id}{suffix}")
            lines.append(f"Sends to: {', '.join(to_labels)}")

        lines.append("")

    lines.append("## Instructions")
    lines.append("")
    lines.append("Synthesize the above nodes into a coherent SKILL.md document.")
    lines.append("Transform the mechanical steps into natural, flowing instructions.")

    return "\n".join(lines)


__all__ = [
    "format_graph_for_llm",
    "get_graph_compile_system_prompt",
]
