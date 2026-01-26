"""Commit Linker AI Agent for issue reference extraction using Claude Agent SDK.

T180: CommitLinkerAgent SDK migration.
Uses Claude Haiku for speed with regex fallback.

Architecture:
- Extends SDKBaseAgent for consistent infrastructure
- Uses claude-3-5-haiku for fast responses
- Regex-first approach with optional AI enhancement
- Graceful degradation on AI failures
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from anthropic import AsyncAnthropic

from pilot_space.ai.agents.sdk_base import (
    AgentContext,
    SDKBaseAgent,
)

if TYPE_CHECKING:
    from pilot_space.ai.infrastructure.cost_tracker import CostTracker
    from pilot_space.ai.infrastructure.key_storage import SecureKeyStorage
    from pilot_space.ai.infrastructure.resilience import ResilientExecutor
    from pilot_space.ai.providers.provider_selector import ProviderSelector
    from pilot_space.ai.tools.mcp_server import ToolRegistry

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
    input_tokens: int = 0
    output_tokens: int = 0


class CommitLinkerAgent(SDKBaseAgent[CommitLinkerInput, CommitLinkerOutput]):
    """Agent for extracting issue references from text using Claude Agent SDK.

    Uses:
    - Fast regex extraction by default
    - Claude Haiku AI extraction for ambiguous cases

    Optimized for latency since this runs on every commit.

    Attributes:
        AGENT_NAME: Unique identifier for cost tracking.
        DEFAULT_MODEL: Claude Haiku for speed.
    """

    AGENT_NAME = "commit_linker"
    DEFAULT_MODEL = "claude-3-5-haiku-20241022"

    def __init__(
        self,
        tool_registry: ToolRegistry,
        provider_selector: ProviderSelector,
        cost_tracker: CostTracker,
        resilient_executor: ResilientExecutor,
        key_storage: SecureKeyStorage,
    ) -> None:
        """Initialize agent.

        Args:
            tool_registry: Registry for MCP tool access
            provider_selector: Provider/model selection service
            cost_tracker: Cost tracking service
            resilient_executor: Retry and circuit breaker service
            key_storage: Secure API key storage
        """
        super().__init__(
            tool_registry=tool_registry,
            provider_selector=provider_selector,
            cost_tracker=cost_tracker,
            resilient_executor=resilient_executor,
        )
        self._key_storage = key_storage

    def get_model(self) -> tuple[str, str]:
        """Get provider and model for commit linking.

        Returns:
            Tuple of (provider, model) for Claude Haiku.
        """
        return ("anthropic", self.DEFAULT_MODEL)

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
            prefix_text = text[max(0, start - 20):start].lower().strip()
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
        return [
            link for link in links if link.identifier.split("-")[0].upper() in prefix_set
        ]

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
        input_data: CommitLinkerInput,
        context: AgentContext,
    ) -> CommitLinkerOutput:
        """Execute issue extraction.

        Args:
            input_data: Input with text to analyze.
            context: Agent context.

        Returns:
            CommitLinkerOutput with extracted links.
        """
        # Always start with regex
        regex_links = self.extract_with_regex(input_data.text)

        # Filter by prefixes if provided
        if input_data.project_prefixes:
            regex_links = self.filter_by_prefixes(regex_links, input_data.project_prefixes)

        # If AI not requested, return regex results
        if not input_data.use_ai:
            return CommitLinkerOutput(links=regex_links, method="regex")

        # Try AI extraction for potentially better results
        try:
            ai_links, input_tokens, output_tokens = await self._extract_with_ai(
                input_data.text, context
            )
            if input_data.project_prefixes:
                ai_links = self.filter_by_prefixes(ai_links, input_data.project_prefixes)

            # Track usage
            await self.track_usage(
                context=context,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )

            return CommitLinkerOutput(
                links=ai_links,
                method="ai",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
        except Exception as e:
            logger.warning(f"AI extraction failed, falling back to regex: {e}")
            return CommitLinkerOutput(links=regex_links, method="regex")

    async def _extract_with_ai(
        self,
        text: str,
        context: AgentContext,
    ) -> tuple[list[IssueLink], int, int]:
        """Extract issue references using AI.

        Args:
            text: Text to analyze.
            context: Agent context.

        Returns:
            Tuple of (links, input_tokens, output_tokens).

        Raises:
            Exception: If AI extraction fails.
        """
        api_key = await self._get_api_key(context)
        if not api_key:
            raise ValueError("Anthropic API key not configured")

        client = AsyncAnthropic(api_key=api_key)

        response = await client.messages.create(
            model=self.DEFAULT_MODEL,
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": text}],
        )

        # Parse response
        content = response.content[0]
        if content.type != "text":
            return [], response.usage.input_tokens, response.usage.output_tokens

        try:
            data = json.loads(content.text)
            links = [
                IssueLink(
                    identifier=item["identifier"],
                    is_closing=item.get("is_closing", False),
                )
                for item in data
                if isinstance(item, dict) and "identifier" in item
            ]
            return links, response.usage.input_tokens, response.usage.output_tokens
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse AI response: {e}")
            return [], response.usage.input_tokens, response.usage.output_tokens


def extract_issue_refs(text: str) -> list[dict[str, Any]]:
    """Convenience function for sync regex-only extraction.

    Args:
        text: Text to analyze.

    Returns:
        List of dicts with identifier and is_closing keys.
    """
    if not text:
        return []

    links: list[dict[str, Any]] = []
    seen: set[str] = set()

    for match in ISSUE_REF_PATTERN.finditer(text):
        project = match.group(1).upper()
        number = int(match.group(2))
        identifier = f"{project}-{number}"

        if identifier in seen:
            continue
        seen.add(identifier)

        start = match.start()
        prefix_text = text[max(0, start - 20):start].lower().strip()
        is_closing = any(prefix_text.endswith(kw) for kw in FIX_KEYWORDS)

        links.append({"identifier": identifier, "is_closing": is_closing})

    return links


__all__ = [
    "CommitLinkerAgent",
    "CommitLinkerInput",
    "CommitLinkerOutput",
    "IssueLink",
    "extract_issue_refs",
]
