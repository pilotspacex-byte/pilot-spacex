"""Issue extractor agent for note-to-issue conversion.

Uses Claude Sonnet to extract structured issues from note content.
Supports confidence scoring and issue categorization.

T086: IssueExtractorAgent implementation.
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
from pilot_space.ai.prompts.issue_extraction import (
    ConfidenceTag,
    IssueExtractionPromptConfig,
    IssuePriority,
    build_issue_extraction_prompt,
    get_confidence_tag,
)
from pilot_space.ai.telemetry import AIOperation
from pilot_space.ai.utils.retry import RetryConfig

logger = logging.getLogger(__name__)


@dataclass
class ExtractedIssue:
    """A single extracted issue.

    Attributes:
        title: Issue title.
        description: Issue description.
        priority: Suggested priority.
        labels: Suggested labels.
        confidence: Confidence score 0.0-1.0.
        confidence_tag: Confidence category.
        source_block_ids: Blocks this was extracted from.
        source_text: Original text.
    """

    title: str
    description: str
    priority: IssuePriority
    labels: list[str]
    confidence: float
    confidence_tag: ConfidenceTag
    source_block_ids: list[str] = field(default_factory=list)  # pyright: ignore[reportUnknownVariableType]
    source_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value,
            "labels": self.labels,
            "confidence": self.confidence,
            "confidence_tag": self.confidence_tag.value,
            "source_block_ids": self.source_block_ids,
            "source_text": self.source_text,
        }


@dataclass
class IssueExtractionInput:
    """Input for issue extraction.

    Attributes:
        note_title: Title of the note.
        note_content: Full note content.
        project_context: Optional project description.
        selected_text: Optional user-selected text to focus on.
        available_labels: Labels available in the project.
    """

    note_title: str
    note_content: str
    project_context: str | None = None
    selected_text: str | None = None
    available_labels: list[str] | None = None


@dataclass
class IssueExtractionOutput:
    """Output from issue extraction.

    Attributes:
        issues: List of extracted issues.
        recommended_count: Count of recommended issues.
        total_count: Total count of extracted issues.
    """

    issues: list[ExtractedIssue] = field(default_factory=list)  # pyright: ignore[reportUnknownVariableType]

    @property
    def recommended_count(self) -> int:
        """Count of recommended issues."""
        return sum(1 for i in self.issues if i.confidence_tag == ConfidenceTag.RECOMMENDED)

    @property
    def total_count(self) -> int:
        """Total issue count."""
        return len(self.issues)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "issues": [i.to_dict() for i in self.issues],
            "recommended_count": self.recommended_count,
            "total_count": self.total_count,
        }

    def get_by_confidence(
        self,
        tag: ConfidenceTag,
    ) -> list[ExtractedIssue]:
        """Filter issues by confidence tag.

        Args:
            tag: Confidence tag to filter by.

        Returns:
            List of matching issues.
        """
        return [i for i in self.issues if i.confidence_tag == tag]


class IssueExtractorAgent(BaseAgent[IssueExtractionInput, IssueExtractionOutput]):
    """Agent for extracting issues from note content.

    Uses Claude Sonnet for quality extraction.
    Provides confidence scoring per DD-048.

    Attributes:
        task_type: CODE_ANALYSIS for Claude routing.
        operation: ISSUE_EXTRACTION for telemetry.
    """

    task_type = TaskType.CODE_ANALYSIS
    operation = AIOperation.ISSUE_EXTRACTION
    retry_config = RetryConfig(max_retries=2, initial_delay_seconds=1.0)

    DEFAULT_MODEL = "claude-sonnet-4-20250514"

    def __init__(
        self,
        model: str | None = None,
    ) -> None:
        """Initialize issue extractor agent.

        Args:
            model: Override default Claude model.
        """
        super().__init__(model or self.DEFAULT_MODEL)
        self._prompt_config = IssueExtractionPromptConfig()

    def validate_input(self, input_data: IssueExtractionInput) -> None:
        """Validate input before processing.

        Args:
            input_data: The input to validate.

        Raises:
            ValueError: If input is invalid.
        """
        if not input_data.note_title:
            raise ValueError("note_title cannot be empty")

        if not input_data.note_content:
            raise ValueError("note_content cannot be empty")

    async def _execute_impl(
        self,
        input_data: IssueExtractionInput,
        context: AgentContext,
    ) -> AgentResult[IssueExtractionOutput]:
        """Execute issue extraction.

        Args:
            input_data: Extraction input.
            context: Agent execution context.

        Returns:
            AgentResult with extracted issues.
        """
        self.validate_input(input_data)

        # Get API key for Claude
        api_key = context.get_api_key(Provider.CLAUDE)
        if not api_key:
            raise AIConfigurationError(
                "Anthropic API key not configured for issue extraction",
                provider="anthropic",
                missing_fields=["api_key"],
            )

        # Build prompts
        system_prompt, user_prompt = build_issue_extraction_prompt(
            note_title=input_data.note_title,
            note_content=input_data.note_content,
            project_context=input_data.project_context,
            selected_text=input_data.selected_text,
            available_labels=input_data.available_labels,
            config=self._prompt_config,
        )

        # Call Claude
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

            # Parse response
            issues = self._parse_issues(response)

            return AgentResult(
                output=IssueExtractionOutput(issues=issues),
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
                "Anthropic API error in issue extraction",
                extra={
                    "error": str(e),
                    "correlation_id": context.correlation_id,
                },
            )
            raise

    def _parse_issues(
        self,
        response: anthropic.types.Message,
    ) -> list[ExtractedIssue]:
        """Parse issues from Claude response.

        Args:
            response: Claude API response.

        Returns:
            List of extracted issues.
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
            # Find JSON object in response
            start_idx = text_content.find("{")
            end_idx = text_content.rfind("}") + 1

            if start_idx == -1 or end_idx == 0:
                logger.warning("No JSON object found in issue extraction response")
                return []

            json_str = text_content[start_idx:end_idx]
            raw_result = json.loads(json_str)

            if not isinstance(raw_result, dict):
                logger.warning("Issue extraction response is not an object")
                return []

            raw_dict: dict[str, Any] = raw_result  # pyright: ignore[reportUnknownVariableType]
            raw_issues_value = raw_dict.get("issues", [])
            if not isinstance(raw_issues_value, list):
                return []

            # Convert to ExtractedIssue objects
            issues: list[ExtractedIssue] = []
            for raw_item in raw_issues_value:  # pyright: ignore[reportUnknownVariableType]
                if not isinstance(raw_item, dict):
                    continue
                raw: dict[str, Any] = raw_item  # pyright: ignore[reportUnknownVariableType]
                try:
                    # Parse priority
                    priority_value = raw.get("priority", "medium")
                    priority_str = str(priority_value).lower() if priority_value else "medium"
                    try:
                        priority = IssuePriority(priority_str)
                    except ValueError:
                        priority = IssuePriority.MEDIUM

                    # Parse confidence
                    conf_value = raw.get("confidence", 0.5)
                    confidence = float(conf_value) if conf_value is not None else 0.5
                    confidence = max(0.0, min(1.0, confidence))  # Clamp to 0-1

                    # Determine confidence tag
                    confidence_tag_value = raw.get("confidence_tag")
                    confidence_tag_str = str(confidence_tag_value) if confidence_tag_value else None
                    if confidence_tag_str:
                        try:
                            confidence_tag = ConfidenceTag(confidence_tag_str)
                        except ValueError:
                            confidence_tag = get_confidence_tag(confidence)
                    else:
                        confidence_tag = get_confidence_tag(confidence)

                    # Parse labels
                    labels_value = raw.get("labels", [])
                    labels_list: list[str] = []
                    if isinstance(labels_value, str):
                        labels_list = [labels_value]
                    elif isinstance(labels_value, list):
                        labels_list = [str(item) for item in labels_value]  # pyright: ignore[reportUnknownVariableType,reportUnknownArgumentType]

                    # Parse source block IDs
                    source_ids_value = raw.get("source_block_ids", [])
                    source_ids: list[str] = []
                    if isinstance(source_ids_value, str):
                        source_ids = [source_ids_value]
                    elif isinstance(source_ids_value, list):
                        source_ids = [str(item) for item in source_ids_value]  # pyright: ignore[reportUnknownVariableType,reportUnknownArgumentType]

                    title_value = raw.get("title", "Untitled Issue")
                    desc_value = raw.get("description", "")
                    source_text_value = raw.get("source_text", "")

                    issues.append(
                        ExtractedIssue(
                            title=str(title_value) if title_value else "Untitled Issue",
                            description=str(desc_value) if desc_value else "",
                            priority=priority,
                            labels=labels_list,
                            confidence=confidence,
                            confidence_tag=confidence_tag,
                            source_block_ids=source_ids,
                            source_text=str(source_text_value) if source_text_value else "",
                        )
                    )
                except (ValueError, KeyError) as e:
                    logger.warning(f"Failed to parse extracted issue: {e}")
                    continue

            # Sort by confidence (highest first)
            issues.sort(key=lambda x: x.confidence, reverse=True)

            return issues

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse issue extraction JSON: {e}")
            return []


class QuickIssueExtractor:
    """Helper for quick single-issue extraction from selected text.

    Simpler interface for extracting one issue from a text selection.
    """

    def __init__(self, agent: IssueExtractorAgent | None = None) -> None:
        """Initialize quick extractor.

        Args:
            agent: Optional pre-configured agent.
        """
        self._agent = agent or IssueExtractorAgent()

    async def extract_from_selection(
        self,
        selected_text: str,
        note_title: str,
        context: AgentContext,
        available_labels: list[str] | None = None,
    ) -> ExtractedIssue | None:
        """Extract a single issue from selected text.

        Args:
            selected_text: User-selected text.
            note_title: Title of the note.
            context: Agent context.
            available_labels: Available labels.

        Returns:
            Extracted issue or None.
        """
        input_data = IssueExtractionInput(
            note_title=note_title,
            note_content=selected_text,
            selected_text=selected_text,
            available_labels=available_labels,
        )

        result = await self._agent.execute(input_data, context)

        if result.output.issues:
            return result.output.issues[0]

        return None


__all__ = [
    "ExtractedIssue",
    "IssueExtractionInput",
    "IssueExtractionOutput",
    "IssueExtractorAgent",
    "QuickIssueExtractor",
]
