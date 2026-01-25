"""Margin annotation agent for AI-powered suggestions.

Uses Claude Sonnet for quality analysis of note content.
Provides contextual suggestions in the right margin.

T085: MarginAnnotationAgent implementation.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

import anthropic

from pilot_space.ai.agents.base import (
    AgentContext,
    AgentResult,
    BaseAgent,
    Provider,
    TaskType,
)
from pilot_space.ai.exceptions import (
    AIConfigurationError,
    RateLimitError,
)
from pilot_space.ai.prompts.margin_annotation import (
    AnnotationType,
    MarginAnnotationPromptConfig,
    build_batch_annotation_prompt,
    build_margin_annotation_prompt,
)
from pilot_space.ai.telemetry import AIOperation
from pilot_space.ai.utils.retry import RetryConfig

logger = logging.getLogger(__name__)


@dataclass
class AnnotationSuggestion:
    """A single annotation suggestion.

    Attributes:
        type: Type of annotation.
        block_id: Block this annotation relates to.
        content: The suggestion content.
        confidence: Confidence score 0.0-1.0.
        highlight_start: Start position of highlight.
        highlight_end: End position of highlight.
    """

    type: AnnotationType
    block_id: str
    content: str
    confidence: float
    highlight_start: int | None = None
    highlight_end: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {
            "type": self.type.value,
            "block_id": self.block_id,
            "content": self.content,
            "confidence": self.confidence,
        }
        if self.highlight_start is not None:
            result["highlight_start"] = self.highlight_start
        if self.highlight_end is not None:
            result["highlight_end"] = self.highlight_end
        return result


@dataclass
class MarginAnnotationInput:
    """Input for margin annotation generation.

    Attributes:
        note_title: Title of the note.
        blocks: Note content as list of blocks with 'id' and 'content'.
        workspace_context: Optional workspace/project description.
    """

    note_title: str
    blocks: list[dict[str, str]]
    workspace_context: str | None = None


@dataclass
class MarginAnnotationOutput:
    """Output from margin annotation generation.

    Attributes:
        annotations: List of annotation suggestions.
        block_count: Number of blocks processed.
    """

    annotations: list[AnnotationSuggestion] = field(default_factory=list)  # pyright: ignore[reportUnknownVariableType]
    block_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "annotations": [a.to_dict() for a in self.annotations],
            "block_count": self.block_count,
        }


class MarginAnnotationAgent(BaseAgent[MarginAnnotationInput, MarginAnnotationOutput]):
    """Agent for generating margin annotations.

    Uses Claude Sonnet for quality analysis.
    Supports batch processing for multiple blocks.

    Attributes:
        task_type: CODE_ANALYSIS for Claude routing.
        operation: MARGIN_ANNOTATION for telemetry.
        min_confidence: Minimum confidence to include.
    """

    task_type = TaskType.CODE_ANALYSIS
    operation = AIOperation.MARGIN_ANNOTATION
    retry_config = RetryConfig(max_retries=2, initial_delay_seconds=1.0)

    DEFAULT_MODEL = "claude-sonnet-4-20250514"
    MIN_CONFIDENCE = 0.5

    def __init__(
        self,
        model: str | None = None,
        min_confidence: float = 0.5,
    ) -> None:
        """Initialize margin annotation agent.

        Args:
            model: Override default Claude model.
            min_confidence: Minimum confidence threshold.
        """
        super().__init__(model or self.DEFAULT_MODEL)
        self.min_confidence = min_confidence
        self._prompt_config = MarginAnnotationPromptConfig(
            min_confidence_threshold=min_confidence,
        )

    def validate_input(self, input_data: MarginAnnotationInput) -> None:
        """Validate input before processing.

        Args:
            input_data: The input to validate.

        Raises:
            ValueError: If input is invalid.
        """
        if not input_data.note_title:
            raise ValueError("note_title cannot be empty")

        if not input_data.blocks:
            raise ValueError("blocks cannot be empty")

        for block in input_data.blocks:
            if "id" not in block or "content" not in block:
                raise ValueError("Each block must have 'id' and 'content' keys")

    async def _execute_impl(
        self,
        input_data: MarginAnnotationInput,
        context: AgentContext,
    ) -> AgentResult[MarginAnnotationOutput]:
        """Execute margin annotation generation.

        Args:
            input_data: Annotation input.
            context: Agent execution context.

        Returns:
            AgentResult with annotations.
        """
        self.validate_input(input_data)

        # Get API key for Claude
        api_key = context.get_api_key(Provider.CLAUDE)
        if not api_key:
            raise AIConfigurationError(
                "Anthropic API key not configured for margin annotations",
                provider="anthropic",
                missing_fields=["api_key"],
            )

        # Build prompts
        system_prompt, user_prompt = build_margin_annotation_prompt(
            note_title=input_data.note_title,
            blocks=input_data.blocks,
            workspace_context=input_data.workspace_context,
            config=self._prompt_config,
        )

        # Call Claude
        try:
            client = anthropic.AsyncAnthropic(api_key=api_key)

            response = await client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt},
                ],
            )

            # Parse response
            annotations = self._parse_annotations(response)

            return AgentResult(
                output=MarginAnnotationOutput(
                    annotations=annotations,
                    block_count=len(input_data.blocks),
                ),
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                model=self.model,
                provider=Provider.CLAUDE,
            )

        except anthropic.RateLimitError as e:
            raise RateLimitError(
                "Anthropic rate limit exceeded",
                retry_after_seconds=60,
                provider="anthropic",
            ) from e

        except anthropic.APIError as e:
            logger.exception(
                "Anthropic API error in margin annotation",
                extra={
                    "error": str(e),
                    "correlation_id": context.correlation_id,
                },
            )
            raise

    def _parse_annotations(
        self,
        response: anthropic.types.Message,
    ) -> list[AnnotationSuggestion]:
        """Parse annotations from Claude response.

        Args:
            response: Claude API response.

        Returns:
            List of annotation suggestions.
        """
        # Extract text content
        text_content = ""
        for block in response.content:
            if block.type == "text":
                text_content = block.text
                break

        if not text_content:
            return []

        # Try to parse as JSON
        try:
            # Find JSON array in response
            start_idx = text_content.find("[")
            end_idx = text_content.rfind("]") + 1

            if start_idx == -1 or end_idx == 0:
                logger.warning("No JSON array found in margin annotation response")
                return []

            json_str = text_content[start_idx:end_idx]
            raw_annotations = json.loads(json_str)

            if not isinstance(raw_annotations, list):
                logger.warning("Margin annotation response is not an array")
                return []

            # Convert to AnnotationSuggestion objects
            annotations: list[AnnotationSuggestion] = []
            for raw_item in raw_annotations:  # pyright: ignore[reportUnknownVariableType]
                if not isinstance(raw_item, dict):
                    continue
                raw: dict[str, Any] = raw_item  # pyright: ignore[reportUnknownVariableType]
                try:
                    type_value = raw.get("type", "clarification")
                    annotation_type = AnnotationType(str(type_value))
                    conf_value = raw.get("confidence", 0.5)
                    confidence = float(conf_value) if conf_value is not None else 0.5

                    # Filter by confidence threshold
                    if confidence < self.min_confidence:
                        continue

                    block_id_val = raw.get("block_id", "")
                    content_val = raw.get("content", "")
                    highlight_start_val = raw.get("highlight_start")
                    highlight_end_val = raw.get("highlight_end")

                    annotations.append(
                        AnnotationSuggestion(
                            type=annotation_type,
                            block_id=str(block_id_val) if block_id_val else "",
                            content=str(content_val) if content_val else "",
                            confidence=confidence,
                            highlight_start=int(highlight_start_val)
                            if highlight_start_val is not None
                            else None,
                            highlight_end=int(highlight_end_val)
                            if highlight_end_val is not None
                            else None,
                        )
                    )
                except (ValueError, KeyError) as e:
                    logger.warning(f"Failed to parse annotation: {e}")
                    continue

            return annotations

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse margin annotation JSON: {e}")
            return []


class BatchMarginAnnotationAgent(MarginAnnotationAgent):
    """Agent for batch processing multiple blocks.

    More efficient when analyzing many blocks at once.
    """

    async def annotate_batch(
        self,
        blocks: list[dict[str, str]],
        context: AgentContext,
    ) -> dict[str, list[AnnotationSuggestion]]:
        """Process multiple blocks and return annotations by block.

        Args:
            blocks: List of blocks to annotate.
            context: Agent execution context.

        Returns:
            Dictionary mapping block IDs to their annotations.
        """
        api_key = context.get_api_key(Provider.CLAUDE)
        if not api_key:
            raise AIConfigurationError(
                "Anthropic API key not configured",
                provider="anthropic",
            )

        # Build batch prompt
        system_prompt, user_prompt = build_batch_annotation_prompt(blocks)

        try:
            client = anthropic.AsyncAnthropic(api_key=api_key)

            response = await client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt},
                ],
            )

            return self._parse_batch_annotations(response)

        except anthropic.RateLimitError as e:
            raise RateLimitError(
                "Anthropic rate limit exceeded",
                provider="anthropic",
            ) from e

    def _parse_batch_annotations(
        self,
        response: anthropic.types.Message,
    ) -> dict[str, list[AnnotationSuggestion]]:
        """Parse batch annotations from response.

        Args:
            response: Claude API response.

        Returns:
            Dictionary mapping block IDs to annotations.
        """
        # Extract text content
        text_content = ""
        for block in response.content:
            if block.type == "text":
                text_content = block.text
                break

        if not text_content:
            return {}

        try:
            # Find JSON object in response
            start_idx = text_content.find("{")
            end_idx = text_content.rfind("}") + 1

            if start_idx == -1 or end_idx == 0:
                return {}

            json_str = text_content[start_idx:end_idx]
            raw_result = json.loads(json_str)

            if not isinstance(raw_result, dict):
                return {}

            # Convert to structured result
            result: dict[str, list[AnnotationSuggestion]] = {}
            raw_dict: dict[str, Any] = raw_result  # pyright: ignore[reportUnknownVariableType]

            for block_id_key, annotations_value in raw_dict.items():
                block_id = str(block_id_key)
                if not isinstance(annotations_value, list):
                    continue

                block_annotations: list[AnnotationSuggestion] = []
                for raw_item in annotations_value:  # pyright: ignore[reportUnknownVariableType]
                    if not isinstance(raw_item, dict):
                        continue
                    raw: dict[str, Any] = raw_item  # pyright: ignore[reportUnknownVariableType]
                    try:
                        type_value = raw.get("type", "clarification")
                        annotation_type = AnnotationType(str(type_value))
                        conf_value = raw.get("confidence", 0.5)
                        confidence = float(conf_value) if conf_value is not None else 0.5

                        if confidence < self.min_confidence:
                            continue

                        content_val = raw.get("content", "")
                        block_annotations.append(
                            AnnotationSuggestion(
                                type=annotation_type,
                                block_id=block_id,
                                content=str(content_val) if content_val else "",
                                confidence=confidence,
                            )
                        )
                    except (ValueError, KeyError):
                        continue

                result[block_id] = block_annotations

            return result

        except json.JSONDecodeError:
            return {}


__all__ = [
    "AnnotationSuggestion",
    "BatchMarginAnnotationAgent",
    "MarginAnnotationAgent",
    "MarginAnnotationInput",
    "MarginAnnotationOutput",
]
