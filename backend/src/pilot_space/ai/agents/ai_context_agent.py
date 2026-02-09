"""AI Context Agent — delegates to PilotSpaceAgent with ai-context skill.

Replaces the standalone AIContextSubagent (DD-086) by routing context
generation through the centralized PilotSpaceAgent orchestrator, which
has access to 33 MCP tools across 6 servers (notes, issues, projects,
comments, etc.) instead of the 4 inline tools the old subagent had.

Services (GenerateAIContextService, RefineAIContextService) call this
module's AIContextAgent class, which builds an enriched prompt and
delegates to PilotSpaceAgent.execute() or PilotSpaceAgent.stream().

Data classes (AIContextInput, AIContextOutput, RelatedItem, CodeReference)
are the stable interface consumed by the service layer.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pilot_space.ai.agents.agent_base import AgentContext, AgentResult
from pilot_space.ai.prompts.ai_context import (
    build_claude_code_prompt,
    build_context_generation_prompt,
    build_refinement_prompt,
    parse_context_response,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from pilot_space.ai.agents.pilotspace_agent import PilotSpaceAgent
    from pilot_space.ai.infrastructure.cost_tracker import CostTracker
    from pilot_space.ai.infrastructure.resilience import ResilientExecutor
    from pilot_space.ai.providers.provider_selector import ProviderSelector
    from pilot_space.ai.tools.mcp_server import ToolRegistry

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes — stable interface for service layer
# =============================================================================


@dataclass
class RelatedItem:
    """A related issue, note, or page discovered during context search."""

    id: str
    type: str  # "issue" | "note" | "page"
    title: str
    relevance_score: float
    excerpt: str = ""
    identifier: str | None = None
    state: str | None = None


@dataclass
class CodeReference:
    """A code file referenced from linked commits or PRs."""

    file_path: str
    description: str = ""
    line_range: tuple[int, int] | None = None
    relevance: str = "medium"


@dataclass
class AIContextInput:
    """Input for AI context generation or refinement.

    Attributes:
        issue_id: Issue UUID string.
        issue_title: Issue name/title.
        issue_description: Issue description text.
        issue_identifier: Human-readable identifier (e.g. PILOT-42).
        workspace_id: Workspace UUID string.
        project_name: Optional project name for context.
        related_issues: Pre-discovered related issues.
        related_notes: Pre-discovered related notes.
        code_references: Pre-extracted code file references.
        conversation_history: Previous refinement messages.
        refinement_query: User's refinement question (None for initial generation).
        api_key: Anthropic API key (BYOK).
    """

    issue_id: str
    issue_title: str
    issue_description: str | None
    issue_identifier: str
    workspace_id: str
    project_name: str | None = None
    related_issues: list[RelatedItem] = field(default_factory=list)
    related_notes: list[RelatedItem] = field(default_factory=list)
    code_references: list[CodeReference] = field(default_factory=list)
    conversation_history: list[dict[str, Any]] = field(default_factory=list)
    refinement_query: str | None = None
    api_key: str = ""


@dataclass
class AIContextOutput:
    """Structured output from AI context generation.

    Attributes match what GenerateAIContextService persists to the DB.
    """

    summary: str
    analysis: str
    complexity: str
    estimated_effort: str
    tasks_checklist: list[dict[str, Any]]
    related_issues: list[dict[str, Any]]
    related_notes: list[dict[str, Any]]
    related_pages: list[dict[str, Any]] = field(default_factory=list)
    code_references: list[dict[str, Any]] = field(default_factory=list)
    conversation_history: list[dict[str, Any]] = field(default_factory=list)
    claude_code_prompt: str | None = None

    def to_content_dict(self) -> dict[str, Any]:
        """Convert to JSONB content dict for AIContext.content column."""
        return {
            "summary": self.summary,
            "analysis": self.analysis,
            "complexity": self.complexity,
            "estimated_effort": self.estimated_effort,
        }


# =============================================================================
# AIContextAgent — delegates to PilotSpaceAgent
# =============================================================================


class AIContextAgent:
    """AI context generation agent that delegates to PilotSpaceAgent.

    Instead of spawning a separate Claude SDK subprocess with limited tools,
    this routes through the centralized PilotSpaceAgent which has access to
    all MCP tool servers (notes, issues, projects, comments, etc.).

    Usage from service layer (unchanged):
        agent = AIContextAgent(
            pilotspace_agent=pilotspace_agent,
            tool_registry=tool_registry,
            ...
        )
        result = await agent.run(agent_input, agent_context)
    """

    AGENT_NAME = "ai_context_agent"

    def __init__(
        self,
        pilotspace_agent: PilotSpaceAgent,
        tool_registry: ToolRegistry,
        provider_selector: ProviderSelector,
        cost_tracker: CostTracker,
        resilient_executor: ResilientExecutor,
    ) -> None:
        self._agent = pilotspace_agent
        self._tool_registry = tool_registry
        self._provider_selector = provider_selector
        self._cost_tracker = cost_tracker
        self._resilient_executor = resilient_executor

    async def run(
        self,
        input_data: AIContextInput,
        context: AgentContext,
    ) -> AgentResult[AIContextOutput]:
        """Generate or refine AI context via PilotSpaceAgent.

        Args:
            input_data: Issue context + related items.
            context: Workspace/user execution context.

        Returns:
            AgentResult with AIContextOutput on success.
        """
        try:
            prompt = self._build_prompt(input_data)
            chat_output = await self._execute_agent(prompt, input_data, context)
            output = self._parse_response(chat_output.response, input_data)

            return AgentResult.ok(
                output,
                input_tokens=chat_output.metadata.get("input_tokens", 0),
                output_tokens=chat_output.metadata.get("output_tokens", 0),
                cost_usd=chat_output.metadata.get("cost_usd", 0.0),
            )
        except Exception as e:
            logger.exception(
                "AI context generation failed",
                extra={
                    "issue_id": input_data.issue_id,
                    "workspace_id": input_data.workspace_id,
                },
            )
            return AgentResult.fail(str(e))

    async def run_stream(
        self,
        input_data: AIContextInput,
        context: AgentContext,
    ) -> AsyncIterator[str]:
        """Stream AI context refinement via PilotSpaceAgent.

        Args:
            input_data: Issue context with refinement_query.
            context: Workspace/user execution context.

        Yields:
            Text chunks from PilotSpaceAgent streaming response.
        """
        from pilot_space.ai.agents.pilotspace_agent import ChatInput

        prompt = self._build_prompt(input_data)
        chat_input = ChatInput(
            message=prompt,
            session_id=None,
            context={"source": "ai_context_refinement", "issue_id": input_data.issue_id},
            user_id=context.user_id,
            workspace_id=context.workspace_id,
        )

        async for chunk in self._agent.stream(chat_input, context):
            # Extract text content from SSE events
            text = self._extract_text_from_sse(chunk)
            if text:
                yield text

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    def _build_prompt(self, input_data: AIContextInput) -> str:
        """Build prompt from input data using prompt templates."""
        if input_data.refinement_query:
            # Refinement mode: use existing context + query
            context_summary = (
                input_data.conversation_history[-1].get("content", "")
                if input_data.conversation_history
                else ""
            )
            system_prompt, messages = build_refinement_prompt(
                context_summary=context_summary or input_data.issue_title,
                refinement_query=input_data.refinement_query,
                conversation_history=input_data.conversation_history,
            )
            # Combine into single prompt for PilotSpaceAgent
            parts = [f"[System context]: {system_prompt}\n"]
            for msg in messages:
                parts.append(f"[{msg['role']}]: {msg['content']}\n")
            return "".join(parts)

        # Generation mode: build full context prompt
        related_issues_dicts = [
            {
                "identifier": item.identifier or item.id,
                "title": item.title,
                "excerpt": item.excerpt,
            }
            for item in input_data.related_issues
        ]
        related_notes_dicts = [
            {"title": item.title, "excerpt": item.excerpt} for item in input_data.related_notes
        ]
        code_files = [ref.file_path for ref in input_data.code_references]

        _system_prompt, user_prompt = build_context_generation_prompt(
            issue_title=input_data.issue_title,
            issue_description=input_data.issue_description,
            issue_identifier=input_data.issue_identifier,
            project_name=input_data.project_name,
            related_issues=related_issues_dicts,
            related_notes=related_notes_dicts,
            code_files=code_files,
        )

        # Prefix with /ai-context skill invocation for PilotSpaceAgent
        return f"/ai-context\n\n{user_prompt}"

    async def _execute_agent(
        self,
        prompt: str,
        input_data: AIContextInput,
        context: AgentContext,
    ) -> Any:
        """Execute PilotSpaceAgent and collect response."""
        from pilot_space.ai.agents.pilotspace_agent import ChatInput

        chat_input = ChatInput(
            message=prompt,
            session_id=None,
            context={"source": "ai_context_generation", "issue_id": input_data.issue_id},
            user_id=context.user_id,
            workspace_id=context.workspace_id,
        )

        return await self._agent.execute(chat_input, context)

    def _parse_response(
        self,
        response_text: str,
        input_data: AIContextInput,
    ) -> AIContextOutput:
        """Parse PilotSpaceAgent response into structured AIContextOutput."""
        parsed = parse_context_response(response_text)

        # Build Claude Code prompt from parsed data
        claude_code_prompt = build_claude_code_prompt(
            identifier=input_data.issue_identifier,
            title=input_data.issue_title,
            summary=parsed.summary,
            code_references=[
                {"file_path": ref.file_path, "description": ref.description}
                for ref in input_data.code_references
            ],
            tasks=parsed.tasks,
            instructions=parsed.claude_code_sections.get("instructions"),
            technical_notes=parsed.suggested_approach,
        )

        # Serialize related items to dicts for DB storage
        related_issues_dicts = [
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
        ]
        related_notes_dicts = [
            {
                "id": item.id,
                "type": item.type,
                "title": item.title,
                "relevance_score": item.relevance_score,
                "excerpt": item.excerpt,
            }
            for item in input_data.related_notes
        ]
        code_refs_dicts = [
            {
                "file_path": ref.file_path,
                "description": ref.description,
                "relevance": ref.relevance,
                "line_start": ref.line_range[0] if ref.line_range else None,
                "line_end": ref.line_range[1] if ref.line_range else None,
            }
            for ref in input_data.code_references
        ]

        return AIContextOutput(
            summary=parsed.summary,
            analysis=parsed.analysis,
            complexity=parsed.complexity,
            estimated_effort=parsed.estimated_effort,
            tasks_checklist=parsed.tasks,
            related_issues=related_issues_dicts,
            related_notes=related_notes_dicts,
            code_references=code_refs_dicts,
            claude_code_prompt=claude_code_prompt,
            conversation_history=input_data.conversation_history,
        )

    @staticmethod
    def _extract_text_from_sse(chunk: str) -> str | None:
        """Extract text content from an SSE event chunk.

        Handles:
        - 'event: text_delta\\ndata: {"delta": "text"}' → "text"
        - 'data: text' → "text"
        - Everything else → None
        """
        import json as _json

        for line in chunk.strip().split("\n"):
            if line.startswith("data: "):
                data_str = line[6:]
                try:
                    data = _json.loads(data_str)
                    if isinstance(data, dict):
                        return data.get("delta") or data.get("text")
                except (ValueError, TypeError):
                    # Plain text data
                    return data_str
        return None


__all__ = [
    "AIContextAgent",
    "AIContextInput",
    "AIContextOutput",
    "CodeReference",
    "RelatedItem",
]
