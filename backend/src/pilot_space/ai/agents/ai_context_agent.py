"""AI Context Agent for generating comprehensive issue context.

T203: Create AIContextAgent using Claude Opus 4.5.

Provides:
- Context aggregation from related items via embeddings
- Code reference extraction from linked commits/PRs
- Task checklist generation
- Claude Code prompt generation
- Multi-turn conversation for refinement
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import anthropic

from pilot_space.ai.agents.base import (
    AgentContext,
    AgentResult,
    BaseAgent,
    Provider,
    TaskType,
)
from pilot_space.ai.exceptions import AIConfigurationError, RateLimitError
from pilot_space.ai.prompts.ai_context import (
    build_claude_code_prompt,
    build_context_generation_prompt,
    build_refinement_prompt,
    extract_refinement_updates,
    parse_context_response,
)
from pilot_space.ai.telemetry import AIOperation
from pilot_space.ai.utils.retry import RetryConfig

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class RelatedItem:
    """A related item (issue, note, or page).

    Attributes:
        id: Item UUID.
        type: Item type (issue, note, page).
        title: Item title.
        relevance_score: Similarity score (0-1).
        excerpt: Brief excerpt or description.
        identifier: Optional identifier (e.g., PILOT-123).
        state: Optional state for issues.
    """

    id: str
    type: str
    title: str
    relevance_score: float
    excerpt: str
    identifier: str | None = None
    state: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "relevance_score": self.relevance_score,
            "excerpt": self.excerpt,
            "identifier": self.identifier,
            "state": self.state,
        }


@dataclass
class CodeReference:
    """A code file reference.

    Attributes:
        file_path: Path to the file.
        line_range: Tuple of (start, end) line numbers.
        description: Description of the code.
        relevance: Relevance level (high, medium, low).
    """

    file_path: str
    line_range: tuple[int, int] | None = None
    description: str = ""
    relevance: str = "medium"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "file_path": self.file_path,
            "line_start": self.line_range[0] if self.line_range else None,
            "line_end": self.line_range[1] if self.line_range else None,
            "description": self.description,
            "relevance": self.relevance,
        }


@dataclass
class TaskItem:
    """An implementation task.

    Attributes:
        id: Task identifier.
        description: Task description.
        completed: Whether task is completed.
        dependencies: List of dependent task IDs.
        estimated_effort: Effort estimate (S, M, L, XL).
        order: Sort order.
    """

    id: str
    description: str
    completed: bool = False
    dependencies: list[str] = field(default_factory=list)
    estimated_effort: str = "M"
    order: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "description": self.description,
            "completed": self.completed,
            "dependencies": self.dependencies,
            "estimated_effort": self.estimated_effort,
            "order": self.order,
        }


@dataclass
class AIContextInput:
    """Input for AI context generation.

    Attributes:
        issue_id: Issue UUID.
        issue_title: Issue title.
        issue_description: Issue description.
        issue_identifier: Issue identifier (e.g., PILOT-123).
        workspace_id: Workspace UUID.
        project_name: Project name for context.
        related_issues: Pre-fetched related issues.
        related_notes: Pre-fetched related notes.
        related_pages: Pre-fetched related pages.
        code_references: Pre-fetched code references.
        conversation_history: Existing conversation history.
        refinement_query: Optional refinement query for multi-turn.
    """

    issue_id: str
    issue_title: str
    issue_description: str | None
    issue_identifier: str
    workspace_id: str
    project_name: str | None = None
    related_issues: list[RelatedItem] = field(default_factory=list)
    related_notes: list[RelatedItem] = field(default_factory=list)
    related_pages: list[RelatedItem] = field(default_factory=list)
    code_references: list[CodeReference] = field(default_factory=list)
    conversation_history: list[dict[str, Any]] = field(default_factory=list)
    refinement_query: str | None = None


@dataclass
class AIContextOutput:
    """Output from AI context generation.

    Attributes:
        summary: AI-generated summary.
        analysis: Detailed analysis.
        complexity: Complexity level (low, medium, high).
        estimated_effort: Effort estimate (S, M, L, XL).
        key_considerations: List of key considerations.
        suggested_approach: Suggested implementation approach.
        potential_blockers: Potential blockers or risks.
        related_issues: Related issues with relevance.
        related_notes: Related notes with relevance.
        related_pages: Related pages with relevance.
        code_references: Code file references.
        tasks_checklist: Implementation tasks.
        claude_code_prompt: Generated Claude Code prompt.
        conversation_history: Updated conversation history.
        version: Context version number.
    """

    summary: str
    analysis: str = ""
    complexity: str = "medium"
    estimated_effort: str = "M"
    key_considerations: list[str] = field(default_factory=list)
    suggested_approach: str = ""
    potential_blockers: list[str] = field(default_factory=list)
    related_issues: list[dict[str, Any]] = field(default_factory=list)
    related_notes: list[dict[str, Any]] = field(default_factory=list)
    related_pages: list[dict[str, Any]] = field(default_factory=list)
    code_references: list[dict[str, Any]] = field(default_factory=list)
    tasks_checklist: list[dict[str, Any]] = field(default_factory=list)
    claude_code_prompt: str = ""
    conversation_history: list[dict[str, Any]] = field(default_factory=list)
    version: int = 1

    def to_content_dict(self) -> dict[str, Any]:
        """Convert to content dictionary for storage."""
        return {
            "summary": self.summary,
            "analysis": self.analysis,
            "complexity": self.complexity,
            "estimated_effort": self.estimated_effort,
            "key_considerations": self.key_considerations,
            "suggested_approach": self.suggested_approach,
            "potential_blockers": self.potential_blockers,
            "model_used": "claude-opus-4-5-20251101",
            "generation_timestamp": datetime.now(tz=UTC).isoformat(),
        }


# =============================================================================
# Agent Implementation
# =============================================================================


class AIContextAgent(BaseAgent[AIContextInput, AIContextOutput]):
    """Agent for generating comprehensive issue context.

    Uses Claude Opus 4.5 for deep understanding and multi-turn refinement.

    Features:
    - Context aggregation from related items
    - Code reference analysis
    - Task checklist generation
    - Claude Code prompt formatting
    - Multi-turn conversation support

    Attributes:
        task_type: CODE_ANALYSIS for Claude routing.
        operation: CONTEXT_GENERATION for telemetry.
    """

    task_type = TaskType.CODE_ANALYSIS
    operation = AIOperation.CONTEXT_GENERATION
    retry_config = RetryConfig(max_retries=2, initial_delay_seconds=1.0)

    # Use Claude Opus 4.5 for deep understanding
    OPUS_MODEL = "claude-opus-4-5-20251101"
    MAX_OUTPUT_TOKENS = 4096

    def __init__(
        self,
        model: str | None = None,
        max_output_tokens: int = 4096,
    ) -> None:
        """Initialize AI context agent.

        Args:
            model: Override default Claude model.
            max_output_tokens: Maximum response tokens.
        """
        super().__init__(model or self.OPUS_MODEL)
        self.max_output_tokens = max_output_tokens

    def validate_input(self, input_data: AIContextInput) -> None:
        """Validate input before processing.

        Args:
            input_data: The input to validate.

        Raises:
            ValueError: If input is invalid.
        """
        if not input_data.issue_id:
            raise ValueError("issue_id is required")
        if not input_data.issue_title:
            raise ValueError("issue_title is required")

    async def _execute_impl(
        self,
        input_data: AIContextInput,
        context: AgentContext,
    ) -> AgentResult[AIContextOutput]:
        """Execute context generation or refinement.

        Args:
            input_data: Context generation input.
            context: Agent execution context.

        Returns:
            AgentResult with generated context.
        """
        self.validate_input(input_data)

        # Get API key
        api_key = context.get_api_key(Provider.CLAUDE)
        if not api_key:
            raise AIConfigurationError(
                "Anthropic API key not configured for AI context",
                provider="anthropic",
                missing_fields=["api_key"],
            )

        # Determine if this is a refinement or initial generation
        if input_data.refinement_query:
            return await self._execute_refinement(input_data, api_key, context)
        return await self._execute_generation(input_data, api_key, context)

    async def _execute_generation(
        self,
        input_data: AIContextInput,
        api_key: str,
        context: AgentContext,
    ) -> AgentResult[AIContextOutput]:
        """Execute initial context generation.

        Args:
            input_data: Context generation input.
            api_key: Anthropic API key.
            context: Agent execution context.

        Returns:
            AgentResult with generated context.
        """
        # Convert RelatedItems to dicts for prompt building
        related_issues = [item.to_dict() for item in input_data.related_issues]
        related_notes = [item.to_dict() for item in input_data.related_notes]
        code_files = [ref.file_path for ref in input_data.code_references]

        # Build prompts
        system_prompt, user_prompt = build_context_generation_prompt(
            issue_title=input_data.issue_title,
            issue_description=input_data.issue_description,
            issue_identifier=input_data.issue_identifier,
            project_name=input_data.project_name,
            related_issues=related_issues,
            related_notes=related_notes,
            code_files=code_files,
        )

        try:
            client = anthropic.AsyncAnthropic(api_key=api_key)

            response = await client.messages.create(
                model=self.model,
                max_tokens=self.max_output_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )

            # Extract response text
            response_text = ""
            for block in response.content:
                if block.type == "text":
                    response_text = block.text
                    break

            # Parse response
            parsed = parse_context_response(response_text)

            # Build Claude Code prompt
            claude_code_prompt = build_claude_code_prompt(
                identifier=input_data.issue_identifier,
                title=input_data.issue_title,
                summary=parsed.summary,
                code_references=[ref.to_dict() for ref in input_data.code_references],
                tasks=parsed.tasks,
                instructions=parsed.claude_code_sections.get("instructions"),
                technical_notes=parsed.suggested_approach,
            )

            # Build output
            output = AIContextOutput(
                summary=parsed.summary,
                analysis=parsed.analysis,
                complexity=parsed.complexity,
                estimated_effort=parsed.estimated_effort,
                key_considerations=parsed.key_considerations,
                suggested_approach=parsed.suggested_approach,
                potential_blockers=parsed.potential_blockers,
                related_issues=[item.to_dict() for item in input_data.related_issues],
                related_notes=[item.to_dict() for item in input_data.related_notes],
                related_pages=[item.to_dict() for item in input_data.related_pages],
                code_references=[ref.to_dict() for ref in input_data.code_references],
                tasks_checklist=parsed.tasks,
                claude_code_prompt=claude_code_prompt,
                conversation_history=[],
                version=1,
            )

            return AgentResult(
                output=output,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                model=self.model,
                provider=Provider.CLAUDE,
            )

        except anthropic.RateLimitError as e:
            raise RateLimitError(
                "Anthropic rate limit exceeded",
                retry_after_seconds=60,
                provider="anthropic",
            ) from e

        except anthropic.APIError as e:
            logger.exception(
                "Anthropic API error in context generation",
                extra={
                    "error": str(e),
                    "correlation_id": context.correlation_id,
                },
            )
            raise

    async def _execute_refinement(
        self,
        input_data: AIContextInput,
        api_key: str,
        context: AgentContext,
    ) -> AgentResult[AIContextOutput]:
        """Execute context refinement via conversation.

        Args:
            input_data: Context refinement input.
            api_key: Anthropic API key.
            context: Agent execution context.

        Returns:
            AgentResult with refined context.
        """
        if not input_data.refinement_query:
            raise ValueError("refinement_query is required for refinement")

        # Build context summary from existing related items
        context_summary = (
            f"Issue: {input_data.issue_identifier} - {input_data.issue_title}\n"
            f"Related issues: {len(input_data.related_issues)}\n"
            f"Related notes: {len(input_data.related_notes)}\n"
            f"Code references: {len(input_data.code_references)}"
        )

        # Build refinement prompt
        system_prompt, messages = build_refinement_prompt(
            context_summary=context_summary,
            refinement_query=input_data.refinement_query,
            conversation_history=input_data.conversation_history,
        )

        try:
            client = anthropic.AsyncAnthropic(api_key=api_key)

            # Convert messages to Anthropic format
            api_messages: list[anthropic.types.MessageParam] = [
                {"role": msg["role"], "content": msg["content"]}  # type: ignore[typeddict-item]
                for msg in messages
            ]

            response = await client.messages.create(
                model=self.model,
                max_tokens=self.max_output_tokens,
                system=system_prompt,
                messages=api_messages,  # type: ignore[arg-type]
            )

            # Extract response text
            response_text = ""
            for block in response.content:
                if block.type == "text":
                    response_text = block.text
                    break

            # Update conversation history
            updated_history = list(input_data.conversation_history)
            updated_history.append(
                {
                    "role": "user",
                    "content": input_data.refinement_query,
                    "timestamp": datetime.now(tz=UTC).isoformat(),
                }
            )
            updated_history.append(
                {
                    "role": "assistant",
                    "content": response_text,
                    "timestamp": datetime.now(tz=UTC).isoformat(),
                }
            )

            # Extract any updates from response
            updates = extract_refinement_updates(response_text, {})

            # Build output with updates
            output = AIContextOutput(
                summary=response_text[:500]
                if len(response_text) < 500
                else response_text[:500] + "...",
                related_issues=[item.to_dict() for item in input_data.related_issues],
                related_notes=[item.to_dict() for item in input_data.related_notes],
                related_pages=[item.to_dict() for item in input_data.related_pages],
                code_references=[ref.to_dict() for ref in input_data.code_references],
                tasks_checklist=updates.get("tasks_checklist", []),
                conversation_history=updated_history,
            )

            return AgentResult(
                output=output,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                model=self.model,
                provider=Provider.CLAUDE,
            )

        except anthropic.RateLimitError as e:
            raise RateLimitError(
                "Anthropic rate limit exceeded",
                retry_after_seconds=60,
                provider="anthropic",
            ) from e

        except anthropic.APIError as e:
            logger.exception(
                "Anthropic API error in context refinement",
                extra={
                    "error": str(e),
                    "correlation_id": context.correlation_id,
                },
            )
            raise

    async def stream_refinement(
        self,
        input_data: AIContextInput,
        context: AgentContext,
    ) -> AsyncIterator[str]:
        """Stream refinement response.

        Args:
            input_data: Context refinement input.
            context: Agent execution context.

        Yields:
            Response chunks as they're generated.
        """
        if not input_data.refinement_query:
            raise ValueError("refinement_query is required for refinement")

        api_key = context.get_api_key(Provider.CLAUDE)
        if not api_key:
            raise AIConfigurationError(
                "Anthropic API key not configured",
                provider="anthropic",
            )

        # Build context summary
        context_summary = (
            f"Issue: {input_data.issue_identifier} - {input_data.issue_title}\n"
            f"Related issues: {len(input_data.related_issues)}\n"
            f"Related notes: {len(input_data.related_notes)}\n"
            f"Code references: {len(input_data.code_references)}"
        )

        # Build refinement prompt
        system_prompt, messages = build_refinement_prompt(
            context_summary=context_summary,
            refinement_query=input_data.refinement_query,
            conversation_history=input_data.conversation_history,
        )

        # Convert messages to Anthropic format
        api_messages: list[anthropic.types.MessageParam] = [
            {"role": msg["role"], "content": msg["content"]}  # type: ignore[typeddict-item]
            for msg in messages
        ]

        client = anthropic.AsyncAnthropic(api_key=api_key)

        async with client.messages.stream(
            model=self.model,
            max_tokens=self.max_output_tokens,
            system=system_prompt,
            messages=api_messages,  # type: ignore[arg-type]
        ) as stream:
            async for text in stream.text_stream:
                yield text


__all__ = [
    "AIContextAgent",
    "AIContextInput",
    "AIContextOutput",
    "CodeReference",
    "RelatedItem",
    "TaskItem",
]
