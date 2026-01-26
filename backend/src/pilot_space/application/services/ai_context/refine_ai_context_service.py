"""Refine AI Context service.

T207: Create RefineAIContextService for multi-turn refinement.

Handles:
- Multi-turn conversation with existing context
- SSE streaming responses
- Conversation history management
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pilot_space.ai.agents.ai_context_agent import (
    AIContextAgent,
    AIContextInput,
    CodeReference,
    RelatedItem,
)
from pilot_space.ai.agents.sdk_base import AgentContext

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.ai.infrastructure.cost_tracker import CostTracker
    from pilot_space.ai.infrastructure.resilience import ResilientExecutor
    from pilot_space.ai.providers.provider_selector import ProviderSelector
    from pilot_space.ai.tools.mcp_server import ToolRegistry
    from pilot_space.infrastructure.database.repositories import (
        AIContextRepository,
        IssueRepository,
    )

logger = logging.getLogger(__name__)


@dataclass
class RefineAIContextPayload:
    """Payload for refining AI context.

    Attributes:
        workspace_id: Workspace UUID.
        issue_id: Issue UUID.
        user_id: User requesting refinement.
        query: User's refinement query.
        correlation_id: Request correlation ID for tracing.
        api_keys: Provider API keys from user configuration.
    """

    workspace_id: UUID
    issue_id: UUID
    user_id: UUID
    query: str
    correlation_id: str = ""
    api_keys: dict[str, str] = field(default_factory=dict)


@dataclass
class RefineAIContextResult:
    """Result from AI context refinement.

    Attributes:
        context_id: Context UUID.
        issue_id: Issue UUID.
        response: AI response text.
        conversation_count: Total conversation messages.
        last_refined_at: Refinement timestamp.
    """

    context_id: UUID
    issue_id: UUID
    response: str
    conversation_count: int
    last_refined_at: datetime


class RefineAIContextService:
    """Service for refining AI context via multi-turn conversation.

    Handles:
    - Loading existing context and conversation history
    - Executing refinement via AIContextAgent
    - Updating conversation history
    - SSE streaming for real-time responses
    """

    def __init__(
        self,
        session: AsyncSession,
        ai_context_repository: AIContextRepository,
        issue_repository: IssueRepository,
        tool_registry: ToolRegistry,
        provider_selector: ProviderSelector,
        cost_tracker: CostTracker,
        resilient_executor: ResilientExecutor,
    ) -> None:
        """Initialize service.

        Args:
            session: Async database session.
            ai_context_repository: AIContext repository.
            issue_repository: Issue repository.
            tool_registry: MCP tool registry.
            provider_selector: Provider/model selection service.
            cost_tracker: Cost tracking service.
            resilient_executor: Retry and circuit breaker service.
        """
        self._session = session
        self._context_repo = ai_context_repository
        self._issue_repo = issue_repository
        self._tool_registry = tool_registry
        self._provider_selector = provider_selector
        self._cost_tracker = cost_tracker
        self._resilient_executor = resilient_executor

    async def execute(
        self,
        payload: RefineAIContextPayload,
    ) -> RefineAIContextResult:
        """Refine AI context with a new query.

        Args:
            payload: Refinement parameters.

        Returns:
            RefineAIContextResult with AI response.

        Raises:
            ValueError: If context or issue not found.
        """
        logger.info(
            "Refining AI context",
            extra={
                "issue_id": str(payload.issue_id),
                "workspace_id": str(payload.workspace_id),
                "correlation_id": payload.correlation_id,
            },
        )

        # Get existing context
        context = await self._context_repo.get_by_issue_id(payload.issue_id)
        if not context:
            raise ValueError(
                f"AI context not found for issue: {payload.issue_id}. "
                "Generate context first before refining."
            )

        # Get issue for context
        issue = await self._issue_repo.get_by_id_with_relations(payload.issue_id)
        if not issue:
            raise ValueError(f"Issue not found: {payload.issue_id}")

        # Build related items from stored data
        related_issues = [
            RelatedItem(
                id=item.get("id", ""),
                type="issue",
                title=item.get("title", ""),
                relevance_score=item.get("relevance_score", 0.5),
                excerpt=item.get("excerpt", ""),
                identifier=item.get("identifier"),
                state=item.get("state"),
            )
            for item in context.related_issues
        ]

        related_notes = [
            RelatedItem(
                id=item.get("id", ""),
                type="note",
                title=item.get("title", ""),
                relevance_score=item.get("relevance_score", 0.5),
                excerpt=item.get("excerpt", ""),
            )
            for item in context.related_notes
        ]

        code_references = [
            CodeReference(
                file_path=ref.get("file_path", ""),
                line_range=(int(ref["line_start"]), int(ref["line_end"]))
                if ref.get("line_start") is not None and ref.get("line_end") is not None
                else None,
                description=ref.get("description", ""),
                relevance=ref.get("relevance", "medium"),
            )
            for ref in context.code_references
        ]

        # Build agent input with refinement query
        agent_input = AIContextInput(
            issue_id=str(payload.issue_id),
            issue_title=issue.name,
            issue_description=issue.description,
            issue_identifier=issue.identifier,
            workspace_id=str(payload.workspace_id),
            project_name=issue.project.name if issue.project else None,
            related_issues=related_issues,
            related_notes=related_notes,
            code_references=code_references,
            conversation_history=context.conversation_history or [],
            refinement_query=payload.query,
        )

        # Build agent context
        agent_context = AgentContext(
            workspace_id=payload.workspace_id,
            user_id=payload.user_id,
            operation_id=None,
            metadata={"correlation_id": payload.correlation_id},
        )

        # Extract Anthropic API key for the agent
        anthropic_key = payload.api_keys.get("anthropic", "")
        if not anthropic_key:
            raise ValueError("Anthropic API key is required")

        # Update input with API key
        agent_input.api_key = anthropic_key

        # Execute agent
        agent = AIContextAgent(
            tool_registry=self._tool_registry,
            provider_selector=self._provider_selector,
            cost_tracker=self._cost_tracker,
            resilient_executor=self._resilient_executor,
        )
        result = await agent.run(agent_input, agent_context)
        if not result.success or not result.output:
            raise ValueError(f"Agent refinement failed: {result.error}")
        output = result.output

        # Update conversation history
        await self._context_repo.update_conversation_history(
            issue_id=payload.issue_id,
            history=output.conversation_history,
        )

        await self._session.commit()

        # Refresh context
        context = await self._context_repo.get_by_issue_id(payload.issue_id)
        if not context:
            raise ValueError("Failed to retrieve updated context")

        # Extract response from last assistant message
        response_text = ""
        if output.conversation_history:
            for msg in reversed(output.conversation_history):
                if msg.get("role") == "assistant":
                    response_text = msg.get("content", "")
                    break

        logger.info(
            "AI context refined",
            extra={
                "issue_id": str(payload.issue_id),
                "context_id": str(context.id),
                "conversation_count": context.conversation_count,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "cost_usd": result.cost_usd,
            },
        )

        return RefineAIContextResult(
            context_id=context.id,
            issue_id=payload.issue_id,
            response=response_text,
            conversation_count=context.conversation_count,
            last_refined_at=context.last_refined_at or datetime.now(tz=UTC),
        )

    async def stream(
        self,
        payload: RefineAIContextPayload,
    ) -> AsyncIterator[str]:
        """Stream refinement response via SSE.

        Args:
            payload: Refinement parameters.

        Yields:
            Response chunks as they're generated.
        """
        logger.info(
            "Streaming AI context refinement",
            extra={
                "issue_id": str(payload.issue_id),
                "correlation_id": payload.correlation_id,
            },
        )

        # Get existing context
        context = await self._context_repo.get_by_issue_id(payload.issue_id)
        if not context:
            yield f"Error: AI context not found for issue {payload.issue_id}"
            return

        # Get issue for context
        issue = await self._issue_repo.get_by_id_with_relations(payload.issue_id)
        if not issue:
            yield f"Error: Issue not found: {payload.issue_id}"
            return

        # Build related items from stored data
        related_issues = [
            RelatedItem(
                id=item.get("id", ""),
                type="issue",
                title=item.get("title", ""),
                relevance_score=item.get("relevance_score", 0.5),
                excerpt=item.get("excerpt", ""),
            )
            for item in context.related_issues
        ]

        code_references = [
            CodeReference(
                file_path=ref.get("file_path", ""),
                description=ref.get("description", ""),
            )
            for ref in context.code_references
        ]

        # Build agent input
        agent_input = AIContextInput(
            issue_id=str(payload.issue_id),
            issue_title=issue.name,
            issue_description=issue.description,
            issue_identifier=issue.identifier,
            workspace_id=str(payload.workspace_id),
            project_name=issue.project.name if issue.project else None,
            related_issues=related_issues,
            related_notes=[],
            code_references=code_references,
            conversation_history=context.conversation_history or [],
            refinement_query=payload.query,
        )

        # Build agent context
        agent_context = AgentContext(
            workspace_id=payload.workspace_id,
            user_id=payload.user_id,
            operation_id=None,
            metadata={"correlation_id": payload.correlation_id},
        )

        # Extract Anthropic API key for the agent
        anthropic_key = payload.api_keys.get("anthropic", "")
        if not anthropic_key:
            yield "Error: Anthropic API key is required"
            return

        # Update input with API key
        agent_input.api_key = anthropic_key

        # Stream from agent
        agent = AIContextAgent(
            tool_registry=self._tool_registry,
            provider_selector=self._provider_selector,
            cost_tracker=self._cost_tracker,
            resilient_executor=self._resilient_executor,
        )
        full_response = ""

        async for chunk in agent.run_stream(agent_input, agent_context):
            full_response += chunk
            yield chunk

        # Update conversation history after streaming completes
        updated_history = list(context.conversation_history or [])
        updated_history.append(
            {
                "role": "user",
                "content": payload.query,
                "timestamp": datetime.now(tz=UTC).isoformat(),
            }
        )
        updated_history.append(
            {
                "role": "assistant",
                "content": full_response,
                "timestamp": datetime.now(tz=UTC).isoformat(),
            }
        )

        await self._context_repo.update_conversation_history(
            issue_id=payload.issue_id,
            history=updated_history,
        )
        await self._session.commit()


__all__ = [
    "RefineAIContextPayload",
    "RefineAIContextResult",
    "RefineAIContextService",
]
