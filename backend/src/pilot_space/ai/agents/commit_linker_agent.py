"""Commit Linker AI Agent for issue reference extraction.

T180: Create CommitLinkerAgent for parsing issue refs from commits/PRs.
Uses Claude Haiku for speed with regex fallback.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from pilot_space.ai.agents.base import (
    AgentContext,
    AgentResult,
    BaseAgent,
    Provider,
    TaskType,
)
from pilot_space.ai.telemetry import AIOperation
from pilot_space.ai.utils.retry import RetryConfig

logger = logging.getLogger(__name__)

# Regex patterns for issue extraction
ISSUE_REF_PATTERN = re.compile(r"([A-Z]{2,10})-(\d+)", re.IGNORECASE)
FIX_KEYWORDS = ("fix", "fixes", "fixed", "close", "closes", "closed", "resolve", "resolves")

SYSTEM_PROMPT = """You are an AI that extracts issue references from git commit messages and PR descriptions.

Given a commit message or PR title/body, identify all issue references in the format PROJECT-NUMBER (e.g., PILOT-123, ABC-456).

For each reference found, determine:
1. The issue identifier (e.g., PILOT-123)
2. Whether it indicates the issue should be closed (preceded by fix/close/resolve keywords)

Return a JSON array with objects containing:
- "identifier": the issue identifier
- "is_closing": boolean indicating if this is a closing reference

Example input:
"Fix PILOT-123: Update authentication flow
Also related to ABC-456"

Example output:
[{"identifier": "PILOT-123", "is_closing": true}, {"identifier": "ABC-456", "is_closing": false}]

Only return the JSON array, no other text."""


@dataclass
class CommitLinkerInput:
    """Input for CommitLinkerAgent.

    Attributes:
        text: Text to analyze (commit message, PR title/body).
        use_ai: Whether to use AI for extraction (vs regex only).
        project_prefixes: Optional list of valid project prefixes to filter.
    """

    text: str
    use_ai: bool = False  # Default to regex for speed
    project_prefixes: list[str] = field(default_factory=list)


@dataclass
class IssueLink:
    """Extracted issue link."""

    identifier: str
    is_closing: bool = False


@dataclass
class CommitLinkerOutput:
    """Output from CommitLinkerAgent."""

    links: list[IssueLink]
    method: str  # "regex" or "ai"


class CommitLinkerAgent(BaseAgent[CommitLinkerInput, CommitLinkerOutput]):
    """Agent for extracting issue references from text.

    Uses:
    - Fast regex extraction by default
    - Claude Haiku AI extraction for ambiguous cases

    Optimized for latency since this runs on every commit.
    """

    task_type = TaskType.LATENCY_SENSITIVE
    operation = AIOperation.CONTEXT_GENERATION
    retry_config = RetryConfig(max_retries=2, initial_delay_seconds=0.5)

    def __init__(self, model: str | None = None) -> None:
        """Initialize agent.

        Args:
            model: Override model (defaults to Haiku for speed).
        """
        # Use Haiku for speed
        super().__init__(model or "claude-3-5-haiku-20241022")

    def extract_with_regex(self, text: str) -> list[IssueLink]:
        """Extract issue references using regex.

        Args:
            text: Text to analyze.

        Returns:
            List of IssueLink objects.
        """
        if not text:
            return []

        links: list[IssueLink] = []
        seen: set[str] = set()

        for match in ISSUE_REF_PATTERN.finditer(text):
            project = match.group(1).upper()
            number = int(match.group(2))
            identifier = f"{project}-{number}"

            if identifier in seen:
                continue
            seen.add(identifier)

            # Check for fix/close keywords before the match
            start = match.start()
            prefix_text = text[max(0, start - 20) : start].lower().strip()
            is_closing = any(prefix_text.endswith(kw) for kw in FIX_KEYWORDS)

            links.append(IssueLink(identifier=identifier, is_closing=is_closing))

        return links

    def filter_by_prefixes(
        self,
        links: list[IssueLink],
        prefixes: list[str],
    ) -> list[IssueLink]:
        """Filter links by valid project prefixes.

        Args:
            links: List of extracted links.
            prefixes: Valid project prefixes.

        Returns:
            Filtered list.
        """
        if not prefixes:
            return links

        prefix_set = {p.upper() for p in prefixes}
        return [link for link in links if link.identifier.split("-")[0].upper() in prefix_set]

    async def _execute_impl(
        self,
        input_data: CommitLinkerInput,
        context: AgentContext,
    ) -> AgentResult[CommitLinkerOutput]:
        """Execute issue extraction.

        Args:
            input_data: Input with text to analyze.
            context: Agent context.

        Returns:
            AgentResult with extracted links.
        """
        # Always start with regex
        regex_links = self.extract_with_regex(input_data.text)

        # Filter by prefixes if provided
        if input_data.project_prefixes:
            regex_links = self.filter_by_prefixes(regex_links, input_data.project_prefixes)

        # If AI not requested or no API key, return regex results
        if not input_data.use_ai:
            return AgentResult(
                output=CommitLinkerOutput(links=regex_links, method="regex"),
                model=self.model,
                provider=Provider.CLAUDE,
                input_tokens=0,
                output_tokens=0,
            )

        # Try AI extraction for potentially better results
        try:
            ai_links = await self._extract_with_ai(input_data.text, context)
            if input_data.project_prefixes:
                ai_links = self.filter_by_prefixes(ai_links, input_data.project_prefixes)

            return AgentResult(
                output=CommitLinkerOutput(links=ai_links, method="ai"),
                model=self.model,
                provider=Provider.CLAUDE,
                input_tokens=len(input_data.text) // 4,  # Rough estimate
                output_tokens=100,
            )
        except Exception as e:
            logger.warning(f"AI extraction failed, falling back to regex: {e}")
            return AgentResult(
                output=CommitLinkerOutput(links=regex_links, method="regex"),
                model=self.model,
                provider=Provider.CLAUDE,
                input_tokens=0,
                output_tokens=0,
            )

    async def _extract_with_ai(
        self,
        text: str,
        context: AgentContext,
    ) -> list[IssueLink]:
        """Extract issue references using AI.

        Args:
            text: Text to analyze.
            context: Agent context.

        Returns:
            List of IssueLink objects.
        """
        import json

        import anthropic

        api_key = context.require_api_key(Provider.CLAUDE)
        client = anthropic.AsyncAnthropic(api_key=api_key)

        response = await client.messages.create(
            model=self.model,
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": text}],
        )

        # Parse response
        content = response.content[0]
        if content.type != "text":
            return []

        try:
            data = json.loads(content.text)
            return [
                IssueLink(
                    identifier=item["identifier"],
                    is_closing=item.get("is_closing", False),
                )
                for item in data
                if isinstance(item, dict) and "identifier" in item
            ]
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse AI response: {e}")
            return []


def extract_issue_refs(text: str) -> list[dict[str, Any]]:
    """Convenience function for sync extraction.

    Args:
        text: Text to analyze.

    Returns:
        List of dicts with identifier and is_closing keys.
    """
    agent = CommitLinkerAgent()
    links = agent.extract_with_regex(text)
    return [{"identifier": link.identifier, "is_closing": link.is_closing} for link in links]


__all__ = [
    "CommitLinkerAgent",
    "CommitLinkerInput",
    "CommitLinkerOutput",
    "IssueLink",
    "extract_issue_refs",
]
