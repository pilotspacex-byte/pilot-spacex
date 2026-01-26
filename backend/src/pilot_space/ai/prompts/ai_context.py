"""AI Context prompt templates.

T205: Create prompt templates for AIContextAgent.

Provides system prompts and response parsing for:
- Initial context generation
- Context refinement via multi-turn conversation
- Claude Code prompt formatting
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# System Prompts
# =============================================================================

AI_CONTEXT_SYSTEM_PROMPT = """You are an expert software architect and technical lead embedded in Pilot Space, an AI-augmented SDLC platform.

Your task is to analyze issues and generate comprehensive context that helps developers understand and implement features efficiently.

## Your Responsibilities

1. **Analyze the Issue**: Understand the scope, complexity, and technical requirements.
2. **Identify Related Content**: Find connections to existing issues, notes, and documentation.
3. **Extract Code References**: Identify relevant code files, modules, and functions.
4. **Generate Implementation Tasks**: Break down the work into actionable, ordered tasks.
5. **Create Claude Code Prompt**: Generate a prompt for AI-assisted development.

## Output Format

Respond with valid JSON containing the following structure:

```json
{{
  "summary": "2-3 sentence summary of the issue and its context",
  "analysis": "Detailed analysis including technical considerations",
  "complexity": "low|medium|high",
  "estimated_effort": "S|M|L|XL",
  "key_considerations": ["list", "of", "important", "points"],
  "suggested_approach": "Recommended implementation approach",
  "potential_blockers": ["possible", "blockers", "or", "risks"],
  "tasks": [
    {{
      "id": "task-1",
      "description": "Task description",
      "dependencies": [],
      "estimated_effort": "S|M|L",
      "order": 1
    }}
  ],
  "claude_code_sections": {{
    "context": "Brief context for Claude Code",
    "code_references": ["list of relevant file paths"],
    "instructions": "Implementation instructions",
    "constraints": "Any constraints or requirements"
  }}
}}
```

## Guidelines

- Be specific and actionable in your recommendations
- Consider edge cases and error handling
- Think about testing requirements
- Account for code quality and maintainability
- Reference existing patterns in the codebase when available
- Keep tasks small enough to be completed in a few hours

{additional_context}"""


AI_CONTEXT_REFINEMENT_PROMPT = """You are continuing a conversation about issue context refinement.

Previous context has been generated for this issue. The user wants to refine or expand on specific aspects.

## Previous Context Summary
{context_summary}

## User's Refinement Request
{refinement_query}

## Instructions

1. Address the user's specific question or concern
2. Provide updated or additional context as needed
3. If modifying tasks, include the complete updated task list
4. Maintain consistency with previous context unless explicitly changing it

Respond naturally to the user's request while providing actionable technical guidance."""


CLAUDE_CODE_PROMPT_TEMPLATE = """## Issue: {identifier} - {title}

## Context
{summary}

## Related Code
{code_references}

## Implementation Tasks
{tasks_checklist}

## Instructions
{instructions}

## Constraints
- Follow existing code patterns and conventions
- Ensure proper error handling and logging
- Add appropriate tests for new functionality
- Document public APIs and complex logic

## Technical Notes
{technical_notes}
"""


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class ParsedAIContext:
    """Parsed AI context from model response."""

    summary: str
    analysis: str
    complexity: str
    estimated_effort: str
    key_considerations: list[str]
    suggested_approach: str
    potential_blockers: list[str]
    tasks: list[dict[str, Any]]
    claude_code_sections: dict[str, Any]
    raw_response: str


# =============================================================================
# Prompt Building Functions
# =============================================================================


def build_context_generation_prompt(
    *,
    issue_title: str,
    issue_description: str | None,
    issue_identifier: str,
    project_name: str | None = None,
    related_issues: list[dict[str, Any]] | None = None,
    related_notes: list[dict[str, Any]] | None = None,
    code_files: list[str] | None = None,
    additional_context: str | None = None,
) -> tuple[str, str]:
    """Build the context generation prompt.

    Args:
        issue_title: Issue title.
        issue_description: Issue description.
        issue_identifier: Issue identifier (e.g., PILOT-123).
        project_name: Project name for context.
        related_issues: List of potentially related issues.
        related_notes: List of potentially related notes.
        code_files: List of relevant code file paths.
        additional_context: Additional context from workspace.

    Returns:
        Tuple of (system_prompt, user_prompt).
    """
    # Build system prompt with additional context
    system_context_parts = []
    if project_name:
        system_context_parts.append(f"Project: {project_name}")
    if additional_context:
        system_context_parts.append(additional_context)

    additional_ctx = "\n".join(system_context_parts) if system_context_parts else ""
    system_prompt = AI_CONTEXT_SYSTEM_PROMPT.format(additional_context=additional_ctx)

    # Build user prompt
    user_parts = [
        f"## Issue: {issue_identifier}\n",
        f"**Title:** {issue_title}\n",
    ]

    if issue_description:
        user_parts.append(f"\n**Description:**\n{issue_description}\n")

    if related_issues:
        user_parts.append("\n## Related Issues (for reference)\n")
        for issue in related_issues[:5]:  # Limit to 5
            identifier = issue.get("identifier", "???")
            title = issue.get("title", "Untitled")
            user_parts.append(f"- {identifier}: {title}\n")

    if related_notes:
        user_parts.append("\n## Related Notes (for reference)\n")
        for note in related_notes[:5]:  # Limit to 5
            title = note.get("title", "Untitled")
            excerpt = note.get("excerpt", "")[:100]
            user_parts.append(f"- {title}: {excerpt}...\n")

    if code_files:
        user_parts.append("\n## Potentially Relevant Files\n")
        for file_path in code_files[:10]:  # Limit to 10
            user_parts.append(f"- {file_path}\n")

    user_parts.append("\nPlease analyze this issue and generate comprehensive context.")

    return system_prompt, "".join(user_parts)


def build_refinement_prompt(
    *,
    context_summary: str,
    refinement_query: str,
    conversation_history: list[dict[str, Any]] | None = None,
) -> tuple[str, list[dict[str, str]]]:
    """Build the refinement conversation prompt.

    Args:
        context_summary: Summary of existing context.
        refinement_query: User's refinement query.
        conversation_history: Previous conversation messages.

    Returns:
        Tuple of (system_prompt, messages_list).
    """
    system_prompt = AI_CONTEXT_REFINEMENT_PROMPT.format(
        context_summary=context_summary,
        refinement_query=refinement_query,
    )

    messages: list[dict[str, str]] = []

    # Add conversation history
    if conversation_history:
        for msg in conversation_history[-10:]:  # Last 10 messages
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant"):
                messages.append({"role": role, "content": content})

    # Add current query
    messages.append({"role": "user", "content": refinement_query})

    return system_prompt, messages


def build_claude_code_prompt(
    *,
    identifier: str,
    title: str,
    summary: str,
    code_references: list[dict[str, Any]] | None = None,
    tasks: list[dict[str, Any]] | None = None,
    instructions: str | None = None,
    technical_notes: str | None = None,
) -> str:
    """Build the Claude Code prompt for developers.

    Args:
        identifier: Issue identifier (e.g., PILOT-123).
        title: Issue title.
        summary: Context summary.
        code_references: List of code file references.
        tasks: Implementation tasks checklist.
        instructions: Implementation instructions.
        technical_notes: Additional technical notes.

    Returns:
        Formatted Claude Code prompt.
    """
    # Format code references
    code_refs_parts = []
    if code_references:
        for ref in code_references:
            file_path = ref.get("file_path", "unknown")
            line_start = ref.get("line_start")
            line_end = ref.get("line_end")
            description = ref.get("description", "")

            if line_start and line_end:
                code_refs_parts.append(f"- `{file_path}` (L{line_start}-{line_end}): {description}")
            else:
                code_refs_parts.append(f"- `{file_path}`: {description}")
    else:
        code_refs_parts.append("No specific code references identified.")

    # Format tasks
    tasks_parts = []
    if tasks:
        for task in sorted(tasks, key=lambda t: t.get("order", 0)):
            task_id = task.get("id", "?")
            description = task.get("description", "")
            effort = task.get("estimated_effort", "M")
            completed = task.get("completed", False)
            checkbox = "[x]" if completed else "[ ]"
            tasks_parts.append(f"- {checkbox} {task_id}: {description} ({effort})")
    else:
        tasks_parts.append("No tasks defined yet.")

    return CLAUDE_CODE_PROMPT_TEMPLATE.format(
        identifier=identifier,
        title=title,
        summary=summary,
        code_references="\n".join(code_refs_parts),
        tasks_checklist="\n".join(tasks_parts),
        instructions=instructions or "Implement the feature as described in the context.",
        technical_notes=technical_notes or "None",
    )


# =============================================================================
# Response Parsing Functions
# =============================================================================


def parse_context_response(response_text: str) -> ParsedAIContext:
    """Parse the AI model response into structured context.

    Args:
        response_text: Raw response from AI model.

    Returns:
        ParsedAIContext with extracted data.
    """
    # Try to extract JSON from response
    try:
        # Look for JSON block (could be in code fence or plain)
        json_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", response_text)
        if json_match:
            data = json.loads(json_match.group(1))
        else:
            # Try to find raw JSON
            json_match = re.search(r"\{[\s\S]*\}", response_text)
            if json_match:
                data = json.loads(json_match.group())
            else:
                logger.warning("No JSON found in AI context response")
                data = {}
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse AI context JSON: {e}")
        data = {}

    # Extract and validate fields with defaults
    return ParsedAIContext(
        summary=data.get("summary", "Unable to generate summary."),
        analysis=data.get("analysis", ""),
        complexity=_validate_complexity(data.get("complexity", "medium")),
        estimated_effort=_validate_effort(data.get("estimated_effort", "M")),
        key_considerations=data.get("key_considerations", []),
        suggested_approach=data.get("suggested_approach", ""),
        potential_blockers=data.get("potential_blockers", []),
        tasks=_normalize_tasks(data.get("tasks", [])),
        claude_code_sections=data.get("claude_code_sections", {}),
        raw_response=response_text,
    )


def _validate_complexity(value: str) -> str:
    """Validate complexity value."""
    valid = {"low", "medium", "high"}
    return value.lower() if value.lower() in valid else "medium"


def _validate_effort(value: str) -> str:
    """Validate effort value."""
    valid = {"S", "M", "L", "XL"}
    return value.upper() if value.upper() in valid else "M"


def _normalize_tasks(tasks: list[Any]) -> list[dict[str, Any]]:
    """Normalize tasks list to ensure consistent structure.

    Args:
        tasks: Raw tasks from response.

    Returns:
        Normalized tasks list.
    """
    normalized = []
    for i, task in enumerate(tasks):
        if not isinstance(task, dict):
            continue

        normalized.append(
            {
                "id": task.get("id", f"task-{i + 1}"),
                "description": task.get("description", ""),
                "completed": task.get("completed", False),
                "dependencies": task.get("dependencies", []),
                "estimated_effort": _validate_effort(task.get("estimated_effort", "M")),
                "order": task.get("order", i + 1),
            }
        )

    return normalized


def extract_refinement_updates(
    response_text: str,
    existing_context: dict[str, Any],
) -> dict[str, Any]:
    """Extract updates from refinement response.

    Args:
        response_text: Refinement response from AI.
        existing_context: Existing context data.

    Returns:
        Dictionary of updates to apply to context.
    """
    updates: dict[str, Any] = {}

    # Try to extract structured updates
    try:
        json_match = re.search(r"\{[\s\S]*\}", response_text)
        if json_match:
            data = json.loads(json_match.group())

            # Check for updated fields
            if "tasks" in data:
                updates["tasks_checklist"] = _normalize_tasks(data["tasks"])
            if "summary" in data:
                updates["summary"] = data["summary"]
            if "analysis" in data:
                updates["analysis"] = data["analysis"]
            if "key_considerations" in data:
                updates["key_considerations"] = data["key_considerations"]
    except json.JSONDecodeError:
        # Response was natural language, no structured updates
        pass

    # Always record the conversation
    updates["last_refined_at"] = datetime.now(tz=UTC).isoformat()

    return updates


__all__ = [
    "AI_CONTEXT_SYSTEM_PROMPT",
    "CLAUDE_CODE_PROMPT_TEMPLATE",
    "ParsedAIContext",
    "build_claude_code_prompt",
    "build_context_generation_prompt",
    "build_refinement_prompt",
    "extract_refinement_updates",
    "parse_context_response",
]
