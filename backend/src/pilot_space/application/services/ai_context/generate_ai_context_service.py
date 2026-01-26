"""Generate AI Context service.

T206: Create GenerateAIContextService for context generation.

Handles:
- Fetching related items via embeddings
- Extracting code from linked commits/PRs
- Generating context via AIContextAgent
- Caching for 1 hour unless forced
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
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
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.ai.infrastructure.cost_tracker import CostTracker
    from pilot_space.ai.infrastructure.resilience import ResilientExecutor
    from pilot_space.ai.providers.provider_selector import ProviderSelector
    from pilot_space.ai.tools.mcp_server import ToolRegistry
    from pilot_space.infrastructure.database.repositories import (
        AIContextRepository,
        IntegrationLinkRepository,
        IssueRepository,
        NoteRepository,
    )

logger = logging.getLogger(__name__)

# Cache duration in hours
CACHE_DURATION_HOURS = 1


@dataclass
class GenerateAIContextPayload:
    """Payload for generating AI context.

    Attributes:
        workspace_id: Workspace UUID.
        issue_id: Issue UUID.
        user_id: User requesting generation.
        force_regenerate: Bypass cache and regenerate.
        correlation_id: Request correlation ID for tracing.
        api_keys: Provider API keys from user configuration.
    """

    workspace_id: UUID
    issue_id: UUID
    user_id: UUID
    force_regenerate: bool = False
    correlation_id: str = ""
    api_keys: dict[str, str] = field(default_factory=dict)


@dataclass
class GenerateAIContextResult:
    """Result from AI context generation.

    Attributes:
        context_id: Generated context UUID.
        issue_id: Issue UUID.
        summary: Generated summary.
        complexity: Detected complexity (low, medium, high).
        task_count: Number of generated tasks.
        related_issue_count: Number of related issues found.
        claude_code_prompt: Generated Claude Code prompt.
        from_cache: Whether result was from cache.
        generated_at: Generation timestamp.
        version: Context version.
    """

    context_id: UUID
    issue_id: UUID
    summary: str
    complexity: str
    task_count: int
    related_issue_count: int
    claude_code_prompt: str | None
    from_cache: bool
    generated_at: datetime
    version: int


class GenerateAIContextService:
    """Service for generating AI context for issues.

    Handles:
    - Cache checking (1 hour freshness)
    - Related item discovery via embeddings
    - Code reference extraction from integrations
    - Context generation via AIContextAgent
    """

    def __init__(
        self,
        session: AsyncSession,
        ai_context_repository: AIContextRepository,
        issue_repository: IssueRepository,
        note_repository: NoteRepository,
        integration_link_repository: IntegrationLinkRepository,
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
            note_repository: Note repository.
            integration_link_repository: IntegrationLink repository.
            tool_registry: MCP tool registry.
            provider_selector: Provider/model selection service.
            cost_tracker: Cost tracking service.
            resilient_executor: Retry and circuit breaker service.
        """
        self._session = session
        self._context_repo = ai_context_repository
        self._issue_repo = issue_repository
        self._note_repo = note_repository
        self._link_repo = integration_link_repository
        self._tool_registry = tool_registry
        self._provider_selector = provider_selector
        self._cost_tracker = cost_tracker
        self._resilient_executor = resilient_executor

    async def execute(
        self,
        payload: GenerateAIContextPayload,
    ) -> GenerateAIContextResult:
        """Generate AI context for an issue.

        Args:
            payload: Generation parameters.

        Returns:
            GenerateAIContextResult with generated context.

        Raises:
            ValueError: If issue not found.
            AIConfigurationError: If API keys missing.
        """
        logger.info(
            "Generating AI context",
            extra={
                "issue_id": str(payload.issue_id),
                "workspace_id": str(payload.workspace_id),
                "force_regenerate": payload.force_regenerate,
                "correlation_id": payload.correlation_id,
            },
        )

        # Get issue
        issue = await self._issue_repo.get_by_id_with_relations(payload.issue_id)
        if not issue:
            raise ValueError(f"Issue not found: {payload.issue_id}")

        # Check cache unless forced
        if not payload.force_regenerate:
            is_fresh = await self._context_repo.is_fresh(
                payload.issue_id,
                max_age_hours=CACHE_DURATION_HOURS,
            )
            if is_fresh:
                existing = await self._context_repo.get_by_issue_id(payload.issue_id)
                if existing:
                    logger.info(
                        "Returning cached AI context",
                        extra={
                            "issue_id": str(payload.issue_id),
                            "context_id": str(existing.id),
                            "version": existing.version,
                        },
                    )
                    return GenerateAIContextResult(
                        context_id=existing.id,
                        issue_id=payload.issue_id,
                        summary=existing.summary or "",
                        complexity=existing.content.get("complexity", "medium"),
                        task_count=existing.task_count,
                        related_issue_count=len(existing.related_issues),
                        claude_code_prompt=existing.claude_code_prompt,
                        from_cache=True,
                        generated_at=existing.generated_at,
                        version=existing.version,
                    )

        # Get or create context record
        context, _ = await self._context_repo.get_or_create(
            issue_id=payload.issue_id,
            workspace_id=payload.workspace_id,
        )

        # Fetch related items
        related_issues = await self._find_related_issues(
            workspace_id=payload.workspace_id,
            issue_id=payload.issue_id,
            issue_title=issue.name,
        )
        related_notes = await self._find_related_notes(
            workspace_id=payload.workspace_id,
            issue_title=issue.name,
        )

        # Get code references from integration links
        code_references = await self._extract_code_references(
            issue_id=payload.issue_id,
        )

        # Build agent input
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
            raise ValueError(f"Agent execution failed: {result.error}")
        output = result.output

        # Update context in database
        await self._context_repo.update_content(
            issue_id=payload.issue_id,
            content=output.to_content_dict(),
            claude_code_prompt=output.claude_code_prompt,
            tasks_checklist=output.tasks_checklist,
            related_issues=output.related_issues,
            related_notes=output.related_notes,
            related_pages=output.related_pages,
            code_references=output.code_references,
        )

        # Refresh context
        context = await self._context_repo.get_by_issue_id(payload.issue_id)
        if not context:
            raise ValueError("Failed to retrieve updated context")

        await self._session.commit()

        logger.info(
            "AI context generated",
            extra={
                "issue_id": str(payload.issue_id),
                "context_id": str(context.id),
                "task_count": len(output.tasks_checklist),
                "related_issues": len(output.related_issues),
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "cost_usd": result.cost_usd,
            },
        )

        return GenerateAIContextResult(
            context_id=context.id,
            issue_id=payload.issue_id,
            summary=output.summary,
            complexity=output.complexity,
            task_count=len(output.tasks_checklist),
            related_issue_count=len(output.related_issues),
            claude_code_prompt=output.claude_code_prompt,
            from_cache=False,
            generated_at=context.generated_at,
            version=context.version,
        )

    async def _find_related_issues(
        self,
        workspace_id: UUID,  # noqa: ARG002 - Reserved for embedding-based search
        issue_id: UUID,
        issue_title: str,
        limit: int = 5,
    ) -> list[RelatedItem]:
        """Find related issues via text search.

        For MVP, uses simple text search. In production, would use
        embeddings for semantic similarity.

        Args:
            workspace_id: Workspace UUID.
            issue_id: Current issue ID (to exclude).
            issue_title: Issue title for matching.
            limit: Maximum issues to return.

        Returns:
            List of RelatedItem instances.
        """
        # Simple search for related issues
        # In production, this would use embedding similarity
        related_issues: list[RelatedItem] = []

        try:
            # Search by title keywords
            keywords = issue_title.split()[:3]  # First 3 words
            if keywords:
                search_term = " ".join(keywords)
                issues = await self._issue_repo.search(
                    search_term=search_term,
                    search_columns=["name", "description"],
                    limit=limit + 1,  # Get one extra to exclude current
                )

                for issue_item in issues:
                    if issue_item.id == issue_id:
                        continue
                    if len(related_issues) >= limit:
                        break

                    related_issues.append(
                        RelatedItem(
                            id=str(issue_item.id),
                            type="issue",
                            title=issue_item.name,
                            relevance_score=0.7,  # Placeholder score
                            excerpt=issue_item.description[:100] if issue_item.description else "",
                            identifier=issue_item.identifier,
                            state=issue_item.state.name if issue_item.state else None,
                        )
                    )
        except Exception as e:
            logger.warning(f"Error finding related issues: {e}")

        return related_issues

    async def _find_related_notes(
        self,
        workspace_id: UUID,  # noqa: ARG002 - Reserved for embedding-based search
        issue_title: str,
        limit: int = 5,
    ) -> list[RelatedItem]:
        """Find related notes via text search.

        For MVP, uses simple text search. In production, would use
        embeddings for semantic similarity.

        Args:
            workspace_id: Workspace UUID.
            issue_title: Issue title for matching.
            limit: Maximum notes to return.

        Returns:
            List of RelatedItem instances.
        """
        related_notes: list[RelatedItem] = []

        try:
            # Search by title keywords
            keywords = issue_title.split()[:3]
            if keywords:
                search_term = " ".join(keywords)
                notes = await self._note_repo.search(
                    search_term=search_term,
                    search_columns=["title", "content"],
                    limit=limit,
                )

                for note in notes:
                    content_preview = ""
                    if note.content:
                        # Extract text from blocks
                        blocks = note.content.get("blocks", [])
                        for block in blocks[:2]:
                            if isinstance(block, dict):
                                text = block.get("text", "")
                                if text:
                                    content_preview += text[:100]
                                    break

                    related_notes.append(
                        RelatedItem(
                            id=str(note.id),
                            type="note",
                            title=note.title,
                            relevance_score=0.6,  # Placeholder score
                            excerpt=content_preview,
                        )
                    )
        except Exception as e:
            logger.warning(f"Error finding related notes: {e}")

        return related_notes

    async def _extract_code_references(
        self,
        issue_id: UUID,
    ) -> list[CodeReference]:
        """Extract code references from linked commits/PRs.

        Args:
            issue_id: Issue UUID.

        Returns:
            List of CodeReference instances.
        """
        code_references: list[CodeReference] = []

        try:
            links = await self._link_repo.get_by_issue(issue_id)

            for link in links:
                if not link.link_metadata:
                    continue

                # Extract file paths from metadata
                files = link.link_metadata.get("files", [])
                for file_info in files[:5]:  # Limit per link
                    if isinstance(file_info, dict):
                        file_path = file_info.get("filename", "")
                        if file_path:
                            code_references.append(
                                CodeReference(
                                    file_path=file_path,
                                    description=f"From {link.link_type.value}: {link.title or 'Untitled'}",
                                    relevance="medium",
                                )
                            )
                    elif isinstance(file_info, str):
                        code_references.append(
                            CodeReference(
                                file_path=file_info,
                                description=f"From {link.link_type.value}",
                                relevance="medium",
                            )
                        )
        except Exception as e:
            logger.warning(f"Error extracting code references: {e}")

        return code_references


__all__ = [
    "GenerateAIContextPayload",
    "GenerateAIContextResult",
    "GenerateAIContextService",
]
