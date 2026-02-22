"""Implementation Plan prompt templates.

Provides system prompts and response parsing for plan generation:
- One-shot Claude query producing structured JSON
- JSON-to-YAML-frontmatter-markdown conversion (canonical plan format)
- Graceful fallback on malformed model output
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# System Prompt
# =============================================================================

PLAN_SYSTEM_PROMPT = """You are an expert software architect embedded in Pilot Space, an AI-augmented SDLC platform.

Your task is to generate a structured implementation plan for a software issue. The plan decomposes work into parallel subagent tasks that can be executed concurrently by Claude Code in orchestrator mode.

Each subagent is an autonomous Claude Code agent that will read files, write code, and run commands entirely on its own — with no human guidance during execution. Every field you produce must be self-sufficient for that agent to complete its work correctly.

## Output Format

Respond with a SINGLE valid JSON object — no prose, no markdown, no explanations outside the JSON:

```json
{
  "outcome": "A 2-3 sentence paragraph describing what success looks like after this issue is implemented. Include specific verifiable evidence of success (e.g. 'POST /issues/{id}/ai-context/plan returns 200 with subagent_count > 0').",
  "subagents": [
    {
      "id": "sa-1",
      "role": "python-expert | frontend-expert | backend-expert | ml-expert | Bash | general-purpose | security-expert",
      "task": "Full standalone prompt for this subagent (3-6 sentences). Must include: (1) what to implement, (2) which pattern/reference file to follow first, (3) which files to create or modify, (4) quality gate command to run at the end.",
      "context": "Technical context this subagent needs: the relevant architectural pattern (e.g. 'CQRS-lite: Service.execute(Payload) -> Result, follow generate_ai_context_service.py'), the DI registration file to update, any non-obvious constraint (e.g. 'workspace_id comes from X-Workspace-Id header, not URL'). Be specific — vague context produces wrong code.",
      "files": [
        "backend/src/pilot_space/application/services/ai_context/generate_ai_context_service.py",
        "backend/src/pilot_space/api/v1/routers/issues_ai_context.py"
      ],
      "steps": [
        "Read CLAUDE.md and backend/README.md to understand project conventions.",
        "Read the pattern reference file listed in context before writing any code.",
        "Implement: <specific function/class/endpoint name> in <exact file path>.",
        "Register in DI container: <exact container file and provider key>.",
        "Run quality gate: uv run pyright && uv run ruff check && uv run pytest -x --tb=short (backend) OR pnpm type-check && pnpm lint && pnpm test --run (frontend).",
        "Verify: <specific curl command or assertion that proves the work is correct>."
      ],
      "acceptance_criteria": [
        "Criterion 1 — verifiable with a specific command or observable output",
        "Criterion 2 — pyright/tsc reports 0 errors",
        "Criterion 3 — pytest/vitest test for the new code passes"
      ],
      "depends_on": []
    }
  ],
  "related_issues": [
    {
      "identifier": "PS-38",
      "title": "Issue title",
      "relation": "blocks | relates | blocked_by"
    }
  ]
}
```

## Design Rules

- **Maximise parallelism**: Group independent tasks so they can run concurrently. Use `depends_on` only when a task genuinely cannot start before another finishes (e.g. frontend depends on backend schema being finalised).
- **Use correct Claude Code agent types for `role`**: `python-expert` for FastAPI/SQLAlchemy/Python; `frontend-expert` for React/TypeScript/Next.js/TailwindCSS; `backend-expert` for general backend; `Bash` for CI, migrations, or shell-only tasks; `security-expert` for auth/RLS work. Do NOT use `backend-engineer`, `qa-engineer`, or `devops-engineer` — these are not valid Claude Code subagent types.
- **`task` must be a self-sufficient prompt**: The `task` field is passed verbatim as the Claude Code Task tool `prompt` parameter. Write it as if briefing a competent engineer who has never seen the codebase. Include the pattern to follow, the files to change, and the quality gate to run.
- **`context` must cite specific files**: Do not say "follow existing patterns." Say "follow the pattern in `backend/src/pilot_space/application/services/ai_context/generate_ai_context_service.py`."
- **Every `steps` list must end with a quality gate command**: Backend gate: `uv run pyright && uv run ruff check && uv run pytest -x`. Frontend gate: `pnpm type-check && pnpm lint && pnpm test --run`. Include the exact command, not a generic reminder.
- **File paths are relative** to the repository root (e.g. `backend/src/pilot_space/api/v1/routers/issues.py`).
- **Limit subagents**: 2-6 subagents is ideal. Do not create a subagent per file; group related changes by domain (backend service+endpoint together, frontend component+hook together).
- **DO NOT use any tools.** All context is provided below.
- **Respond ONLY with a single JSON code block.**"""


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class SubagentSpec:
    """Specification for a single subagent in the implementation plan."""

    id: str
    role: str
    task: str
    context: str
    files: list[str] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)


# =============================================================================
# Prompt Building
# =============================================================================


def build_plan_prompt(
    *,
    issue_title: str,
    issue_description: str | None,
    issue_identifier: str,
    context_data: dict[str, Any] | None = None,
    related_issues: list[dict[str, Any]] | None = None,
    code_references: list[dict[str, Any]] | None = None,
) -> str:
    """Build the user-facing prompt for plan generation.

    Args:
        issue_title: Issue title/name.
        issue_description: Issue description text (may be None).
        issue_identifier: Human-readable identifier (e.g. PS-42).
        context_data: Existing AIContext content dict (summary, analysis, etc.).
        related_issues: Pre-discovered related issues.
        code_references: Pre-extracted code file references.

    Returns:
        Formatted user prompt string.
    """
    parts: list[str] = [
        f"## Issue: {issue_identifier}\n",
        f"**Title:** {issue_title}\n",
    ]

    if issue_description:
        parts.append(f"\n**Description:**\n{issue_description}\n")

    if context_data:
        summary = context_data.get("summary", "")
        analysis = context_data.get("analysis", "")
        complexity = context_data.get("complexity", "")
        estimated_effort = context_data.get("estimated_effort", "")
        suggested_approach = context_data.get("suggested_approach", "")

        if summary:
            parts.append(f"\n## AI-Generated Summary\n{summary}\n")
        if analysis:
            parts.append(f"\n## Technical Analysis\n{analysis}\n")
        if complexity or estimated_effort:
            parts.append(f"\n**Complexity**: {complexity} | **Effort**: {estimated_effort}\n")
        if suggested_approach:
            parts.append(f"\n**Suggested Approach**: {suggested_approach}\n")

        tasks_checklist = context_data.get("tasks_checklist", [])
        if tasks_checklist:
            parts.append("\n## Existing Task Breakdown\n")
            for task in tasks_checklist:
                if isinstance(task, dict):
                    desc = task.get("description", "")
                    effort = task.get("estimated_effort", "")
                    parts.append(f"- {desc} ({effort})\n")

    if related_issues:
        parts.append("\n## Related Issues\n")
        for issue in related_issues[:8]:
            identifier = issue.get("identifier", "???")
            title = issue.get("title", "Untitled")
            parts.append(f"- {identifier}: {title}\n")

    if code_references:
        parts.append("\n## Relevant Code Files\n")
        for ref in code_references[:15]:
            file_path = ref.get("file_path", "")
            description = ref.get("description", "")
            if file_path:
                parts.append(f"- `{file_path}`: {description}\n")

    parts.append(
        "\n## Project Quality Gates\n"
        "Every subagent's `steps` list MUST end with the correct quality gate command:\n"
        "- **Backend** (FastAPI/Python): `uv run pyright && uv run ruff check && uv run pytest -x --tb=short`\n"
        "- **Frontend** (Next.js/TypeScript): `pnpm type-check && pnpm lint && pnpm test --run`\n"
        "- **Bash/infra** (migrations, CI): use the appropriate shell command for the task.\n"
        "\n## Pattern Reference Files\n"
        "Direct subagents to read these before implementing:\n"
        "- Backend service: `backend/src/pilot_space/application/services/ai_context/generate_ai_context_service.py`\n"
        "- Backend router: `backend/src/pilot_space/api/v1/routers/issues_ai_context.py`\n"
        "- DI container: `backend/src/pilot_space/container.py`\n"
        "- Frontend API client: `frontend/src/services/api/issues.ts`\n"
        "- Frontend component: `frontend/src/features/issues/components/clone-context-panel.tsx`\n"
        "- Project conventions: `CLAUDE.md`, `backend/README.md`, `frontend/README.md`\n"
        "\nGenerate a structured implementation plan with parallel subagent tasks. "
        "Output only the JSON object as specified in your instructions."
    )

    return "".join(parts)


# =============================================================================
# Response Parsing
# =============================================================================


def parse_plan_response(
    response_text: str,
    issue_identifier: str,
    issue_title: str,
) -> str:
    """Parse JSON model response into canonical YAML-frontmatter markdown.

    On any parse error, returns a non-empty fallback skeleton — never raises.

    Args:
        response_text: Raw text from AI model (may contain code fences).
        issue_identifier: Used in YAML front matter and markdown heading.
        issue_title: Used in YAML front matter and markdown heading.

    Returns:
        Canonical YAML-frontmatter markdown string ready for persistence.
    """
    data = _extract_json(response_text)
    if data is None:
        logger.warning(
            "parse_plan_response: malformed JSON for %s — returning fallback",
            issue_identifier,
        )
        return _build_fallback_plan(issue_identifier, issue_title)

    outcome: str = data.get("outcome", "Implementation outcome not specified.")
    raw_subagents: list[Any] = data.get("subagents", [])
    raw_related: list[Any] = data.get("related_issues", [])

    subagents = [
        _parse_subagent(sa, idx) for idx, sa in enumerate(raw_subagents) if isinstance(sa, dict)
    ]
    related = [r for r in raw_related if isinstance(r, dict)]

    return _render_markdown(
        issue_identifier=issue_identifier,
        issue_title=issue_title,
        outcome=outcome,
        subagents=subagents,
        related_issues=related,
    )


# =============================================================================
# Private helpers
# =============================================================================


def _extract_json(text: str) -> dict[str, Any] | None:
    """Extract and parse JSON from response text, handling code fences."""
    # Try code-fenced JSON first
    fenced = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
    if fenced:
        try:
            result = json.loads(fenced.group(1))
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

    # Try raw JSON object
    raw = re.search(r"\{[\s\S]*?\}", text)
    if raw:
        try:
            result = json.loads(raw.group())
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

    return None


def _parse_subagent(data: dict[str, Any], idx: int) -> SubagentSpec:
    """Construct a SubagentSpec from a raw dict with safe defaults."""
    return SubagentSpec(
        id=data.get("id", f"sa-{idx + 1}"),
        role=data.get("role", "backend-engineer"),
        task=data.get("task", ""),
        context=data.get("context", ""),
        files=_ensure_str_list(data.get("files", [])),
        steps=_ensure_str_list(data.get("steps", [])),
        acceptance_criteria=_ensure_str_list(data.get("acceptance_criteria", [])),
        depends_on=_ensure_str_list(data.get("depends_on", [])),
    )


def _ensure_str_list(value: Any) -> list[str]:
    """Coerce value to a list of strings."""
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None]


def _role_display(role: str) -> str:
    """Convert role slug to display name."""
    display = {
        "backend-engineer": "Backend Engineer",
        "frontend-expert": "Frontend Expert",
        "qa-engineer": "QA Engineer",
        "ml-expert": "ML Expert",
        "devops-engineer": "DevOps Engineer",
    }
    return display.get(role, role.replace("-", " ").title())


def _render_markdown(
    *,
    issue_identifier: str,
    issue_title: str,
    outcome: str,
    subagents: list[SubagentSpec],
    related_issues: list[dict[str, Any]],
) -> str:
    """Render the canonical YAML-frontmatter markdown plan document."""
    generated_at = datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Sanitize title for safe YAML embedding (prevent injection)
    safe_title = issue_title.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")

    # --- YAML front matter ---
    lines: list[str] = ["---"]
    lines.append(f"issue: {issue_identifier}")
    lines.append(f'title: "{safe_title}"')
    lines.append(f"generated: {generated_at}")
    lines.append("orchestrator: true")
    lines.append("model: claude-sonnet-4-6")

    if subagents:
        lines.append("subagents:")
        for sa in subagents:
            lines.append(f"  - id: {sa.id}")
            lines.append(f"    role: {sa.role}")
            safe_task = sa.task.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
            lines.append(f'    task: "{safe_task}"')
            if sa.depends_on:
                deps = ", ".join(sa.depends_on)
                lines.append(f"    depends_on: [{deps}]")
            else:
                lines.append("    depends_on: []")

    lines.append("---")
    lines.append("")

    # --- Document body ---
    lines.append(f"# {issue_identifier}: {issue_title}")
    lines.append("")
    lines.append("## Target Outcome")
    lines.append(outcome)
    lines.append("")

    if related_issues:
        lines.append("## Related Issues")
        for r in related_issues:
            identifier = r.get("identifier", "???")
            title = r.get("title", "")
            relation = r.get("relation", "relates")
            lines.append(f"- {identifier}: {title} ({relation})")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Subagents")
    lines.append("")

    for sa in subagents:
        role_label = _role_display(sa.role)
        lines.append(f"### {sa.id} — {role_label}")
        lines.append(f"**Role**: {role_label}.")
        lines.append("")

        if sa.context:
            lines.append("**Context**")
            lines.append(sa.context)
            lines.append("")

        if sa.files:
            lines.append("**Relevant Files**")
            for f in sa.files:
                lines.append(f"- `{f}`")
            lines.append("")

        if sa.steps:
            lines.append("**Steps**")
            for i, step in enumerate(sa.steps, 1):
                lines.append(f"{i}. {step}")
            lines.append("")

        if sa.acceptance_criteria:
            lines.append("**Acceptance Criteria**")
            for criterion in sa.acceptance_criteria:
                lines.append(f"- [ ] {criterion}")
            lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def _build_fallback_plan(issue_identifier: str, issue_title: str) -> str:
    """Return a minimal skeleton plan when JSON parsing fails."""
    generated_at = datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    safe_title = issue_title.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
    return (
        f"---\n"
        f"issue: {issue_identifier}\n"
        f'title: "{safe_title}"\n'
        f"generated: {generated_at}\n"
        f"orchestrator: true\n"
        f"model: claude-sonnet-4-6\n"
        f"subagents: []\n"
        f"---\n\n"
        f"# {issue_identifier}: {issue_title}\n\n"
        f"## Target Outcome\n\n"
        f"Plan generation encountered a parsing error. "
        f"Please regenerate or manually define subagent tasks.\n\n"
        f"---\n\n"
        f"## Subagents\n\n"
        f"No subagents were parsed from the model response.\n"
    )


__all__ = [
    "PLAN_SYSTEM_PROMPT",
    "SubagentSpec",
    "build_plan_prompt",
    "parse_plan_response",
]
