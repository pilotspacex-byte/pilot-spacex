"""AI Context Agent for generating structured issue context.

Creates comprehensive AI context for issues including:
- Context summary and complexity assessment
- Claude Code ready-to-use prompt
- Task decomposition checklist
- Related items mapping (issues, notes, pages, code)

Used by GenerateAIContextService and RefineAIContextService.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from anthropic import AsyncAnthropic
from anthropic.types import MessageParam

from pilot_space.ai.agents.agent_base import AgentContext, SDKBaseAgent
from pilot_space.ai.providers.provider_selector import ProviderSelector, TaskType
from pilot_space.ai.sdk.config import MODEL_SONNET

logger = logging.getLogger(__name__)

# Output token limits
MAX_GENERATE_TOKENS = 4096
MAX_REFINE_TOKENS = 2048


@dataclass
class RelatedItem:
    """A related issue, note, or document.

    Attributes:
        id: Item UUID as string.
        type: Item type (issue, note, page).
        title: Item title.
        relevance_score: Similarity score 0-1.
        excerpt: Content preview.
        identifier: Issue identifier (e.g. PS-42).
        state: Issue state name.
    """

    id: str
    type: str
    title: str
    relevance_score: float = 0.5
    excerpt: str = ""
    identifier: str | None = None
    state: str | None = None


@dataclass
class CodeReference:
    """A code file reference linked to the issue.

    Attributes:
        file_path: Path to the source file.
        line_range: Optional (start, end) line numbers.
        description: Context about the reference.
        relevance: Relevance level (high, medium, low).
    """

    file_path: str
    line_range: tuple[int, int] | None = None
    description: str = ""
    relevance: str = "medium"


@dataclass
class AIContextInput:
    """Input for AI context generation or refinement.

    Attributes:
        issue_id: Issue UUID as string.
        issue_title: Issue name.
        issue_description: Issue description text.
        issue_identifier: Issue identifier (e.g. PS-42).
        workspace_id: Workspace UUID as string.
        project_name: Project name if assigned.
        related_issues: Related issues found via search.
        related_notes: Related notes found via search.
        code_references: Code files linked to the issue.
        conversation_history: Prior refinement conversation.
        refinement_query: User's refinement question.
        api_key: Anthropic API key for LLM calls.
    """

    issue_id: str
    issue_title: str
    issue_description: str | None = None
    issue_identifier: str | None = None
    workspace_id: str = ""
    project_name: str | None = None
    related_issues: list[RelatedItem] = field(default_factory=list)
    related_notes: list[RelatedItem] = field(default_factory=list)
    code_references: list[CodeReference] = field(default_factory=list)
    conversation_history: list[dict[str, Any]] = field(default_factory=list)
    refinement_query: str | None = None
    api_key: str = ""


@dataclass
class AIContextOutput:
    """Output from AI context generation.

    Attributes:
        summary: Executive summary of the issue context.
        complexity: Estimated complexity (low, medium, high).
        claude_code_prompt: Ready-to-use prompt for Claude Code.
        tasks_checklist: Decomposed task list with metadata.
        related_issues: Related issues with relevance data.
        related_notes: Related notes with relevance data.
        related_pages: Related documentation pages.
        code_references: Code files with context.
        conversation_history: Updated conversation history.
    """

    summary: str = ""
    complexity: str = "medium"
    claude_code_prompt: str = ""
    tasks_checklist: list[dict[str, Any]] = field(default_factory=list)
    related_issues: list[dict[str, Any]] = field(default_factory=list)
    related_notes: list[dict[str, Any]] = field(default_factory=list)
    related_pages: list[dict[str, Any]] = field(default_factory=list)
    code_references: list[dict[str, Any]] = field(default_factory=list)
    conversation_history: list[dict[str, Any]] = field(default_factory=list)

    def to_content_dict(self) -> dict[str, Any]:
        """Convert to dict for storage in AIContext.content JSON field."""
        return {
            "summary": self.summary,
            "complexity": self.complexity,
            "claude_code_prompt": self.claude_code_prompt,
            "tasks_checklist": self.tasks_checklist,
        }


SYSTEM_PROMPT = """\
You are an AI context generator for a software development platform.
Your task is to analyze an issue and generate structured context that helps
developers understand the issue deeply and start implementation efficiently.

You must respond with valid JSON matching this schema:
{
  "summary": "Executive summary of the issue (2-3 sentences)",
  "complexity": "low" | "medium" | "high",
  "claude_code_prompt": "A ready-to-use prompt for Claude Code that a developer can paste to start implementation",
  "tasks_checklist": [
    {
      "title": "Task title",
      "description": "What needs to be done",
      "estimated_points": 1,
      "dependencies": [],
      "priority": "high" | "medium" | "low"
    }
  ],
  "related_pages": [
    {
      "title": "Page title",
      "url": "URL or path",
      "relevance": "Why this page is relevant"
    }
  ]
}

Guidelines:
- The summary should capture the business context and technical requirements.
- Complexity assessment should consider scope, dependencies, and risk.
- The Claude Code prompt should be specific, actionable, and include file paths where possible.
- Tasks should follow Fibonacci estimation (1, 2, 3, 5, 8).
- Include dependency relationships between tasks.
- Keep the response focused and actionable.
"""

REFINEMENT_SYSTEM_PROMPT = """\
You are refining an existing AI context for a software development issue.
The user is asking follow-up questions or requesting modifications to the context.
Respond naturally to the user's query while maintaining awareness of the full issue context.
Be concise and actionable.
"""


class AIContextAgent(SDKBaseAgent["AIContextInput", "AIContextOutput"]):
    """Agent for generating structured AI context for issues.

    Extends SDKBaseAgent with direct Anthropic API calls.
    Supports both generation (run) and streaming refinement (run_stream).
    """

    AGENT_NAME = "ai_context_agent"
    DEFAULT_MODEL = MODEL_SONNET  # Fallback only; select_model() prefers routing table

    @staticmethod
    def _select_model() -> str:
        """Select model via ProviderSelector (DD-011: AI_CONTEXT -> Opus)."""
        try:
            selector = ProviderSelector()
            _provider, model = selector.select(TaskType.AI_CONTEXT)
            return model
        except Exception:
            logger.warning(
                "ProviderSelector failed for AI_CONTEXT, falling back to %s",
                MODEL_SONNET,
            )
            return MODEL_SONNET

    def _build_issue_context(self, input_data: AIContextInput) -> str:
        """Build issue context string for the LLM prompt."""
        parts = [f"## Issue: {input_data.issue_title}"]

        if input_data.issue_identifier:
            parts.append(f"Identifier: {input_data.issue_identifier}")

        if input_data.issue_description:
            parts.append(f"\n### Description\n{input_data.issue_description}")

        if input_data.project_name:
            parts.append(f"\nProject: {input_data.project_name}")

        if input_data.related_issues:
            parts.append("\n### Related Issues")
            for item in input_data.related_issues[:10]:
                ident = f" ({item.identifier})" if item.identifier else ""
                state = f" [{item.state}]" if item.state else ""
                parts.append(f"- {item.title}{ident}{state}")
                if item.excerpt:
                    parts.append(f"  {item.excerpt[:150]}")

        if input_data.related_notes:
            parts.append("\n### Related Notes")
            for item in input_data.related_notes[:10]:
                parts.append(f"- {item.title}")
                if item.excerpt:
                    parts.append(f"  {item.excerpt[:150]}")

        if input_data.code_references:
            parts.append("\n### Code References")
            for ref in input_data.code_references[:10]:
                line_info = ""
                if ref.line_range:
                    line_info = f" (L{ref.line_range[0]}-{ref.line_range[1]})"
                parts.append(f"- `{ref.file_path}`{line_info}")
                if ref.description:
                    parts.append(f"  {ref.description}")

        return "\n".join(parts)

    def _parse_llm_response(
        self, response_text: str, input_data: AIContextInput
    ) -> AIContextOutput:
        """Parse LLM JSON response into AIContextOutput."""
        # Extract JSON from response (handle markdown code blocks)
        json_text = response_text.strip()
        if json_text.startswith("```"):
            # Remove markdown code fence
            lines = json_text.split("\n")
            # Skip first line (```json) and last line (```)
            json_lines = []
            in_block = False
            for line in lines:
                if line.strip().startswith("```") and not in_block:
                    in_block = True
                    continue
                if line.strip() == "```" and in_block:
                    break
                if in_block:
                    json_lines.append(line)
            json_text = "\n".join(json_lines)

        try:
            data = json.loads(json_text)
        except json.JSONDecodeError:
            logger.warning(
                "Failed to parse LLM response as JSON, using raw text as summary",
                extra={"response_preview": response_text[:200]},
            )
            return AIContextOutput(
                summary=response_text[:500],
                complexity="medium",
                claude_code_prompt=f"Implement: {input_data.issue_title}",
                related_issues=[
                    {
                        "id": item.id,
                        "type": item.type,
                        "title": item.title,
                        "relevance_score": item.relevance_score,
                        "excerpt": item.excerpt,
                        "identifier": item.identifier,
                        "state": item.state,
                    }
                    for item in input_data.related_issues
                ],
                related_notes=[
                    {
                        "id": item.id,
                        "type": item.type,
                        "title": item.title,
                        "relevance_score": item.relevance_score,
                        "excerpt": item.excerpt,
                    }
                    for item in input_data.related_notes
                ],
                code_references=[
                    {
                        "file_path": ref.file_path,
                        "description": ref.description,
                        "relevance": ref.relevance,
                    }
                    for ref in input_data.code_references
                ],
            )

        return AIContextOutput(
            summary=data.get("summary", ""),
            complexity=data.get("complexity", "medium"),
            claude_code_prompt=data.get("claude_code_prompt", ""),
            tasks_checklist=data.get("tasks_checklist", []),
            related_issues=[
                {
                    "id": item.id,
                    "type": item.type,
                    "title": item.title,
                    "relevance_score": item.relevance_score,
                    "excerpt": item.excerpt,
                    "identifier": item.identifier,
                    "state": item.state,
                }
                for item in input_data.related_issues
            ],
            related_notes=[
                {
                    "id": item.id,
                    "type": item.type,
                    "title": item.title,
                    "relevance_score": item.relevance_score,
                    "excerpt": item.excerpt,
                }
                for item in input_data.related_notes
            ],
            related_pages=data.get("related_pages", []),
            code_references=[
                {
                    "file_path": ref.file_path,
                    "description": ref.description,
                    "relevance": ref.relevance,
                    **(
                        {"line_start": ref.line_range[0], "line_end": ref.line_range[1]}
                        if ref.line_range
                        else {}
                    ),
                }
                for ref in input_data.code_references
            ],
        )

    async def execute(
        self,
        input_data: AIContextInput,
        context: AgentContext,
    ) -> AIContextOutput:
        """Generate AI context for an issue.

        Args:
            input_data: Issue data and related items.
            context: Agent execution context.

        Returns:
            AIContextOutput with structured context.
        """
        issue_context = self._build_issue_context(input_data)

        # Determine if this is a refinement or initial generation
        if input_data.refinement_query and input_data.conversation_history:
            return await self._execute_refinement(input_data, context, issue_context)

        return await self._execute_generation(input_data, context, issue_context)

    async def _execute_generation(
        self,
        input_data: AIContextInput,
        context: AgentContext,
        issue_context: str,
    ) -> AIContextOutput:
        """Execute initial context generation."""
        client = AsyncAnthropic(api_key=input_data.api_key)

        user_message = (
            f"Generate comprehensive AI context for the following issue:\n\n"
            f"{issue_context}\n\n"
            f"Respond with JSON only."
        )

        response = await client.messages.create(
            model=self._select_model(),
            max_tokens=MAX_GENERATE_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        # Track usage
        input_tokens = response.usage.input_tokens if response.usage else 0
        output_tokens = response.usage.output_tokens if response.usage else 0

        await self.track_usage(context, input_tokens, output_tokens)

        # Extract text response
        response_text = ""
        for block in response.content:
            if block.type == "text":
                response_text = block.text
                break

        return self._parse_llm_response(response_text, input_data)

    async def _execute_refinement(
        self,
        input_data: AIContextInput,
        context: AgentContext,
        issue_context: str,
    ) -> AIContextOutput:
        """Execute context refinement with conversation history."""
        client = AsyncAnthropic(api_key=input_data.api_key)

        # Build messages from conversation history
        messages: list[MessageParam] = []

        # Add initial context as first user message
        messages.append(
            {
                "role": "user",
                "content": f"Here is the issue context:\n\n{issue_context}",
            }
        )
        messages.append(
            {
                "role": "assistant",
                "content": "I understand the issue context. How can I help refine it?",
            }
        )

        # Add conversation history
        for msg in input_data.conversation_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

        # Add refinement query
        if input_data.refinement_query:
            messages.append(
                {
                    "role": "user",
                    "content": input_data.refinement_query,
                }
            )

        response = await client.messages.create(
            model=self._select_model(),
            max_tokens=MAX_REFINE_TOKENS,
            system=REFINEMENT_SYSTEM_PROMPT,
            messages=messages,
        )

        # Track usage
        input_tokens = response.usage.input_tokens if response.usage else 0
        output_tokens = response.usage.output_tokens if response.usage else 0

        await self.track_usage(context, input_tokens, output_tokens)

        # Extract response text
        response_text = ""
        for block in response.content:
            if block.type == "text":
                response_text = block.text
                break

        # Build updated conversation history
        updated_history = list(input_data.conversation_history)
        if input_data.refinement_query:
            updated_history.append(
                {
                    "role": "user",
                    "content": input_data.refinement_query,
                }
            )
        updated_history.append(
            {
                "role": "assistant",
                "content": response_text,
            }
        )

        # Return output with preserved related items and updated history
        return AIContextOutput(
            summary=response_text[:500],
            complexity="medium",
            related_issues=[
                {
                    "id": item.id,
                    "type": item.type,
                    "title": item.title,
                    "relevance_score": item.relevance_score,
                    "excerpt": item.excerpt,
                    "identifier": item.identifier,
                    "state": item.state,
                }
                for item in input_data.related_issues
            ],
            related_notes=[
                {
                    "id": item.id,
                    "type": item.type,
                    "title": item.title,
                    "relevance_score": item.relevance_score,
                    "excerpt": item.excerpt,
                }
                for item in input_data.related_notes
            ],
            code_references=[
                {
                    "file_path": ref.file_path,
                    "description": ref.description,
                    "relevance": ref.relevance,
                }
                for ref in input_data.code_references
            ],
            conversation_history=updated_history,
        )

    async def run_stream(
        self,
        input_data: AIContextInput,
        context: AgentContext,
    ) -> AsyncIterator[str]:
        """Stream refinement response for SSE.

        Args:
            input_data: Issue data with refinement query.
            context: Agent execution context.

        Yields:
            Response text chunks.
        """
        issue_context = self._build_issue_context(input_data)
        client = AsyncAnthropic(api_key=input_data.api_key)

        # Build messages
        messages: list[MessageParam] = []

        messages.append(
            {
                "role": "user",
                "content": f"Here is the issue context:\n\n{issue_context}",
            }
        )
        messages.append(
            {
                "role": "assistant",
                "content": "I understand the issue context. How can I help refine it?",
            }
        )

        for msg in input_data.conversation_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

        if input_data.refinement_query:
            messages.append(
                {
                    "role": "user",
                    "content": input_data.refinement_query,
                }
            )

        async with client.messages.stream(
            model=self._select_model(),
            max_tokens=MAX_REFINE_TOKENS,
            system=REFINEMENT_SYSTEM_PROMPT,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text

            # Track usage after stream completes
            final_message = await stream.get_final_message()
            if final_message and final_message.usage:
                await self.track_usage(
                    context,
                    final_message.usage.input_tokens,
                    final_message.usage.output_tokens,
                )
