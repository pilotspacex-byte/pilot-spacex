"""Generate Implementation Plan service.

Reads an existing AIContext record, calls PlanGenerationAgent to produce
a YAML-frontmatter markdown plan, and persists it to content["implementation_plan"].

Prerequisites: AIContext must already exist (GenerateAIContextService must have
been run first). Raises ValueError if not found.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pilot_space.ai.agents.plan_generation_agent import PlanGenerationAgent, PlanInput
from pilot_space.domain.exceptions import NotFoundError, ValidationError
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.ai.agents.pilotspace_agent import PilotSpaceAgent
    from pilot_space.infrastructure.database.repositories import (
        AIContextRepository,
        IssueRepository,
    )

logger = get_logger(__name__)


@dataclass
class GeneratePlanPayload:
    """Payload for generating an implementation plan.

    Attributes:
        workspace_id: Workspace UUID.
        issue_id: Issue UUID.
        user_id: User requesting generation.
        correlation_id: Request correlation ID for tracing.
    """

    workspace_id: UUID
    issue_id: UUID
    user_id: UUID
    correlation_id: str = ""


@dataclass
class GeneratePlanResult:
    """Result from implementation plan generation.

    Attributes:
        context_id: AIContext UUID that was updated.
        issue_id: Issue UUID.
        subagent_count: Number of subagents in the generated plan.
        generated_at: Timestamp when plan was generated.
    """

    context_id: UUID
    issue_id: UUID
    subagent_count: int
    generated_at: datetime


class GenerateImplementationPlanService:
    """Service for generating implementation plans for issues.

    Requires an existing AIContext record. Calls PlanGenerationAgent with the
    existing context data, then merges the plan markdown into
    content["implementation_plan"] on the same record.

    Usage:
        service = GenerateImplementationPlanService(
            session=session,
            ai_context_repository=context_repo,
            issue_repository=issue_repo,
            pilotspace_agent=agent,
        )
        result = await service.execute(payload)
    """

    def __init__(
        self,
        session: AsyncSession,
        ai_context_repository: AIContextRepository,
        issue_repository: IssueRepository,
        pilotspace_agent: PilotSpaceAgent,
    ) -> None:
        """Initialize service.

        Args:
            session: Async database session.
            ai_context_repository: AIContext repository.
            issue_repository: Issue repository.
            pilotspace_agent: PilotSpaceAgent for BYOK key resolution.
        """
        self._session = session
        self._context_repo = ai_context_repository
        self._issue_repo = issue_repository
        self._pilotspace_agent = pilotspace_agent

    async def execute(self, payload: GeneratePlanPayload) -> GeneratePlanResult:
        """Generate and persist implementation plan.

        Args:
            payload: Generation parameters.

        Returns:
            GeneratePlanResult with context ID and subagent count.

        Raises:
            NotFoundError: If AIContext or issue not found.
            ValidationError: If plan persistence fails.
        """
        logger.info(
            "Generating implementation plan",
            extra={
                "issue_id": str(payload.issue_id),
                "workspace_id": str(payload.workspace_id),
                "correlation_id": payload.correlation_id,
            },
        )

        # Load existing AIContext — prerequisite check
        context = await self._context_repo.get_by_issue_id(payload.issue_id)
        if not context:
            raise NotFoundError(
                f"No AI context found for issue {payload.issue_id}. "
                "Generate AI context first before creating an implementation plan."
            )

        # Load issue for identifier/title
        issue = await self._issue_repo.get_by_id_with_relations(payload.issue_id)
        if not issue:
            raise NotFoundError(f"Issue not found: {payload.issue_id}")

        # Build PlanInput from existing context data
        content_data = context.content or {}
        plan_input = PlanInput(
            issue_id=str(payload.issue_id),
            issue_title=issue.name,
            issue_description=issue.description,
            issue_identifier=issue.identifier,
            workspace_id=str(payload.workspace_id),
            tasks_checklist=list(context.tasks_checklist or []),
            related_issues=list(context.related_issues or []),
            code_references=list(context.code_references or []),
            complexity=content_data.get("complexity", "medium"),
            suggested_approach=content_data.get("suggested_approach", ""),
        )

        # Run PlanGenerationAgent
        agent = PlanGenerationAgent(pilotspace_agent=self._pilotspace_agent)
        plan_output = await agent.run(plan_input)

        # Merge plan into existing content dict
        new_content = {**content_data, "implementation_plan": plan_output.plan_markdown}

        # Persist via narrow update method
        updated = await self._context_repo.update_plan_content(
            issue_id=payload.issue_id,
            new_content=new_content,
        )
        if not updated:
            raise ValidationError(f"Failed to persist plan for issue: {payload.issue_id}")

        await self._session.commit()

        generated_at = datetime.now(tz=UTC)

        logger.info(
            "Implementation plan generated",
            extra={
                "issue_id": str(payload.issue_id),
                "context_id": str(context.id),
                "subagent_count": plan_output.subagent_count,
            },
        )

        return GeneratePlanResult(
            context_id=context.id,
            issue_id=payload.issue_id,
            subagent_count=plan_output.subagent_count,
            generated_at=generated_at,
        )


__all__ = [
    "GenerateImplementationPlanService",
    "GeneratePlanPayload",
    "GeneratePlanResult",
]
