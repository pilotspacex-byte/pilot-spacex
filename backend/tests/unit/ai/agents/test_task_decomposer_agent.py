"""Unit tests for TaskDecomposerAgent.

T083-T084: TaskDecomposerAgent tests.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from pilot_space.ai.agents.sdk_base import AgentContext
from pilot_space.ai.agents.task_decomposer_agent import (
    TaskDecomposerAgent,
    TaskDecomposerInput,
)


@pytest.fixture
def mock_infrastructure() -> dict:
    """Create mock infrastructure dependencies."""
    return {
        "tool_registry": MagicMock(),
        "provider_selector": MagicMock(),
        "cost_tracker": AsyncMock(),
        "resilient_executor": AsyncMock(),
    }


@pytest.fixture
def task_decomposer_agent(mock_infrastructure: dict) -> TaskDecomposerAgent:
    """Create TaskDecomposerAgent with mocked dependencies."""
    return TaskDecomposerAgent(**mock_infrastructure)


@pytest.fixture
def agent_context() -> AgentContext:
    """Create test agent context."""
    return AgentContext(
        workspace_id=uuid4(),
        user_id=uuid4(),
        metadata={"anthropic_api_key": "test-key"},
    )


class TestTaskDecomposerAgent:
    """Test suite for TaskDecomposerAgent."""

    def test_agent_initialization(
        self, task_decomposer_agent: TaskDecomposerAgent
    ) -> None:
        """Verify agent initializes with correct configuration."""
        assert task_decomposer_agent.AGENT_NAME == "task_decomposer"
        assert task_decomposer_agent.DEFAULT_MODEL == "claude-opus-4-5-20251101"
        assert task_decomposer_agent.MAX_TOKENS == 4096

    def test_build_prompt_basic(
        self, task_decomposer_agent: TaskDecomposerAgent
    ) -> None:
        """Verify prompt building with basic input."""
        input_data = TaskDecomposerInput(
            issue_id="PILOT-123",
            issue_title="Implement user authentication",
        )

        prompt = task_decomposer_agent._build_prompt(input_data)

        # issue_id is not shown in prompt, only title
        assert "Implement user authentication" in prompt
        assert "Maximum 10 subtasks" in prompt

    def test_build_prompt_with_description(
        self, task_decomposer_agent: TaskDecomposerAgent
    ) -> None:
        """Verify prompt building with description and context."""
        input_data = TaskDecomposerInput(
            issue_id="PILOT-456",
            issue_title="Add API endpoints",
            issue_description="Need REST API for user management",
            max_subtasks=5,
            include_dependencies=False,
            project_context="FastAPI backend service",
        )

        prompt = task_decomposer_agent._build_prompt(input_data)

        assert "Add API endpoints" in prompt
        assert "user management" in prompt
        assert "Maximum 5 subtasks" in prompt
        assert "dependencies: False" in prompt
        assert "FastAPI backend" in prompt

    def test_get_system_prompt(
        self, task_decomposer_agent: TaskDecomposerAgent
    ) -> None:
        """Verify system prompt content."""
        system_prompt = task_decomposer_agent._get_system_prompt()

        assert "project manager" in system_prompt.lower()
        assert "actionable" in system_prompt.lower()
        assert "dependencies" in system_prompt.lower()
        assert "JSON" in system_prompt

    def test_parse_response_valid_json(
        self, task_decomposer_agent: TaskDecomposerAgent
    ) -> None:
        """Verify response parsing with valid JSON."""
        json_response = """{
  "subtasks": [
    {
      "title": "Setup database",
      "description": "Configure PostgreSQL",
      "estimated_effort": "small",
      "dependencies": [],
      "labels": ["backend", "database"],
      "acceptance_criteria": ["DB connected", "Migrations run"]
    },
    {
      "title": "Create API endpoints",
      "description": "Build REST API",
      "estimated_effort": "medium",
      "dependencies": [0],
      "labels": ["backend", "api"],
      "acceptance_criteria": ["Tests pass"]
    }
  ],
  "total_effort": "medium",
  "recommended_order": [0, 1],
  "parallel_groups": []
}"""

        output = task_decomposer_agent._parse_response(json_response)

        assert len(output.subtasks) == 2
        assert output.subtasks[0].title == "Setup database"
        assert output.subtasks[0].estimated_effort == "small"
        assert output.subtasks[1].dependencies == [0]
        assert output.total_effort == "medium"
        assert output.recommended_order == [0, 1]

    def test_parse_response_markdown_wrapped(
        self, task_decomposer_agent: TaskDecomposerAgent
    ) -> None:
        """Verify parsing of JSON wrapped in markdown code block."""
        markdown_response = """Here's the breakdown:

```json
{
  "subtasks": [
    {
      "title": "Task 1",
      "description": "First task",
      "estimated_effort": "small",
      "dependencies": [],
      "labels": ["test"],
      "acceptance_criteria": ["Done"]
    }
  ],
  "total_effort": "small",
  "recommended_order": [0],
  "parallel_groups": [[0]]
}
```

This should work well."""

        output = task_decomposer_agent._parse_response(markdown_response)

        assert len(output.subtasks) == 1
        assert output.subtasks[0].title == "Task 1"

    def test_parse_response_invalid_json(
        self, task_decomposer_agent: TaskDecomposerAgent
    ) -> None:
        """Verify error handling for invalid JSON."""
        invalid_response = "This is not JSON at all"

        with pytest.raises(ValueError) as exc_info:
            task_decomposer_agent._parse_response(invalid_response)

        assert "JSON" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_requires_api_key(
        self,
        task_decomposer_agent: TaskDecomposerAgent,
    ) -> None:
        """Verify execution fails without API key."""
        input_data = TaskDecomposerInput(
            issue_id="TEST-1",
            issue_title="Test issue",
        )
        context = AgentContext(
            workspace_id=uuid4(),
            user_id=uuid4(),
            metadata={},  # No API key
        )

        with pytest.raises(Exception) as exc_info:
            await task_decomposer_agent.execute(input_data, context)

        assert "api key" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_execute_validates_input(
        self,
        task_decomposer_agent: TaskDecomposerAgent,
        agent_context: AgentContext,
    ) -> None:
        """Verify execution validates required fields."""
        input_data = TaskDecomposerInput(
            issue_id="TEST-1",
            issue_title="",  # Empty title
        )

        with pytest.raises(ValueError) as exc_info:
            await task_decomposer_agent.execute(input_data, agent_context)

        assert "required" in str(exc_info.value).lower()


__all__ = ["TestTaskDecomposerAgent"]
