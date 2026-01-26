"""Task Decomposer Agent using Claude Agent SDK.

Decomposes complex issues into manageable subtasks with dependencies.
Uses Claude Opus for strong reasoning capabilities.

T083-T084: TaskDecomposerAgent implementation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from anthropic import Anthropic

from pilot_space.ai.agents.sdk_base import AgentContext, SDKBaseAgent
from pilot_space.ai.exceptions import AIConfigurationError

if TYPE_CHECKING:
    from pilot_space.ai.infrastructure.cost_tracker import CostTracker
    from pilot_space.ai.infrastructure.resilience import ResilientExecutor
    from pilot_space.ai.providers.provider_selector import ProviderSelector
    from pilot_space.ai.tools.mcp_server import ToolRegistry


@dataclass(frozen=True, slots=True, kw_only=True)
class SubTask:
    """A decomposed sub-task.

    Attributes:
        title: Sub-task title.
        description: Detailed description.
        estimated_effort: Size estimate (small, medium, large).
        dependencies: Indices of dependent tasks in the list.
        labels: Suggested labels for this sub-task.
        acceptance_criteria: List of completion criteria.
    """

    title: str
    description: str
    estimated_effort: str
    dependencies: list[int]
    labels: list[str]
    acceptance_criteria: list[str]


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskDecomposerInput:
    """Input for task decomposition.

    Attributes:
        issue_id: Issue ID to decompose.
        issue_title: Issue title for context.
        issue_description: Issue description.
        max_subtasks: Maximum number of subtasks to generate.
        include_dependencies: Whether to analyze dependencies.
        project_context: Additional project context.
    """

    issue_id: str
    issue_title: str
    issue_description: str | None = None
    max_subtasks: int = 10
    include_dependencies: bool = True
    project_context: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskDecomposerOutput:
    """Decomposed tasks output.

    Attributes:
        subtasks: List of subtasks.
        total_effort: Aggregate effort estimate.
        recommended_order: Suggested execution order (task indices).
        parallel_groups: Tasks that can be done in parallel.
    """

    subtasks: list[SubTask]
    total_effort: str
    recommended_order: list[int]
    parallel_groups: list[list[int]]


class TaskDecomposerAgent(SDKBaseAgent[TaskDecomposerInput, TaskDecomposerOutput]):
    """Decomposes complex issues into actionable subtasks.

    Uses Claude Opus for strong reasoning about task breakdown
    and dependency analysis.

    Attributes:
        AGENT_NAME: Unique identifier for this agent.
        DEFAULT_MODEL: Claude Opus 4.5 for complex reasoning.
        MAX_TOKENS: 4096 for detailed breakdowns.
    """

    AGENT_NAME = "task_decomposer"
    DEFAULT_MODEL = "claude-opus-4-5-20251101"
    MAX_TOKENS = 4096

    def __init__(
        self,
        tool_registry: ToolRegistry,
        provider_selector: ProviderSelector,
        cost_tracker: CostTracker,
        resilient_executor: ResilientExecutor,
    ) -> None:
        """Initialize task decomposer agent.

        Args:
            tool_registry: Registry for MCP tools.
            provider_selector: Provider selection service.
            cost_tracker: Cost tracking service.
            resilient_executor: Resilience service.
        """
        super().__init__(
            tool_registry=tool_registry,
            provider_selector=provider_selector,
            cost_tracker=cost_tracker,
            resilient_executor=resilient_executor,
        )

    async def execute(
        self,
        input_data: TaskDecomposerInput,
        context: AgentContext,
    ) -> TaskDecomposerOutput:
        """Execute task decomposition.

        Args:
            input_data: Issue to decompose.
            context: Execution context.

        Returns:
            Decomposed tasks with dependencies.

        Raises:
            AIConfigurationError: If Anthropic API key not configured.
        """
        # Validate input
        if not input_data.issue_title:
            raise ValueError("issue_title is required")

        # Get API key
        api_key = context.metadata.get("anthropic_api_key")
        if not api_key:
            raise AIConfigurationError(
                "Anthropic API key not configured",
                provider="anthropic",
                missing_fields=["api_key"],
            )

        # Build prompt
        prompt = self._build_prompt(input_data)
        system_prompt = self._get_system_prompt()

        # Call Anthropic API
        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model=self.DEFAULT_MODEL,
            max_tokens=self.MAX_TOKENS,
            temperature=0.3,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        # Track usage
        await self.track_usage(
            context=context,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

        # Parse response
        content = ""
        for block in response.content:
            if block.type == "text":
                content = block.text
                break

        return self._parse_response(content)

    def _build_prompt(self, input_data: TaskDecomposerInput) -> str:
        """Build decomposition prompt.

        Args:
            input_data: Input parameters.

        Returns:
            Formatted prompt.
        """
        prompt = f"""Decompose this issue into actionable subtasks.

Issue: {input_data.issue_title}
"""

        if input_data.issue_description:
            prompt += f"\nDescription:\n{input_data.issue_description}\n"

        if input_data.project_context:
            prompt += f"\nProject Context:\n{input_data.project_context}\n"

        prompt += f"""
Requirements:
- Maximum {input_data.max_subtasks} subtasks
- Each subtask should be independently completable
- Include dependencies: {input_data.include_dependencies}
- Estimate effort (small/medium/large)
- Suggest labels for each subtask
- Provide acceptance criteria

Output JSON format:
{{
  "subtasks": [
    {{
      "title": "...",
      "description": "...",
      "estimated_effort": "small|medium|large",
      "dependencies": [0, 1],
      "labels": ["backend", "api"],
      "acceptance_criteria": ["...", "..."]
    }}
  ],
  "total_effort": "medium",
  "recommended_order": [0, 1, 2],
  "parallel_groups": [[0, 1], [2, 3]]
}}
"""

        return prompt

    def _get_system_prompt(self) -> str:
        """Get system prompt for task decomposition.

        Returns:
            System prompt string.
        """
        return """You are an expert software project manager and systems analyst.

Your task is to break down complex issues into actionable subtasks that:
1. Can be independently completed and tested
2. Have clear acceptance criteria
3. Identify dependencies between tasks
4. Provide realistic effort estimates
5. Suggest appropriate labels for categorization

Think step-by-step:
1. Understand the overall goal
2. Identify logical components
3. Determine dependencies
4. Estimate complexity
5. Define success criteria

Be practical and specific. Each subtask should be clear enough
for a developer to start working immediately.

Always respond with valid JSON matching the requested format."""

    def _parse_response(self, content: str) -> TaskDecomposerOutput:
        """Parse decomposition response.

        Args:
            content: Generated JSON content.

        Returns:
            Parsed output.

        Raises:
            ValueError: If response format is invalid.
        """
        # Extract JSON from response (may be wrapped in markdown)
        json_str = content
        if "```json" in content:
            # Extract from markdown code block
            start = content.find("```json") + 7
            end = content.find("```", start)
            json_str = content[start:end].strip()
        elif "```" in content:
            # Generic code block
            start = content.find("```") + 3
            end = content.find("```", start)
            json_str = content[start:end].strip()

        try:
            data: dict[str, Any] = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse response as JSON: {e}") from e

        # Parse subtasks
        subtasks = []
        for task_data in data.get("subtasks", []):
            subtasks.append(
                SubTask(
                    title=task_data.get("title", ""),
                    description=task_data.get("description", ""),
                    estimated_effort=task_data.get("estimated_effort", "medium"),
                    dependencies=task_data.get("dependencies", []),
                    labels=task_data.get("labels", []),
                    acceptance_criteria=task_data.get("acceptance_criteria", []),
                )
            )

        return TaskDecomposerOutput(
            subtasks=subtasks,
            total_effort=data.get("total_effort", "medium"),
            recommended_order=data.get("recommended_order", []),
            parallel_groups=data.get("parallel_groups", []),
        )


__all__ = [
    "SubTask",
    "TaskDecomposerAgent",
    "TaskDecomposerInput",
    "TaskDecomposerOutput",
]
