"""Margin Annotation Agent using Claude Agent SDK.

Generates contextual annotations for note blocks displayed
in the right margin of the editor.

T067: SDK-based margin annotation agent.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

from pilot_space.ai.agents.sdk_base import AgentContext, SDKBaseAgent

if TYPE_CHECKING:
    from pilot_space.ai.infrastructure.cost_tracker import CostTracker
    from pilot_space.ai.infrastructure.resilience import ResilientExecutor
    from pilot_space.ai.providers.provider_selector import ProviderSelector
    from pilot_space.ai.tools.mcp_server import ToolRegistry


class AnnotationType(StrEnum):
    """Types of margin annotations."""

    SUGGESTION = "suggestion"  # Improvement suggestion
    WARNING = "warning"  # Potential issue
    QUESTION = "question"  # Clarification needed
    INSIGHT = "insight"  # Additional context
    REFERENCE = "reference"  # Related content link


@dataclass(frozen=True, slots=True)
class Annotation:
    """A margin annotation for a note block."""

    block_id: str
    type: AnnotationType
    title: str
    content: str
    confidence: float  # 0.0-1.0
    action_label: str | None = None  # e.g., "Apply", "Learn more"
    action_payload: dict[str, str] | None = None  # Action-specific data


@dataclass(frozen=True, slots=True)
class MarginAnnotationInput:
    """Input for margin annotation generation."""

    note_id: UUID
    block_ids: list[str]  # Specific blocks to annotate
    context_blocks: int = 3  # Surrounding context


@dataclass(frozen=True, slots=True)
class MarginAnnotationOutput:
    """Output from margin annotation generation."""

    annotations: list[Annotation]
    processed_blocks: int


class MarginAnnotationAgentSDK(
    SDKBaseAgent[MarginAnnotationInput, MarginAnnotationOutput]
):
    """Generates margin annotations for note blocks.

    Uses Claude Sonnet for quality suggestions without
    excessive latency.

    MCP Tools Used:
    - get_note_content: Retrieve block content
    - get_project_context: Understand conventions

    T067: SDK-based implementation.
    """

    AGENT_NAME = "margin_annotation"
    DEFAULT_MODEL = "claude-sonnet-4-20250514"
    MAX_TOKENS = 2048

    def __init__(
        self,
        tool_registry: ToolRegistry,
        provider_selector: ProviderSelector,
        cost_tracker: CostTracker,
        resilient_executor: ResilientExecutor,
    ) -> None:
        """Initialize margin annotation agent.

        Args:
            tool_registry: Registry for MCP tool access
            provider_selector: Provider/model selection service
            cost_tracker: Cost tracking service
            resilient_executor: Retry and circuit breaker service
        """
        super().__init__(
            tool_registry=tool_registry,
            provider_selector=provider_selector,
            cost_tracker=cost_tracker,
            resilient_executor=resilient_executor,
        )

    async def execute(
        self,
        input_data: MarginAnnotationInput,
        context: AgentContext,  # noqa: ARG002
    ) -> MarginAnnotationOutput:
        """Generate annotations for note blocks.

        Args:
            input_data: Annotation input with note_id and block_ids
            context: Execution context

        Returns:
            MarginAnnotationOutput with annotations list

        Raises:
            ValueError: If input validation fails
        """
        # Validate input
        if not input_data.block_ids:
            msg = "block_ids cannot be empty"
            raise ValueError(msg)

        if len(input_data.block_ids) > 20:
            msg = "Cannot annotate more than 20 blocks at once"
            raise ValueError(msg)

        # Build prompt
        prompt = self._build_prompt(input_data)
        system_prompt = self._get_system_prompt()

        # Call Claude Agent SDK
        # Note: Using direct anthropic call until SDK integration is complete
        # TODO: Replace with actual SDK query() call once available
        import anthropic

        api_key = await self._get_api_key()
        if not api_key:
            msg = "Anthropic API key not configured"
            raise ValueError(msg)

        client = anthropic.AsyncAnthropic(api_key=api_key)

        response = await client.messages.create(
            model=self.DEFAULT_MODEL,
            max_tokens=self.MAX_TOKENS,
            temperature=0.5,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )

        # Parse response
        return self._parse_response(response, input_data.block_ids)

    async def _get_api_key(self) -> str | None:
        """Get API key for Anthropic.

        Returns:
            API key or None if not configured
        """
        # TODO: Implement key retrieval from key_storage via orchestrator
        # For now, return environment variable
        import os

        return os.getenv("ANTHROPIC_API_KEY")

    def _get_system_prompt(self) -> str:
        """Get system prompt for margin annotations.

        Returns:
            System prompt string
        """
        return """You are an expert technical writing assistant that provides
helpful annotations for note content.

For each block, analyze and provide annotations of these types:
- SUGGESTION: Improvements to clarity, structure, or completeness
- WARNING: Potential issues, inconsistencies, or errors
- QUESTION: Areas needing clarification or decision
- INSIGHT: Relevant context, patterns, or connections
- REFERENCE: Links to related content or documentation

Output JSON array:
{
  "annotations": [
    {
      "block_id": "string",
      "type": "suggestion|warning|question|insight|reference",
      "title": "Short title (5-10 words)",
      "content": "Detailed annotation content",
      "confidence": 0.0-1.0,
      "action_label": "Optional action button text",
      "action_payload": {}
    }
  ]
}

Focus on actionable, specific annotations. Avoid generic advice."""

    def _build_prompt(self, input_data: MarginAnnotationInput) -> str:
        """Build user prompt for annotation request.

        Args:
            input_data: Annotation input

        Returns:
            User prompt string
        """
        return f"""Generate annotations for the specified blocks in this note.

Note ID: {input_data.note_id}
Block IDs to annotate: {input_data.block_ids}
Context blocks: {input_data.context_blocks}

Steps:
1. Use get_note_content to read the note
2. Use get_project_context to understand conventions
3. Analyze each specified block
4. Generate relevant annotations

Return JSON with annotations array."""

    def _parse_response(
        self,
        response: object,
        block_ids: list[str],
    ) -> MarginAnnotationOutput:
        """Parse SDK response into structured output.

        Args:
            response: Response from Anthropic API
            block_ids: Block IDs that were processed

        Returns:
            MarginAnnotationOutput with parsed annotations
        """
        # Extract content from Anthropic response
        import anthropic

        if isinstance(response, anthropic.types.Message):
            # Extract text from content blocks
            content = ""
            for block in response.content:
                if block.type == "text":
                    content += block.text
        elif isinstance(response, str):
            content = response
        else:
            content = str(response)

        # Try to parse JSON
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code block
            json_match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
            data = (
                json.loads(json_match.group(1))
                if json_match
                else {"annotations": []}
            )

        # Parse annotations
        annotations: list[Annotation] = []
        for annotation_dict in data.get("annotations", []):
            try:
                annotations.append(
                    Annotation(
                        block_id=annotation_dict["block_id"],
                        type=AnnotationType(annotation_dict["type"]),
                        title=annotation_dict["title"],
                        content=annotation_dict["content"],
                        confidence=annotation_dict.get("confidence", 0.7),
                        action_label=annotation_dict.get("action_label"),
                        action_payload=annotation_dict.get("action_payload"),
                    )
                )
            except (KeyError, ValueError) as e:
                # Skip malformed annotations
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"Skipping malformed annotation: {e}")
                continue

        return MarginAnnotationOutput(
            annotations=annotations,
            processed_blocks=len(block_ids),
        )


__all__ = [
    "Annotation",
    "AnnotationType",
    "MarginAnnotationAgentSDK",
    "MarginAnnotationInput",
    "MarginAnnotationOutput",
]
