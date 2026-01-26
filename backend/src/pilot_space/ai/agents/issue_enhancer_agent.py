"""Issue Enhancer Agent for AI-assisted issue creation.

T130: Create IssueEnhancerAgent for title/description enhancement and label suggestion.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from anthropic.types import TextBlock

from pilot_space.ai.agents.base import (
    AgentContext,
    AgentResult,
    BaseAgent,
    Provider,
    TaskType,
)
from pilot_space.ai.prompts.issue_enhancement import (
    build_enhancement_prompt,
    parse_enhancement_response,
)
from pilot_space.ai.telemetry import AIOperation

logger = logging.getLogger(__name__)


@dataclass
class IssueEnhancementInput:
    """Input for issue enhancement.

    Attributes:
        title: Original issue title.
        description: Original description (optional).
        project_context: Project name and description.
        available_labels: Labels available in the project.
        recent_issues: Recent similar issues for context.
    """

    title: str
    description: str | None = None
    project_context: str | None = None
    available_labels: list[str] | None = None
    recent_issues: list[dict[str, str]] | None = None


@dataclass
class IssueEnhancementOutput:
    """Output from issue enhancement.

    Attributes:
        enhanced_title: Improved title (or original if no improvement).
        enhanced_description: Expanded description.
        suggested_labels: Recommended labels with confidence.
        suggested_priority: Recommended priority with confidence.
        title_enhanced: Whether title was modified.
        description_expanded: Whether description was expanded.
    """

    enhanced_title: str
    enhanced_description: str | None
    suggested_labels: list[dict[str, str | float]]  # [{"name": "bug", "confidence": 0.9}]
    suggested_priority: dict[str, str | float] | None  # {"priority": "high", "confidence": 0.85}
    title_enhanced: bool
    description_expanded: bool


class IssueEnhancerAgent(BaseAgent[IssueEnhancementInput, IssueEnhancementOutput]):
    """Agent for enhancing issues with AI suggestions.

    Provides:
    - Title clarity improvement
    - Description expansion with structure
    - Label suggestions based on content
    - Priority recommendation

    Uses Claude for code-aware content analysis.
    """

    task_type = TaskType.CODE_ANALYSIS
    operation = AIOperation.CONTEXT_GENERATION

    async def _execute_impl(
        self,
        input_data: IssueEnhancementInput,
        context: AgentContext,
    ) -> AgentResult[IssueEnhancementOutput]:
        """Execute issue enhancement.

        Args:
            input_data: Issue content to enhance.
            context: Agent execution context.

        Returns:
            AgentResult with enhancement suggestions.
        """
        # Build prompt
        prompt = build_enhancement_prompt(
            title=input_data.title,
            description=input_data.description,
            project_context=input_data.project_context,
            available_labels=input_data.available_labels,
            recent_issues=input_data.recent_issues,
        )

        # Get API key
        api_key = context.require_api_key(Provider.CLAUDE)

        # Call Claude API
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)

        message = client.messages.create(
            model=self.model,
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        # Parse response - extract text from first TextBlock
        response_text = ""
        if message.content:
            first_block = message.content[0]
            if isinstance(first_block, TextBlock):
                response_text = first_block.text
        parsed_data = parse_enhancement_response(
            response_text,
            original_title=input_data.title,
            original_description=input_data.description,
        )

        # Construct output from parsed dict
        output = IssueEnhancementOutput(**parsed_data)

        return AgentResult(
            output=output,
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
            model=self.model,
            provider=self.provider,
        )

    def validate_input(self, input_data: IssueEnhancementInput) -> None:
        """Validate input data.

        Args:
            input_data: Input to validate.

        Raises:
            ValueError: If input is invalid.
        """
        if not input_data.title or not input_data.title.strip():
            raise ValueError("Issue title is required for enhancement")


__all__ = [
    "IssueEnhancementInput",
    "IssueEnhancementOutput",
    "IssueEnhancerAgent",
]
