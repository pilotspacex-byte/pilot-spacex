"""Documentation Generator Agent using Claude Agent SDK.

Generates documentation from project context (README, API docs, architecture, user guides).
Uses query() for one-shot document generation.

T081-T082: DocGeneratorAgent implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from anthropic import Anthropic

from pilot_space.ai.agents.sdk_base import AgentContext, SDKBaseAgent
from pilot_space.ai.exceptions import AIConfigurationError

if TYPE_CHECKING:
    from pilot_space.ai.infrastructure.cost_tracker import CostTracker
    from pilot_space.ai.infrastructure.resilience import ResilientExecutor
    from pilot_space.ai.providers.provider_selector import ProviderSelector
    from pilot_space.ai.tools.mcp_server import ToolRegistry


class DocType(StrEnum):
    """Documentation type to generate."""

    README = "readme"
    API_DOCS = "api_docs"
    ARCHITECTURE = "architecture"
    USER_GUIDE = "user_guide"
    CHANGELOG = "changelog"
    CONTRIBUTING = "contributing"


@dataclass(frozen=True, slots=True, kw_only=True)
class DocGeneratorInput:
    """Input for documentation generation.

    Attributes:
        doc_type: Type of documentation to generate.
        source_id: Optional issue, note, or project ID for context.
        template: Optional template to follow.
        project_context: Additional project context.
    """

    doc_type: DocType
    source_id: str | None = None
    template: str | None = None
    project_context: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class DocGeneratorOutput:
    """Generated documentation output.

    Attributes:
        content: Generated documentation content.
        format: Output format (markdown, html).
        sections: List of section titles included.
        estimated_reading_time: Estimated reading time in minutes.
    """

    content: str
    format: str = "markdown"
    sections: list[str]
    estimated_reading_time: int


class DocGeneratorAgent(SDKBaseAgent[DocGeneratorInput, DocGeneratorOutput]):
    """Generates documentation from project context.

    Uses Claude Sonnet for high-quality technical writing.
    Supports multiple doc types with consistent formatting.

    Attributes:
        AGENT_NAME: Unique identifier for this agent.
        DEFAULT_MODEL: Claude Sonnet 4 for documentation quality.
        MAX_TOKENS: 8192 for long-form documentation.
    """

    AGENT_NAME = "doc_generator"
    DEFAULT_MODEL = "claude-sonnet-4-20250514"
    MAX_TOKENS = 8192

    def __init__(
        self,
        tool_registry: ToolRegistry,
        provider_selector: ProviderSelector,
        cost_tracker: CostTracker,
        resilient_executor: ResilientExecutor,
    ) -> None:
        """Initialize doc generator agent.

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
        input_data: DocGeneratorInput,
        context: AgentContext,
    ) -> DocGeneratorOutput:
        """Execute documentation generation.

        Args:
            input_data: Documentation generation parameters.
            context: Execution context with API keys.

        Returns:
            Generated documentation.

        Raises:
            AIConfigurationError: If Anthropic API key not configured.
        """
        # Validate input
        if not input_data.doc_type:
            raise ValueError("doc_type is required")

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
        system_prompt = self._get_system_prompt(input_data.doc_type)

        # Call Anthropic API using query pattern
        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model=self.DEFAULT_MODEL,
            max_tokens=self.MAX_TOKENS,
            temperature=0.5,
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

        return self._parse_response(content, input_data.doc_type)

    def _build_prompt(self, input_data: DocGeneratorInput) -> str:
        """Build generation prompt.

        Args:
            input_data: Input parameters.

        Returns:
            Formatted prompt string.
        """
        prompt_parts = [
            f"Generate {input_data.doc_type.value} documentation.",
        ]

        if input_data.source_id:
            prompt_parts.append(f"Source context ID: {input_data.source_id}")

        if input_data.project_context:
            prompt_parts.append(f"\nProject Context:\n{input_data.project_context}")

        if input_data.template:
            prompt_parts.append(f"\nFollow this template:\n{input_data.template}")

        prompt_parts.append(
            "\nGenerate comprehensive, well-structured documentation "
            "with clear sections and practical examples."
        )

        return "\n\n".join(prompt_parts)

    def _get_system_prompt(self, doc_type: DocType) -> str:
        """Get system prompt for documentation type.

        Args:
            doc_type: Type of documentation.

        Returns:
            System prompt string.
        """
        base_prompt = """You are a technical documentation expert.
Generate clear, comprehensive, and well-structured documentation.

Follow these principles:
- Use clear, concise language
- Structure content with proper headings
- Include practical examples
- Use Markdown formatting
- Make it scannable with lists and code blocks
"""

        type_specific = {
            DocType.README: """
For README files:
- Start with project name and brief description
- Include installation instructions
- Add usage examples
- List key features
- Include contributing guidelines
""",
            DocType.API_DOCS: """
For API documentation:
- Document each endpoint with method, path, parameters
- Show request/response examples
- Include error codes and meanings
- Add authentication requirements
""",
            DocType.ARCHITECTURE: """
For architecture documentation:
- Describe system components and their relationships
- Explain design decisions and trade-offs
- Include architecture diagrams (Mermaid syntax)
- Document data flow and integration points
""",
            DocType.USER_GUIDE: """
For user guides:
- Use step-by-step instructions
- Include screenshots or diagrams where helpful
- Anticipate common questions
- Add troubleshooting section
""",
        }

        return base_prompt + type_specific.get(doc_type, "")

    def _parse_response(self, content: str, doc_type: DocType) -> DocGeneratorOutput:  # noqa: ARG002
        """Parse documentation response.

        Args:
            content: Generated content.
            doc_type: Documentation type (reserved for future use).

        Returns:
            Parsed output.
        """
        # Extract sections from markdown headers
        sections = []
        for line in content.split("\n"):
            if line.startswith("#"):
                # Extract heading text, remove leading # symbols
                section_title = line.lstrip("#").strip()
                sections.append(section_title)

        # Estimate reading time (200 words per minute)
        word_count = len(content.split())
        estimated_time = max(1, word_count // 200)

        return DocGeneratorOutput(
            content=content,
            format="markdown",
            sections=sections,
            estimated_reading_time=estimated_time,
        )


__all__ = [
    "DocGeneratorAgent",
    "DocGeneratorInput",
    "DocGeneratorOutput",
    "DocType",
]
