"""AI Context Agent — uses Claude Agent SDK query() for tool-free generation.

Uses claude_agent_sdk.query() for initial context generation (one-shot,
no tools, JSON output) and PilotSpaceAgent.stream() for multi-turn
refinement conversations.

Services (GenerateAIContextService, RefineAIContextService) call this
module's AIContextAgent class, which builds an enriched prompt and
delegates accordingly.

Data classes (AIContextInput, AIContextOutput, RelatedItem, CodeReference)
are the stable interface consumed by the service layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pilot_space.ai.agents.agent_base import AgentContext, AgentResult
from pilot_space.ai.prompts.ai_context import (
    build_claude_code_prompt,
    build_context_generation_prompt,
    build_refinement_prompt,
    parse_context_response,
)
from pilot_space.ai.sdk.config import build_sdk_env
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from pilot_space.ai.agents.pilotspace_agent import PilotSpaceAgent
    from pilot_space.ai.infrastructure.cost_tracker import CostTracker
    from pilot_space.ai.infrastructure.resilience import ResilientExecutor
    from pilot_space.ai.providers.provider_selector import ProviderSelector
    from pilot_space.ai.tools.mcp_server import ToolRegistry

logger = get_logger(__name__)


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
# AIContextAgent — SDK query() for generation, PilotSpaceAgent for refinement
# =============================================================================


class AIContextAgent:
    """AI context generation agent.

    Uses claude_agent_sdk.query() for initial generation (one-shot, tool-free)
    and PilotSpaceAgent.stream() for multi-turn refinement conversations.

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
        """Generate or refine AI context.

        Args:
            input_data: Issue context + related items.
            context: Workspace/user execution context.

        Returns:
            AgentResult with AIContextOutput on success.
        """
        try:
            system_prompt, user_prompt = self._build_prompts(input_data)
            response_text = await self._execute_query(
                system_prompt,
                user_prompt,
                context,
            )
            output = self._parse_response(response_text, input_data)

            return AgentResult.ok(output)
        except Exception as e:
            logger.exception(
                "ai_context_generation_failed",
                issue_id=input_data.issue_id,
                workspace_id=input_data.workspace_id,
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

        _, user_prompt = self._build_prompts(input_data)
        chat_input = ChatInput(
            message=user_prompt,
            session_id=None,
            context={"source": "ai_context_refinement", "issue_id": input_data.issue_id},
            user_id=context.user_id,
            workspace_id=context.workspace_id,
        )

        async for chunk in self._agent.stream(chat_input, context):
            text = self._extract_text_from_sse(chunk)
            if text:
                yield text

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    def _build_prompts(self, input_data: AIContextInput) -> tuple[str, str]:
        """Build system and user prompts from input data.

        Returns:
            Tuple of (system_prompt, user_prompt).
        """
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
            # Combine messages into single user prompt
            parts = []
            for msg in messages:
                parts.append(f"[{msg['role']}]: {msg['content']}")
            return system_prompt, "\n".join(parts)

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

        system_prompt, user_prompt = build_context_generation_prompt(
            issue_title=input_data.issue_title,
            issue_description=input_data.issue_description,
            issue_identifier=input_data.issue_identifier,
            project_name=input_data.project_name,
            related_issues=related_issues_dicts,
            related_notes=related_notes_dicts,
            code_files=code_files,
        )

        return system_prompt, user_prompt

    async def _get_api_key(self, context: AgentContext) -> str:
        """Get API key from PilotSpaceAgent (BYOK vault + env fallback)."""
        return await self._agent._get_api_key(context.workspace_id)  # type: ignore[no-any-return]  # noqa: SLF001

    async def _execute_query(
        self,
        system_prompt: str,
        user_prompt: str,
        context: AgentContext,
    ) -> str:
        """Execute one-shot query via claude_agent_sdk.query().

        Uses SDK query() with no allowed_tools and max_turns=1 to get a clean
        JSON response without tool-calling interference.
        """
        import claude_agent_sdk

        from pilot_space.ai.sdk.sandbox_config import ModelTier

        model_tier = ModelTier.SONNET
        api_key = await self._get_api_key(context)

        stderr_lines: list[str] = []

        def _capture_stderr(line: str) -> None:
            stderr_lines.append(line)
            logger.debug("[AIContext] CLI stderr: %s", line.rstrip())

        options = claude_agent_sdk.ClaudeAgentOptions(
            model=model_tier.model_id,
            system_prompt=system_prompt,
            allowed_tools=[],
            disallowed_tools=[
                "Bash",
                "Read",
                "Write",
                "Edit",
                "Glob",
                "Grep",
                "WebFetch",
                "WebSearch",
                "Task",
                "NotebookEdit",
            ],
            max_turns=1,
            permission_mode="bypassPermissions",
            cwd="/tmp",
            setting_sources=[],
            stderr=_capture_stderr,
            extra_args={"debug-to-stderr": None},
            env=build_sdk_env(api_key),
        )

        text_parts: list[str] = []
        try:
            async for message in claude_agent_sdk.query(
                prompt=user_prompt,
                options=options,
            ):
                # Extract text from AssistantMessage content blocks
                if isinstance(message, claude_agent_sdk.AssistantMessage):
                    for block in message.content:
                        if isinstance(block, claude_agent_sdk.TextBlock):
                            text_parts.append(block.text)
                # ResultMessage has cost/usage info
                elif isinstance(message, claude_agent_sdk.ResultMessage):
                    cost = message.total_cost_usd or 0.0
                    logger.info(
                        "[AIContext] query() result: cost=$%.4f, turns=%s",
                        cost,
                        message.num_turns,
                    )
                    # Track cost to database (non-fatal)
                    if self._cost_tracker:
                        from pilot_space.ai.infrastructure.cost_tracker import (
                            extract_response_usage,
                        )

                        input_tokens, output_tokens = extract_response_usage(message)
                        if input_tokens or output_tokens:
                            try:
                                await self._cost_tracker.track(
                                    workspace_id=context.workspace_id,
                                    user_id=context.user_id,
                                    agent_name=self.AGENT_NAME,
                                    provider="anthropic",
                                    model=model_tier.model_id,
                                    input_tokens=input_tokens,
                                    output_tokens=output_tokens,
                                    operation_type="ai_context",
                                )
                            except Exception:
                                logger.warning(
                                    "ai_context_cost_tracking_failed",
                                    workspace_id=str(context.workspace_id),
                                )
        except Exception:
            logger.exception(
                "[AIContext] SDK query() failed. stderr=%s",
                "\n".join(stderr_lines),
            )
            raise

        full_response = "".join(text_parts)
        logger.info(
            "[AIContext] query() finished: response_len=%d, preview=%.200s",
            len(full_response),
            full_response[:200],
        )

        if not full_response:
            logger.warning("[AIContext] Empty response from SDK query()")

        return full_response

    def _parse_response(
        self,
        response_text: str,
        input_data: AIContextInput,
    ) -> AIContextOutput:
        """Parse response into structured AIContextOutput."""
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

        A single chunk may contain MULTIPLE concatenated SSE events
        (e.g. content_block_start + text_delta from DeltaBuffer flush).
        Split by double-newline first, then collect ALL text deltas.

        Handles:
        - 'event: text_delta\\ndata: {"delta": "text"}' → "text"
        - 'data: text' → "text"
        - Multiple events in one chunk → concatenated text
        - Everything else → None
        """
        import json as _json

        text_parts: list[str] = []

        # Split by double-newline to separate individual SSE events
        events = chunk.strip().split("\n\n")

        for event_block in events:
            event_type: str | None = None
            data_str: str | None = None

            for line in event_block.strip().split("\n"):
                if line.startswith("event: "):
                    event_type = line[7:].strip()
                elif line.startswith("data: "):
                    data_str = line[6:]

            if data_str is None:
                continue

            # Only extract text from text_delta events or bare data lines
            is_text_event = event_type == "text_delta" or event_type is None

            if not is_text_event:
                continue

            try:
                data = _json.loads(data_str)
                if isinstance(data, dict):
                    delta = data.get("delta") or data.get("text")
                    if delta:
                        text_parts.append(delta)
            except (ValueError, TypeError):
                # Plain text data line (not JSON)
                text_parts.append(data_str)

        return "".join(text_parts) if text_parts else None


__all__ = [
    "AIContextAgent",
    "AIContextInput",
    "AIContextOutput",
    "CodeReference",
    "RelatedItem",
]
