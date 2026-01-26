"""Issue Extractor Agent using Claude Agent SDK.

Extracts actionable issues from note content with confidence tags
per DD-048 (Recommended/Default/Current/Alternative).

Reference: docs/architect/claude-agent-sdk-architecture.md
T056: IssueExtractorAgent SDK migration.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from uuid import UUID

from anthropic import AsyncAnthropic

from pilot_space.ai.agents.sdk_base import AgentContext, SDKBaseAgent
from pilot_space.ai.prompts.issue_extraction import (
    ConfidenceTag,
    get_confidence_tag,
)

if TYPE_CHECKING:
    from pilot_space.ai.infrastructure.cost_tracker import CostTracker
    from pilot_space.ai.infrastructure.key_storage import SecureKeyStorage
    from pilot_space.ai.infrastructure.resilience import ResilientExecutor
    from pilot_space.ai.providers.provider_selector import ProviderSelector
    from pilot_space.ai.tools.mcp_server import ToolRegistry

logger = logging.getLogger(__name__)


@dataclass
class ExtractedIssue:
    """An issue extracted from note content."""

    title: str
    description: str
    labels: list[str]
    priority: int  # 0-4 (urgent to no priority)
    confidence_tag: ConfidenceTag
    confidence_score: float  # 0.0-1.0
    source_block_ids: list[str]  # Note blocks this came from
    rationale: str  # Why this issue was extracted

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "description": self.description,
            "labels": self.labels,
            "priority": self.priority,
            "confidence_tag": self.confidence_tag.value,
            "confidence_score": self.confidence_score,
            "source_block_ids": self.source_block_ids,
            "rationale": self.rationale,
        }


@dataclass
class IssueExtractorInput:
    """Input for issue extraction."""

    note_id: UUID
    project_id: UUID
    max_issues: int = 10
    min_confidence: float = 0.5


@dataclass
class IssueExtractorOutput:
    """Output from issue extraction."""

    issues: list[ExtractedIssue] = field(default_factory=list)
    source_note_id: UUID | None = None
    extraction_summary: str = ""

    @property
    def recommended_count(self) -> int:
        """Count of recommended issues."""
        return sum(1 for i in self.issues if i.confidence_tag == ConfidenceTag.RECOMMENDED)

    @property
    def total_count(self) -> int:
        """Total issue count."""
        return len(self.issues)


class IssueExtractorAgent(SDKBaseAgent[IssueExtractorInput, IssueExtractorOutput]):
    """Extracts actionable issues from note content.

    Uses Claude Sonnet for balanced extraction quality.
    Returns issues with confidence tags per DD-048.

    MCP Tools Used:
    - get_note_content: Retrieve note blocks
    - get_project_context: Get labels, states for categorization
    """

    AGENT_NAME = "issue_extractor"
    DEFAULT_MODEL = "claude-sonnet-4-20250514"
    MAX_TOKENS = 4096

    def __init__(
        self,
        tool_registry: ToolRegistry,
        provider_selector: ProviderSelector,
        cost_tracker: CostTracker,
        resilient_executor: ResilientExecutor,
        key_storage: SecureKeyStorage,
    ) -> None:
        """Initialize issue extractor agent.

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
        """Get provider and model for issue extraction.

        Returns:
            Tuple of ("anthropic", "claude-sonnet-4-20250514")
        """
        return ("anthropic", self.DEFAULT_MODEL)

    async def _get_api_key(self, context: AgentContext) -> str | None:
        """Get Anthropic API key from secure storage.

        Args:
            context: Agent execution context.

        Returns:
            API key string or None if not configured.
        """
        return await self._key_storage.get_api_key(
            workspace_id=context.workspace_id,
            provider="anthropic",
        )

    async def execute(
        self,
        input_data: IssueExtractorInput,
        context: AgentContext,
    ) -> IssueExtractorOutput:
        """Extract issues from note content.

        Args:
            input_data: Note and project context
            context: Execution context

        Returns:
            Extracted issues with confidence tags
        """
        # Build extraction prompt
        prompt = self._build_prompt(input_data)
        system_prompt = self._get_system_prompt()

        # Get API key from secure storage
        api_key = await self._get_api_key(context)
        if not api_key:
            raise ValueError(
                f"No Anthropic API key configured for workspace {context.workspace_id}"
            )

        # Execute Claude API call with system prompt
        try:
            client = AsyncAnthropic(api_key=api_key)
            response = await client.messages.create(
                model=self.DEFAULT_MODEL,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.MAX_TOKENS,
            )

            # Track usage
            await self.track_usage(
                context,
                response.usage.input_tokens,
                response.usage.output_tokens,
            )

            # Parse structured output
            return self._parse_response(response, input_data.note_id)

        except Exception as e:
            logger.exception(
                "Failed to extract issues",
                extra={
                    "note_id": str(input_data.note_id),
                    "workspace_id": str(context.workspace_id),
                    "error": str(e),
                },
            )
            # Return empty result on error
            return IssueExtractorOutput(
                issues=[],
                source_note_id=input_data.note_id,
                extraction_summary=f"Extraction failed: {e}",
            )

    def _get_system_prompt(self) -> str:
        """System prompt for issue extraction."""
        return """You are an expert at analyzing technical notes and extracting actionable issues.

Your task is to identify potential issues, tasks, bugs, and improvements from the note content.

For each extracted issue, provide:
1. A clear, actionable title (imperative form)
2. A detailed description with context
3. Suggested labels based on the project's label schema
4. Priority (0=urgent, 1=high, 2=medium, 3=low, 4=no priority)
5. Confidence tag per the following schema:
   - RECOMMENDED: You strongly believe this should be an issue
   - DEFAULT: Standard extraction, reasonable confidence
   - CURRENT: Matches existing issues or patterns
   - ALTERNATIVE: Valid but may need human review
6. Confidence score (0.0-1.0)
7. Source block IDs from the note
8. Rationale for the extraction

Output as JSON array with this structure:
{
  "issues": [
    {
      "title": "string",
      "description": "string",
      "labels": ["string"],
      "priority": number,
      "confidence_tag": "recommended|default|current|alternative",
      "confidence_score": number,
      "source_block_ids": ["string"],
      "rationale": "string"
    }
  ],
  "extraction_summary": "Brief summary of what was found"
}

Use the MCP tools to:
1. get_note_content: Read the note blocks
2. get_project_context: Understand available labels and conventions"""

    def _build_prompt(self, input_data: IssueExtractorInput) -> str:
        """Build the extraction prompt."""
        return f"""Extract actionable issues from the note.

Note ID: {input_data.note_id}
Project ID: {input_data.project_id}
Max issues to extract: {input_data.max_issues}
Minimum confidence threshold: {input_data.min_confidence}

Steps:
1. Use get_note_content to read the note blocks
2. Use get_project_context to understand the project's labels and conventions
3. Analyze the content for actionable items
4. Return structured JSON with extracted issues

Only include issues with confidence_score >= {input_data.min_confidence}."""

    def _parse_response(
        self,
        response: Any,
        note_id: UUID,
    ) -> IssueExtractorOutput:
        """Parse Anthropic API response to output format."""
        # Extract text from first content block
        content = ""
        if hasattr(response, "content") and response.content:
            first_block = response.content[0]
            content = first_block.text if hasattr(first_block, "text") else str(first_block)
        else:
            content = str(response)

        # Find JSON in response
        data: dict[str, Any]
        try:
            # Try to parse entire response as JSON
            data = json.loads(content)
        except json.JSONDecodeError:
            # Extract JSON from markdown code block
            json_match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    data = {"issues": [], "extraction_summary": "Failed to parse response"}
            else:
                # Try to find JSON object
                start_idx = content.find("{")
                end_idx = content.rfind("}") + 1
                if start_idx != -1 and end_idx > 0:
                    try:
                        data = json.loads(content[start_idx:end_idx])
                    except json.JSONDecodeError:
                        data = {"issues": [], "extraction_summary": "Failed to parse response"}
                else:
                    data = {"issues": [], "extraction_summary": "Failed to parse response"}

        # Parse issues
        issues: list[ExtractedIssue] = []
        raw_issues = data.get("issues", [])
        if not isinstance(raw_issues, list):
            raw_issues = []

        for raw_issue in raw_issues:
            if not isinstance(raw_issue, dict):
                continue

            try:
                # Parse confidence tag
                confidence_tag_str = raw_issue.get("confidence_tag")
                if confidence_tag_str:
                    try:
                        confidence_tag = ConfidenceTag(str(confidence_tag_str))
                    except ValueError:
                        # Fallback to score-based tag
                        confidence_score = float(raw_issue.get("confidence_score", 0.5))
                        confidence_tag = get_confidence_tag(confidence_score)
                else:
                    # No tag provided, use score
                    confidence_score_val = float(raw_issue.get("confidence_score", 0.5))
                    confidence_tag = get_confidence_tag(confidence_score_val)

                # Parse labels
                labels_raw = raw_issue.get("labels", [])
                labels = labels_raw if isinstance(labels_raw, list) else []

                # Parse source block IDs
                source_blocks_raw = raw_issue.get("source_block_ids", [])
                source_blocks = source_blocks_raw if isinstance(source_blocks_raw, list) else []

                issues.append(
                    ExtractedIssue(
                        title=str(raw_issue.get("title", "Untitled Issue")),
                        description=str(raw_issue.get("description", "")),
                        labels=labels,
                        priority=int(raw_issue.get("priority", 2)),
                        confidence_tag=confidence_tag,
                        confidence_score=float(raw_issue.get("confidence_score", 0.5)),
                        source_block_ids=source_blocks,
                        rationale=str(raw_issue.get("rationale", "")),
                    )
                )
            except (ValueError, KeyError, TypeError) as e:
                logger.warning(f"Failed to parse extracted issue: {e}")
                continue

        summary = data.get("extraction_summary", f"Extracted {len(issues)} issues")
        return IssueExtractorOutput(
            issues=issues,
            source_note_id=note_id,
            extraction_summary=str(summary),
        )


__all__ = [
    "ExtractedIssue",
    "IssueExtractorAgent",
    "IssueExtractorInput",
    "IssueExtractorOutput",
]
