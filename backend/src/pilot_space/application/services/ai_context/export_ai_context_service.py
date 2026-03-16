"""Export AI Context service.

T208: Create ExportAIContextService for context export.

Handles:
- Exporting context as markdown
- Exporting context as JSON
- Including Claude Code prompt
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.repositories import (
        AIContextRepository,
        IssueRepository,
    )

logger = get_logger(__name__)


class ExportFormat(StrEnum):
    """Export format options."""

    MARKDOWN = "markdown"
    JSON = "json"
    IMPLEMENTATION_PLAN = "implementation_plan"


@dataclass
class ExportAIContextPayload:
    """Payload for exporting AI context.

    Attributes:
        workspace_id: Workspace UUID.
        issue_id: Issue UUID.
        user_id: User requesting export.
        format: Export format (markdown or json).
        include_conversation: Include conversation history.
    """

    workspace_id: UUID
    issue_id: UUID
    user_id: UUID
    format: ExportFormat = ExportFormat.MARKDOWN
    include_conversation: bool = False


@dataclass
class ExportAIContextResult:
    """Result from AI context export.

    Attributes:
        content: Exported content string.
        format: Export format used.
        filename: Suggested filename.
        content_type: MIME type for the content.
    """

    content: str
    format: ExportFormat
    filename: str
    content_type: str


class ExportAIContextService:
    """Service for exporting AI context.

    Handles:
    - Markdown export for documentation
    - JSON export for integration
    - Claude Code prompt formatting
    """

    def __init__(
        self,
        session: AsyncSession,
        ai_context_repository: AIContextRepository,
        issue_repository: IssueRepository,
    ) -> None:
        """Initialize service.

        Args:
            session: Async database session.
            ai_context_repository: AIContext repository.
            issue_repository: Issue repository.
        """
        self._session = session
        self._context_repo = ai_context_repository
        self._issue_repo = issue_repository

    async def execute(
        self,
        payload: ExportAIContextPayload,
    ) -> ExportAIContextResult:
        """Export AI context.

        Args:
            payload: Export parameters.

        Returns:
            ExportAIContextResult with exported content.

        Raises:
            ValueError: If context or issue not found.
        """
        logger.info(
            "Exporting AI context",
            extra={
                "issue_id": str(payload.issue_id),
                "format": payload.format.value,
            },
        )

        # Get context
        context = await self._context_repo.get_by_issue_id(payload.issue_id)
        if not context:
            raise ValueError(f"AI context not found for issue: {payload.issue_id}")

        # Get issue
        issue = await self._issue_repo.get_by_id_with_relations(payload.issue_id)
        if not issue:
            raise ValueError(f"Issue not found: {payload.issue_id}")

        # Export based on format
        if payload.format == ExportFormat.MARKDOWN:
            content = self._export_markdown(
                issue=issue,
                context=context,
                include_conversation=payload.include_conversation,
            )
            filename = f"{issue.identifier}-context.md"
            content_type = "text/markdown"
        elif payload.format == ExportFormat.IMPLEMENTATION_PLAN:
            context_content = getattr(context, "content", {}) or {}
            plan = context_content.get("implementation_plan", "")
            if not plan:
                raise ValueError(
                    "No implementation plan found. Generate an implementation plan first."
                )
            content = plan
            filename = f"{issue.identifier}-plan.md"
            content_type = "text/markdown"
        else:
            content = self._export_json(
                issue=issue,
                context=context,
                include_conversation=payload.include_conversation,
            )
            filename = f"{issue.identifier}-context.json"
            content_type = "application/json"

        return ExportAIContextResult(
            content=content,
            format=payload.format,
            filename=filename,
            content_type=content_type,
        )

    def _export_markdown(
        self,
        issue: object,
        context: object,
        include_conversation: bool,
    ) -> str:
        """Export context as markdown.

        Args:
            issue: Issue model instance.
            context: AIContext model instance.
            include_conversation: Include conversation history.

        Returns:
            Markdown string.
        """
        # Access issue attributes safely
        identifier = getattr(issue, "identifier", "UNKNOWN")
        name = getattr(issue, "name", "Untitled")
        description = getattr(issue, "description", "")
        project = getattr(issue, "project", None)
        project_name = project.name if project else "Unknown Project"

        # Access context attributes
        content = getattr(context, "content", {}) or {}
        summary = content.get("summary", "No summary available.")
        analysis = content.get("analysis", "")
        complexity = content.get("complexity", "medium")
        estimated_effort = content.get("estimated_effort", "M")
        key_considerations = content.get("key_considerations", [])
        suggested_approach = content.get("suggested_approach", "")
        potential_blockers = content.get("potential_blockers", [])

        tasks_checklist = getattr(context, "tasks_checklist", []) or []
        code_references = getattr(context, "code_references", []) or []
        related_issues = getattr(context, "related_issues", []) or []
        related_notes = getattr(context, "related_notes", []) or []
        claude_code_prompt = getattr(context, "claude_code_prompt", "")
        conversation_history = getattr(context, "conversation_history", []) or []
        generated_at = getattr(context, "generated_at", None)

        parts = [
            f"# {identifier}: {name}\n",
            f"**Project:** {project_name}\n",
            f"**Complexity:** {complexity}\n",
            f"**Estimated Effort:** {estimated_effort}\n",
        ]

        if generated_at:
            parts.append(f"**Generated:** {generated_at.isoformat()}\n")

        parts.append("\n## Summary\n\n")
        parts.append(f"{summary}\n")

        if description:
            parts.append("\n## Description\n\n")
            parts.append(f"{description}\n")

        if analysis:
            parts.append("\n## Analysis\n\n")
            parts.append(f"{analysis}\n")

        if key_considerations:
            parts.append("\n## Key Considerations\n\n")
            for consideration in key_considerations:
                parts.append(f"- {consideration}\n")

        if suggested_approach:
            parts.append("\n## Suggested Approach\n\n")
            parts.append(f"{suggested_approach}\n")

        if potential_blockers:
            parts.append("\n## Potential Blockers\n\n")
            for blocker in potential_blockers:
                parts.append(f"- {blocker}\n")

        if tasks_checklist:
            parts.append("\n## Implementation Tasks\n\n")
            for task in sorted(tasks_checklist, key=lambda t: t.get("order", 0)):
                task_id = task.get("id", "?")
                desc = task.get("description", "")
                effort = task.get("estimated_effort", "M")
                completed = task.get("completed", False)
                checkbox = "[x]" if completed else "[ ]"
                parts.append(f"- {checkbox} **{task_id}:** {desc} ({effort})\n")

        if code_references:
            parts.append("\n## Related Code\n\n")
            for ref in code_references:
                file_path = ref.get("file_path", "")
                desc = ref.get("description", "")
                line_start = ref.get("line_start")
                line_end = ref.get("line_end")

                if line_start and line_end:
                    parts.append(f"- `{file_path}` (L{line_start}-{line_end}): {desc}\n")
                else:
                    parts.append(f"- `{file_path}`: {desc}\n")

        if related_issues:
            parts.append("\n## Related Issues\n\n")
            for item in related_issues:
                title = item.get("title", "Untitled")
                item_id = item.get("identifier", item.get("id", "?"))
                score = item.get("relevance_score", 0)
                parts.append(f"- **{item_id}:** {title} (relevance: {score:.0%})\n")

        if related_notes:
            parts.append("\n## Related Notes\n\n")
            for item in related_notes:
                title = item.get("title", "Untitled")
                excerpt = item.get("excerpt", "")[:100]
                parts.append(f"- **{title}:** {excerpt}...\n")

        if claude_code_prompt:
            parts.append("\n---\n\n## Claude Code Prompt\n\n")
            parts.append("```markdown\n")
            parts.append(claude_code_prompt)
            parts.append("\n```\n")

        if include_conversation and conversation_history:
            parts.append("\n---\n\n## Conversation History\n\n")
            for msg in conversation_history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                timestamp = msg.get("timestamp", "")
                parts.append(f"### {role.capitalize()} ({timestamp})\n\n")
                parts.append(f"{content}\n\n")

        return "".join(parts)

    def _export_json(
        self,
        issue: object,
        context: object,
        include_conversation: bool,
    ) -> str:
        """Export context as JSON.

        Args:
            issue: Issue model instance.
            context: AIContext model instance.
            include_conversation: Include conversation history.

        Returns:
            JSON string.
        """
        # Access issue attributes
        identifier = getattr(issue, "identifier", "UNKNOWN")
        name = getattr(issue, "name", "Untitled")
        description = getattr(issue, "description", "")
        project = getattr(issue, "project", None)
        project_name = project.name if project else "Unknown Project"

        # Access context attributes
        content = getattr(context, "content", {}) or {}
        tasks_checklist = getattr(context, "tasks_checklist", []) or []
        code_references = getattr(context, "code_references", []) or []
        related_issues = getattr(context, "related_issues", []) or []
        related_notes = getattr(context, "related_notes", []) or []
        related_pages = getattr(context, "related_pages", []) or []
        claude_code_prompt = getattr(context, "claude_code_prompt", "")
        conversation_history = getattr(context, "conversation_history", []) or []
        generated_at = getattr(context, "generated_at", None)
        version = getattr(context, "version", 1)

        data = {
            "issue": {
                "identifier": identifier,
                "title": name,
                "description": description,
                "project": project_name,
            },
            "context": {
                "summary": content.get("summary", ""),
                "analysis": content.get("analysis", ""),
                "complexity": content.get("complexity", "medium"),
                "estimated_effort": content.get("estimated_effort", "M"),
                "key_considerations": content.get("key_considerations", []),
                "suggested_approach": content.get("suggested_approach", ""),
                "potential_blockers": content.get("potential_blockers", []),
            },
            "tasks": tasks_checklist,
            "code_references": code_references,
            "related": {
                "issues": related_issues,
                "notes": related_notes,
                "pages": related_pages,
            },
            "claude_code_prompt": claude_code_prompt,
            "metadata": {
                "generated_at": generated_at.isoformat() if generated_at else None,
                "version": version,
            },
        }

        if include_conversation:
            data["conversation_history"] = conversation_history

        return json.dumps(data, indent=2, default=str)


__all__ = [
    "ExportAIContextPayload",
    "ExportAIContextResult",
    "ExportAIContextService",
    "ExportFormat",
]
