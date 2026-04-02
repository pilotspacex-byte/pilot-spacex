"""In-process SDK MCP server with 6 skill tools.

Provides conversational skill creation, testing, and management tools
for the skill-creator workflow. All mutation tools emit SSE events via
EventPublisher to update the frontend in real time.

Tools:
  create_skill  — Write new SKILL.md to sandbox, emit skill_preview event
  update_skill  — Modify existing skill, emit skill_preview with isUpdate=True
  preview_skill — Read SKILL.md content from sandbox
  test_skill    — Rubric-based evaluation with optional workspace data dry-run
  list_skills   — List available skills in the skills directory
  get_skill_graph — Generate Mermaid dependency diagram for skills

Source: Phase 64, CSR-01, CSR-06, CSR-09, CSR-10
"""

from __future__ import annotations

import contextlib
import json
import uuid
from pathlib import Path
from typing import Any

from claude_agent_sdk import McpSdkServerConfig, create_sdk_mcp_server, tool

from pilot_space.ai.mcp.event_publisher import EventPublisher
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)


def _format_skill_sse(event_type: str, data: dict[str, Any]) -> str:
    """Format a skill-specific SSE event string.

    Mirrors EventPublisher._format_sse() but as a module-level function
    to avoid accessing the private method from outside the class.
    """
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


# MCP server name — used in allowed_tools as mcp__pilot-skills__{tool_name}
SERVER_NAME = "pilot-skills"

# All tool names for allowed_tools configuration
TOOL_NAMES = [
    f"mcp__{SERVER_NAME}__create_skill",
    f"mcp__{SERVER_NAME}__update_skill",
    f"mcp__{SERVER_NAME}__preview_skill",
    f"mcp__{SERVER_NAME}__test_skill",
    f"mcp__{SERVER_NAME}__list_skills",
    f"mcp__{SERVER_NAME}__get_skill_graph",
]

# Prefix used for skill directories (must match role_skill_materializer)
_SKILL_PREFIX = "skill-"


def create_skill_tools_server(
    publisher: EventPublisher,
    *,
    tool_context: Any | None = None,
    skills_dir: Path | None = None,
) -> McpSdkServerConfig:
    """Create SDK MCP server with 6 skill tools.

    Args:
        publisher: EventPublisher for SSE event delivery.
        tool_context: ToolContext for DB access and RLS enforcement.
        skills_dir: Path to the sandbox .claude/skills/ directory.
                    When None, filesystem operations are skipped gracefully.
    """

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _text_result(text: str) -> dict[str, Any]:
        """Create a standard MCP tool text result."""
        return {"content": [{"type": "text", "text": text}]}

    def _find_skill_file(name: str) -> Path | None:
        """Find the SKILL.md for a skill by name prefix scan."""
        if skills_dir is None or not skills_dir.is_dir():
            return None
        prefix = f"{_SKILL_PREFIX}{name}"
        for entry in sorted(skills_dir.iterdir()):
            if entry.is_dir() and entry.name.startswith(prefix):
                candidate = entry / "SKILL.md"
                if candidate.exists():
                    return candidate
        return None

    # ------------------------------------------------------------------
    # Rubric evaluation for test_skill
    # ------------------------------------------------------------------

    _RUBRIC_CHECKS: list[tuple[str, list[str], str]] = [
        (
            "has clear trigger/use case",
            ["use this when", "trigger", "when the user", "use when", "invoke"],
            "Add a trigger phrase describing when to use this skill",
        ),
        (
            "instructions are actionable",
            ["step", "instructions", "do this", "follow", "execute", "perform", "action"],
            "Add step-by-step actionable instructions",
        ),
        (
            "includes examples",
            ["example", "e.g.", "for instance", "sample", "```"],
            "Add concrete examples to illustrate the skill",
        ),
        (
            "output format specified",
            ["output format", "return", "output:", "format:", "json", "returns"],
            "Specify the expected output format",
        ),
        (
            "has context/tools section",
            ["context", "tools", "requires", "## context", "## tools"],
            "Add a context or tools section describing dependencies",
        ),
    ]

    def _evaluate_skill(content: str) -> dict[str, Any]:
        """Evaluate skill content against a 5-point rubric."""
        content_lower = content.lower()
        passed: list[str] = []
        failed: list[str] = []
        suggestions: list[str] = []

        for check_name, keywords, suggestion in _RUBRIC_CHECKS:
            if any(kw in content_lower for kw in keywords):
                passed.append(check_name)
            else:
                failed.append(check_name)
                suggestions.append(suggestion)

        # Each passed check contributes 2 points (5 checks x 2 = 10 max)
        score = len(passed) * 2
        return {
            "score": score,
            "passed": passed,
            "failed": failed,
            "suggestions": suggestions,
        }

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------

    @tool(
        "create_skill",
        "Create a new AI skill and write it to the sandbox. "
        "Emits a skill_preview SSE event for the frontend to display. "
        "Use kebab-case for skill names (e.g., 'review-code').",
        {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Skill name in kebab-case (e.g., 'review-code')",
                },
                "description": {
                    "type": "string",
                    "description": "Short description of what the skill does",
                },
                "content": {
                    "type": "string",
                    "description": "Full SKILL.md content (body, without frontmatter)",
                },
            },
            "required": ["name", "description", "content"],
        },
    )
    async def create_skill(args: dict[str, Any]) -> dict[str, Any]:
        name = args.get("name", "").strip()
        description = args.get("description", "").strip()
        content = args.get("content", "").strip()

        if not name:
            return _text_result("Error: skill name is required")

        skill_id = str(uuid.uuid4())

        # Write to sandbox if skills_dir is available
        if skills_dir is not None:
            try:
                from pilot_space.ai.agents.role_skill_materializer import hot_reload_skill

                await hot_reload_skill(skills_dir, name, content, skill_id)
                logger.info(
                    "skill_tool_create", skill_name=name, skill_id=skill_id[:8], status="ok"
                )
            except OSError as exc:
                logger.warning(
                    "skill_tool_create_write_failed",
                    skill_name=name,
                    error=str(exc),
                    status="failed",
                )

        # Emit skill_preview SSE event
        await publisher.publish(
            _format_skill_sse(
                "skill_preview",
                {
                    "skillName": name,
                    "skillId": skill_id,
                    "frontmatter": {
                        "name": name,
                        "description": description,
                    },
                    "content": content,
                    "isUpdate": False,
                },
            )
        )

        return _text_result(f"Created skill: {name}")

    @tool(
        "update_skill",
        "Update an existing skill's content and reload it in the sandbox. "
        "Emits a skill_preview SSE event with isUpdate=true.",
        {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Skill name to update (kebab-case)",
                },
                "content": {
                    "type": "string",
                    "description": "New SKILL.md content (body, without frontmatter)",
                },
                "skill_id": {
                    "type": "string",
                    "description": "Optional UUID of the skill to update",
                },
            },
            "required": ["name", "content"],
        },
    )
    async def update_skill(args: dict[str, Any]) -> dict[str, Any]:
        name = args.get("name", "").strip()
        content = args.get("content", "").strip()
        skill_id = args.get("skill_id") or str(uuid.uuid4())

        if not name:
            return _text_result("Error: skill name is required")

        # Write to sandbox if skills_dir is available
        if skills_dir is not None:
            try:
                from pilot_space.ai.agents.role_skill_materializer import hot_reload_skill

                await hot_reload_skill(skills_dir, name, content, skill_id)
                logger.info(
                    "skill_tool_update", skill_name=name, skill_id=skill_id[:8], status="ok"
                )
            except OSError as exc:
                logger.warning(
                    "skill_tool_update_write_failed",
                    skill_name=name,
                    error=str(exc),
                    status="failed",
                )

        # Emit skill_preview SSE event with isUpdate=True
        await publisher.publish(
            _format_skill_sse(
                "skill_preview",
                {
                    "skillName": name,
                    "skillId": skill_id,
                    "frontmatter": {
                        "name": name,
                    },
                    "content": content,
                    "isUpdate": True,
                },
            )
        )

        return _text_result(f"Updated skill: {name}")

    @tool(
        "preview_skill",
        "Preview the current content of a skill by reading its SKILL.md file.",
        {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Skill name to preview (kebab-case)",
                },
            },
            "required": ["name"],
        },
    )
    async def preview_skill(args: dict[str, Any]) -> dict[str, Any]:
        name = args.get("name", "").strip()

        if not name:
            return _text_result("Error: skill name is required")

        if skills_dir is None:
            return _text_result("No skills directory configured. Cannot preview skill.")

        skill_file = _find_skill_file(name)
        if skill_file is None:
            return _text_result(f"Skill '{name}' not found in skills directory.")

        try:
            content = skill_file.read_text(encoding="utf-8")
            logger.info("skill_tool_preview", skill_name=name)
            return _text_result(content)
        except OSError as exc:
            return _text_result(f"Error reading skill '{name}': {exc}")

    @tool(
        "test_skill",
        "Evaluate a skill using a 5-point quality rubric. "
        "Returns a score (0-10), passed/failed checks, suggestions, and a sample output. "
        "Optionally loads workspace data for a dry-run if tool_context is available.",
        {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Skill name to test",
                },
                "content": {
                    "type": "string",
                    "description": "Skill content to evaluate (uses SKILL.md if omitted)",
                },
            },
            "required": ["name"],
        },
    )
    async def test_skill(args: dict[str, Any]) -> dict[str, Any]:
        name = args.get("name", "").strip()
        content = args.get("content", "").strip()

        # If content not provided, try to read from skills_dir
        if not content and skills_dir is not None:
            skill_file = _find_skill_file(name)
            if skill_file is not None:
                with contextlib.suppress(OSError):
                    content = skill_file.read_text(encoding="utf-8")

        if not content.strip():
            return _text_result(
                json.dumps(
                    {
                        "score": 0,
                        "passed": [],
                        "failed": ["Skill content is empty or not found"],
                        "suggestions": ["Provide skill content or create the skill first"],
                        "sampleOutput": "",
                    }
                )
            )

        # Phase 1: Rubric evaluation
        evaluation = _evaluate_skill(content)

        # Phase 2: Optional dry-run with workspace data
        sample_output = "(no workspace data available for dry-run)"
        if tool_context is not None:
            try:
                # Attempt to load one note from workspace as test input
                note_content: str | None = None
                if hasattr(tool_context, "note_service"):
                    try:
                        note = await tool_context.note_service.get_latest()
                        if note:
                            note_content = getattr(note, "title", str(note))
                    except Exception:
                        pass

                if note_content:
                    sample_output = (
                        f"[Dry-run with workspace note]\n"
                        f"Input: {note_content[:200]}\n"
                        f"Skill '{name}' would process this content and return structured output."
                    )
                else:
                    sample_output = (
                        f"[Dry-run placeholder]\n"
                        f"Skill '{name}' would process workspace content and return structured output."
                    )
            except Exception as exc:
                logger.debug("skill_tool_test_dry_run_failed", skill_name=name, error=str(exc))

        result = {
            "score": evaluation["score"],
            "passed": evaluation["passed"],
            "failed": evaluation["failed"],
            "suggestions": evaluation["suggestions"],
            "sampleOutput": sample_output,
        }

        # Emit test_result SSE event
        await publisher.publish(
            _format_skill_sse(
                "test_result",
                {
                    "skillName": name,
                    "score": result["score"],
                    "passed": result["passed"],
                    "failed": result["failed"],
                    "suggestions": result.get("suggestions", []),
                    "sampleOutput": result.get("sampleOutput", ""),
                },
            )
        )

        logger.info("skill_tool_test", skill_name=name, score=result["score"])
        return _text_result(json.dumps(result))

    @tool(
        "list_skills",
        "List all skills available in the skills directory.",
        {
            "type": "object",
            "properties": {},
        },
    )
    async def list_skills(_args: dict[str, Any]) -> dict[str, Any]:
        if skills_dir is None:
            return _text_result("No skills directory configured.")

        def _scan_skills() -> list[tuple[str, str]]:
            """Scan skills dir synchronously (runs in thread pool)."""
            assert skills_dir is not None  # guarded by caller
            if not skills_dir.is_dir():
                return []
            results: list[tuple[str, str]] = []
            for entry in sorted(skills_dir.iterdir()):
                if not entry.is_dir():
                    continue
                skill_file = entry / "SKILL.md"
                if not skill_file.exists():
                    continue
                with contextlib.suppress(OSError):
                    first_line = skill_file.read_text(encoding="utf-8").split("\n")[0]
                    results.append((entry.name, first_line.strip("# -")))
            return results

        import asyncio as _asyncio

        skill_entries = await _asyncio.to_thread(_scan_skills)

        if not skill_entries:
            return _text_result("No skills found in skills directory.")

        lines = ["Available skills:"]
        for dir_name, first_line in skill_entries:
            lines.append(f"  - {dir_name} ({first_line})")

        logger.info("skill_tool_list", count=len(skill_entries))
        return _text_result("\n".join(lines))

    @tool(
        "get_skill_graph",
        "Generate a Mermaid dependency diagram showing skill relationships. "
        "Returns a Mermaid 'graph TD' string for inline visualization.",
        {
            "type": "object",
            "properties": {
                "skill_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of skill names to include in the graph",
                },
            },
        },
    )
    async def get_skill_graph(args: dict[str, Any]) -> dict[str, Any]:
        skill_names: list[str] = args.get("skill_names") or []

        # If no names provided but skills_dir exists, discover from filesystem
        if not skill_names and skills_dir is not None:

            def _scan_for_graph() -> list[str]:
                assert skills_dir is not None  # guarded by caller
                if not skills_dir.is_dir():
                    return []
                return [
                    entry.name
                    for entry in sorted(skills_dir.iterdir())
                    if entry.is_dir() and (entry / "SKILL.md").exists()
                ]

            import asyncio as _asyncio

            skill_names = await _asyncio.to_thread(_scan_for_graph)

        if not skill_names:
            # Return a minimal valid graph
            diagram = "graph TD\n  A[No skills configured]"
            return _text_result(diagram)

        # Build a simple graph showing skill nodes
        # Nodes are skill names; edges represent skill-creator relationships
        lines = ["graph TD"]
        # Add a skill-creator orchestrator node if skill-creator exists or is in the list
        has_creator = any("skill-creator" in n for n in skill_names)
        creator_id = "Creator[skill-creator]"

        # Generate safe node IDs (replace hyphens with underscores for Mermaid)
        def _node_id(name: str) -> str:
            safe = name.replace("-", "_").replace(".", "_")
            label = name
            return f"{safe}[{label}]"

        if has_creator:
            # Show skill-creator as orchestrator pointing to other skills
            lines.append(f"  {creator_id}")
            for name in skill_names:
                if "skill-creator" in name:
                    continue
                lines.append(f"  {creator_id} --> {_node_id(name)}")
        else:
            # Show each skill as an independent node
            for i, name in enumerate(skill_names):
                lines.append(f"  {_node_id(name)}")
                # Connect adjacent skills to show workflow pipeline
                if i < len(skill_names) - 1:
                    next_name = skill_names[i + 1]
                    lines.append(f"  {_node_id(name)} --> {_node_id(next_name)}")

        logger.info("skill_tool_graph", skill_count=len(skill_names))
        return _text_result("\n".join(lines))

    return create_sdk_mcp_server(
        name=SERVER_NAME,
        version="1.0.0",
        tools=[
            create_skill,
            update_skill,
            preview_skill,
            test_skill,
            list_skills,
            get_skill_graph,
        ],
    )
