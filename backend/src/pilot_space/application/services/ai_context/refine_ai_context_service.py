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
from pilot_space.ai.agents.base import AgentContext, Provider

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncSession

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
        api_keys = {
            Provider.CLAUDE: payload.api_keys.get("anthropic", ""),
            Provider.OPENAI: payload.api_keys.get("openai", ""),
        }
        agent_context = AgentContext(
            workspace_id=payload.workspace_id,
            user_id=payload.user_id,
            correlation_id=payload.correlation_id,
            api_keys=api_keys,
        )

        # Execute agent
        agent = AIContextAgent()
        result = await agent.execute(agent_input, agent_context)
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
        api_keys = {
            Provider.CLAUDE: payload.api_keys.get("anthropic", ""),
            Provider.OPENAI: payload.api_keys.get("openai", ""),
        }
        agent_context = AgentContext(
            workspace_id=payload.workspace_id,
            user_id=payload.user_id,
            correlation_id=payload.correlation_id,
            api_keys=api_keys,
        )

        # Stream from agent
        agent = AIContextAgent()
        full_response = ""

        async for chunk in agent.stream_refinement(agent_input, agent_context):
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
