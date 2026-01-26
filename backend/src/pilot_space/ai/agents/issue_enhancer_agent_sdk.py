"""Issue Enhancer Agent SDK for AI-assisted issue creation.

Migrated from legacy BaseAgent to SDKBaseAgent pattern.
Uses Claude Agent SDK infrastructure for telemetry, cost tracking, and resilience.

T130: Create IssueEnhancerAgent for title/description enhancement and label suggestion.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from anthropic import AsyncAnthropic
from anthropic.types import TextBlock

from pilot_space.ai.agents.sdk_base import (
    AgentContext,
    SDKBaseAgent,
)
from pilot_space.ai.prompts.issue_enhancement import (
    build_enhancement_prompt,
    parse_enhancement_response,
)

if TYPE_CHECKING:
    from pilot_space.ai.infrastructure.cost_tracker import CostTracker
    from pilot_space.ai.infrastructure.key_storage import SecureKeyStorage
    from pilot_space.ai.infrastructure.resilience import ResilientExecutor
    from pilot_space.ai.providers.provider_selector import ProviderSelector
    from pilot_space.ai.tools.mcp_server import ToolRegistry

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


class IssueEnhancerAgent(SDKBaseAgent[IssueEnhancementInput, IssueEnhancementOutput]):
    """Agent for enhancing issues with AI suggestions.

    Provides:
    - Title clarity improvement
    - Description expansion with structure
    - Label suggestions based on content
    - Priority recommendation

    Uses Claude for code-aware content analysis.

    Architecture:
    - Extends SDKBaseAgent for SDK infrastructure
    - Uses AsyncAnthropic client for API calls
    - Tracks costs with cost_tracker
    - Retrieves API keys from key_storage
    """

    AGENT_NAME = "issue_enhancer"
    DEFAULT_MODEL = "claude-sonnet-4-20250514"

    def __init__(
        self,
        tool_registry: ToolRegistry,
        provider_selector: ProviderSelector,
        cost_tracker: CostTracker,
        resilient_executor: ResilientExecutor,
        key_storage: SecureKeyStorage,
    ) -> None:
        """Initialize issue enhancer agent.

        Args:
            tool_registry: Registry for MCP tool access
            provider_selector: Provider/model selection service
            cost_tracker: Cost tracking service
            resilient_executor: Retry and circuit breaker service
            key_storage: Secure API key storage service
        """
        super().__init__(
            tool_registry=tool_registry,
            provider_selector=provider_selector,
            cost_tracker=cost_tracker,
            resilient_executor=resilient_executor,
        )
        self._key_storage = key_storage

    def get_model(self) -> tuple[str, str]:
        """Get provider and model for issue enhancement.

        Returns:
            Tuple of ("anthropic", "claude-sonnet-4-20250514")
        """
        return ("anthropic", self.DEFAULT_MODEL)

    def _validate_input(self, input_data: IssueEnhancementInput) -> None:
        """Validate input data.

        Args:
            input_data: Input to validate.

        Raises:
            ValueError: If input is invalid.
        """
        if not input_data.title or not input_data.title.strip():
            raise ValueError("Issue title is required for enhancement")

    async def execute(
        self,
        input_data: IssueEnhancementInput,
        context: AgentContext,
    ) -> IssueEnhancementOutput:
        """Execute issue enhancement.

        Args:
            input_data: Issue content to enhance.
            context: Agent execution context.

        Returns:
            IssueEnhancementOutput with enhancement suggestions.

        Raises:
            ValueError: If input validation fails or API key is missing.
            Exception: If API call fails.
        """
        # Validate input
        self._validate_input(input_data)

        # Build prompt
        prompt = build_enhancement_prompt(
            title=input_data.title,
            description=input_data.description,
            project_context=input_data.project_context,
            available_labels=input_data.available_labels,
            recent_issues=input_data.recent_issues,
        )

        # Get API key from secure storage
        api_key = await self._key_storage.get_api_key(
            workspace_id=context.workspace_id,
            provider="anthropic",
        )

        if not api_key:
            raise ValueError(
                f"No Anthropic API key configured for workspace {context.workspace_id}"
            )

        # Call Claude API
        client = AsyncAnthropic(api_key=api_key)

        message = await client.messages.create(
            model=self.DEFAULT_MODEL,
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

        # Track usage
        await self.track_usage(
            context=context,
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
        )

        logger.info(
            "Issue enhancement completed",
            extra={
                "workspace_id": str(context.workspace_id),
                "user_id": str(context.user_id),
                "title_enhanced": output.title_enhanced,
                "description_expanded": output.description_expanded,
                "label_count": len(output.suggested_labels),
                "input_tokens": message.usage.input_tokens,
                "output_tokens": message.usage.output_tokens,
            },
        )

        return output


__all__ = [
    "IssueEnhancementInput",
    "IssueEnhancementOutput",
    "IssueEnhancerAgent",
]
