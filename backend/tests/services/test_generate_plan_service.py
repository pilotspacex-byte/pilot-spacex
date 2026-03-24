"""Unit tests for GenerateImplementationPlanService.

Coverage:
- ValueError when no AIContext exists for the issue
- ValueError when issue not found
- Agent is called with correct PlanInput fields
- Plan is persisted to content["implementation_plan"]
- GeneratePlanResult contains correct subagent_count
- Existing content is preserved when merging plan
- ValueError when update_plan_content returns False
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from pilot_space.ai.agents.plan_generation_agent import PlanInput, PlanOutput
from pilot_space.application.services.ai_context.generate_plan_service import (
    GenerateImplementationPlanService,
    GeneratePlanPayload,
    GeneratePlanResult,
)
from pilot_space.domain.exceptions import NotFoundError, ValidationError

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

WORKSPACE_ID = uuid4()
ISSUE_ID = uuid4()
USER_ID = uuid4()
CONTEXT_ID = uuid4()


def _make_ai_context(
    *,
    issue_id: UUID = ISSUE_ID,
    context_id: UUID = CONTEXT_ID,
    content: dict[str, Any] | None = None,
    tasks_checklist: list[dict[str, Any]] | None = None,
    related_issues: list[dict[str, Any]] | None = None,
    code_references: list[dict[str, Any]] | None = None,
) -> MagicMock:
    """Build a mock AIContext object."""
    ctx = MagicMock()
    ctx.id = context_id
    ctx.issue_id = issue_id
    ctx.content = content or {"summary": "Test summary", "complexity": "high"}
    ctx.tasks_checklist = tasks_checklist or [
        {"description": "Task A", "estimated_effort": "1d"},
    ]
    ctx.related_issues = related_issues or [
        {"identifier": "PS-10", "title": "Related"},
    ]
    ctx.code_references = code_references or [
        {"file_path": "src/auth.py", "description": "Auth module"},
    ]
    return ctx


def _make_issue(
    *,
    issue_id: UUID = ISSUE_ID,
    name: str = "Add authentication",
    description: str | None = "Implement OAuth2 flow",
    identifier: str = "PS-42",
) -> MagicMock:
    """Build a mock Issue object."""
    issue = MagicMock()
    issue.id = issue_id
    issue.name = name
    issue.description = description
    issue.identifier = identifier
    return issue


def _make_plan_output(
    *,
    plan_markdown: str = "---\nissue: PS-42\n---\n# PS-42: Plan",
    subagent_count: int = 3,
) -> PlanOutput:
    """Build a PlanOutput dataclass."""
    return PlanOutput(plan_markdown=plan_markdown, subagent_count=subagent_count)


def _make_payload(
    *,
    workspace_id: UUID = WORKSPACE_ID,
    issue_id: UUID = ISSUE_ID,
    user_id: UUID = USER_ID,
) -> GeneratePlanPayload:
    """Build a GeneratePlanPayload."""
    return GeneratePlanPayload(
        workspace_id=workspace_id,
        issue_id=issue_id,
        user_id=user_id,
        correlation_id="test-corr-123",
    )


def _make_service(
    *,
    session: AsyncMock | None = None,
    context_repo: AsyncMock | None = None,
    issue_repo: AsyncMock | None = None,
    pilotspace_agent: MagicMock | None = None,
) -> GenerateImplementationPlanService:
    """Build service with mock dependencies."""
    return GenerateImplementationPlanService(
        session=session or AsyncMock(),
        ai_context_repository=context_repo or AsyncMock(),
        issue_repository=issue_repo or AsyncMock(),
        pilotspace_agent=pilotspace_agent or MagicMock(),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGenerateImplementationPlanService:
    """Tests for GenerateImplementationPlanService.execute()."""

    @pytest.mark.asyncio
    async def test_raises_when_no_ai_context(self) -> None:
        """ValueError raised when no AIContext exists for the issue."""
        context_repo = AsyncMock()
        context_repo.get_by_issue_id = AsyncMock(return_value=None)

        service = _make_service(context_repo=context_repo)
        payload = _make_payload()

        with pytest.raises(NotFoundError, match="No AI context found"):
            await service.execute(payload)

    @pytest.mark.asyncio
    async def test_raises_when_issue_not_found(self) -> None:
        """ValueError raised when issue does not exist."""
        context_repo = AsyncMock()
        context_repo.get_by_issue_id = AsyncMock(return_value=_make_ai_context())

        issue_repo = AsyncMock()
        issue_repo.get_by_id_with_relations = AsyncMock(return_value=None)

        service = _make_service(context_repo=context_repo, issue_repo=issue_repo)
        payload = _make_payload()

        with pytest.raises(NotFoundError, match="Issue not found"):
            await service.execute(payload)

    @pytest.mark.asyncio
    async def test_agent_called_with_correct_plan_input(self) -> None:
        """PlanGenerationAgent.run() receives PlanInput with correct fields."""
        ai_context = _make_ai_context(
            content={"complexity": "high", "suggested_approach": "Use DDD"},
        )
        issue = _make_issue(
            name="Implement DDD",
            description="Apply domain-driven design",
            identifier="PS-55",
        )

        context_repo = AsyncMock()
        context_repo.get_by_issue_id = AsyncMock(return_value=ai_context)
        context_repo.update_plan_content = AsyncMock(return_value=True)

        issue_repo = AsyncMock()
        issue_repo.get_by_id_with_relations = AsyncMock(return_value=issue)

        plan_output = _make_plan_output(subagent_count=2)

        with patch(
            "pilot_space.application.services.ai_context.generate_plan_service.PlanGenerationAgent"
        ) as MockAgent:
            mock_agent_instance = AsyncMock()
            mock_agent_instance.run = AsyncMock(return_value=plan_output)
            MockAgent.return_value = mock_agent_instance

            service = _make_service(
                context_repo=context_repo,
                issue_repo=issue_repo,
            )
            await service.execute(_make_payload())

            # Verify agent.run was called
            mock_agent_instance.run.assert_awaited_once()

            # Inspect the PlanInput argument
            call_args = mock_agent_instance.run.call_args
            plan_input: PlanInput = call_args[0][0]

            assert plan_input.issue_title == "Implement DDD"
            assert plan_input.issue_description == "Apply domain-driven design"
            assert plan_input.issue_identifier == "PS-55"
            assert plan_input.workspace_id == str(WORKSPACE_ID)
            assert plan_input.complexity == "high"
            assert plan_input.suggested_approach == "Use DDD"
            assert len(plan_input.tasks_checklist) == 1
            assert len(plan_input.related_issues) == 1
            assert len(plan_input.code_references) == 1

    @pytest.mark.asyncio
    async def test_plan_persisted_to_implementation_plan_key(self) -> None:
        """Plan markdown is merged into content['implementation_plan']."""
        existing_content = {"summary": "Existing summary", "complexity": "medium"}
        ai_context = _make_ai_context(content=existing_content)
        issue = _make_issue()

        context_repo = AsyncMock()
        context_repo.get_by_issue_id = AsyncMock(return_value=ai_context)
        context_repo.update_plan_content = AsyncMock(return_value=True)

        issue_repo = AsyncMock()
        issue_repo.get_by_id_with_relations = AsyncMock(return_value=issue)

        plan_md = "---\nissue: PS-42\n---\n# PS-42: Persisted Plan"
        plan_output = _make_plan_output(plan_markdown=plan_md, subagent_count=1)

        session = AsyncMock()

        with patch(
            "pilot_space.application.services.ai_context.generate_plan_service.PlanGenerationAgent"
        ) as MockAgent:
            mock_agent_instance = AsyncMock()
            mock_agent_instance.run = AsyncMock(return_value=plan_output)
            MockAgent.return_value = mock_agent_instance

            service = _make_service(
                session=session,
                context_repo=context_repo,
                issue_repo=issue_repo,
            )
            await service.execute(_make_payload())

            # Verify update_plan_content was called with merged content
            context_repo.update_plan_content.assert_awaited_once()
            call_kwargs = context_repo.update_plan_content.call_args[1]

            assert call_kwargs["issue_id"] == ISSUE_ID
            new_content = call_kwargs["new_content"]

            # Existing keys preserved
            assert new_content["summary"] == "Existing summary"
            assert new_content["complexity"] == "medium"
            # New key added
            assert new_content["implementation_plan"] == plan_md

            # Session committed
            session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_result_contains_correct_subagent_count(self) -> None:
        """GeneratePlanResult.subagent_count matches agent output."""
        ai_context = _make_ai_context()
        issue = _make_issue()

        context_repo = AsyncMock()
        context_repo.get_by_issue_id = AsyncMock(return_value=ai_context)
        context_repo.update_plan_content = AsyncMock(return_value=True)

        issue_repo = AsyncMock()
        issue_repo.get_by_id_with_relations = AsyncMock(return_value=issue)

        plan_output = _make_plan_output(subagent_count=5)

        with patch(
            "pilot_space.application.services.ai_context.generate_plan_service.PlanGenerationAgent"
        ) as MockAgent:
            mock_agent_instance = AsyncMock()
            mock_agent_instance.run = AsyncMock(return_value=plan_output)
            MockAgent.return_value = mock_agent_instance

            service = _make_service(
                context_repo=context_repo,
                issue_repo=issue_repo,
            )
            result = await service.execute(_make_payload())

            assert isinstance(result, GeneratePlanResult)
            assert result.subagent_count == 5
            assert result.context_id == CONTEXT_ID
            assert result.issue_id == ISSUE_ID
            assert isinstance(result.generated_at, datetime)

    @pytest.mark.asyncio
    async def test_raises_when_persist_fails(self) -> None:
        """ValueError raised when update_plan_content returns False."""
        ai_context = _make_ai_context()
        issue = _make_issue()

        context_repo = AsyncMock()
        context_repo.get_by_issue_id = AsyncMock(return_value=ai_context)
        context_repo.update_plan_content = AsyncMock(return_value=False)

        issue_repo = AsyncMock()
        issue_repo.get_by_id_with_relations = AsyncMock(return_value=issue)

        plan_output = _make_plan_output()

        with patch(
            "pilot_space.application.services.ai_context.generate_plan_service.PlanGenerationAgent"
        ) as MockAgent:
            mock_agent_instance = AsyncMock()
            mock_agent_instance.run = AsyncMock(return_value=plan_output)
            MockAgent.return_value = mock_agent_instance

            service = _make_service(
                context_repo=context_repo,
                issue_repo=issue_repo,
            )

            with pytest.raises(ValidationError, match="Failed to persist plan"):
                await service.execute(_make_payload())

    @pytest.mark.asyncio
    async def test_handles_none_content_on_context(self) -> None:
        """Service handles AIContext with content=None gracefully."""
        ai_context = _make_ai_context(content=None)
        # When content is None, context.content or {} -> {}
        ai_context.content = None
        issue = _make_issue()

        context_repo = AsyncMock()
        context_repo.get_by_issue_id = AsyncMock(return_value=ai_context)
        context_repo.update_plan_content = AsyncMock(return_value=True)

        issue_repo = AsyncMock()
        issue_repo.get_by_id_with_relations = AsyncMock(return_value=issue)

        plan_output = _make_plan_output(subagent_count=1)

        with patch(
            "pilot_space.application.services.ai_context.generate_plan_service.PlanGenerationAgent"
        ) as MockAgent:
            mock_agent_instance = AsyncMock()
            mock_agent_instance.run = AsyncMock(return_value=plan_output)
            MockAgent.return_value = mock_agent_instance

            service = _make_service(
                context_repo=context_repo,
                issue_repo=issue_repo,
            )
            result = await service.execute(_make_payload())

            assert result.subagent_count == 1

            # Verify content dict only has the plan key (no existing keys)
            call_kwargs = context_repo.update_plan_content.call_args[1]
            new_content = call_kwargs["new_content"]
            assert "implementation_plan" in new_content

    @pytest.mark.asyncio
    async def test_default_complexity_when_missing_from_content(self) -> None:
        """PlanInput.complexity defaults to 'medium' when not in content."""
        ai_context = _make_ai_context(content={"summary": "No complexity key"})
        issue = _make_issue()

        context_repo = AsyncMock()
        context_repo.get_by_issue_id = AsyncMock(return_value=ai_context)
        context_repo.update_plan_content = AsyncMock(return_value=True)

        issue_repo = AsyncMock()
        issue_repo.get_by_id_with_relations = AsyncMock(return_value=issue)

        plan_output = _make_plan_output()

        with patch(
            "pilot_space.application.services.ai_context.generate_plan_service.PlanGenerationAgent"
        ) as MockAgent:
            mock_agent_instance = AsyncMock()
            mock_agent_instance.run = AsyncMock(return_value=plan_output)
            MockAgent.return_value = mock_agent_instance

            service = _make_service(
                context_repo=context_repo,
                issue_repo=issue_repo,
            )
            await service.execute(_make_payload())

            call_args = mock_agent_instance.run.call_args
            plan_input: PlanInput = call_args[0][0]
            assert plan_input.complexity == "medium"
            assert plan_input.suggested_approach == ""
