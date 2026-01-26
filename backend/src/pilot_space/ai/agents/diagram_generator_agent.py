"""Diagram Generator Agent using Claude Agent SDK.

Generates Mermaid diagrams from textual descriptions.
Supports flowcharts, sequence diagrams, class diagrams, ERDs, and state machines.

T085-T086: DiagramGeneratorAgent implementation.
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


class DiagramType(StrEnum):
    """Supported diagram types."""

    FLOWCHART = "flowchart"
    SEQUENCE = "sequence"
    CLASS = "class"
    ERD = "erd"
    STATE = "state"
    GANTT = "gantt"


@dataclass(frozen=True, slots=True, kw_only=True)
class DiagramGeneratorInput:
    """Input for diagram generation.

    Attributes:
        diagram_type: Type of diagram to generate.
        description: Textual description of what to diagram.
        source_id: Optional issue/note ID for context.
        style_preferences: Optional styling preferences.
    """

    diagram_type: DiagramType
    description: str
    source_id: str | None = None
    style_preferences: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class DiagramGeneratorOutput:
    """Generated diagram output.

    Attributes:
        mermaid_code: Mermaid diagram syntax.
        diagram_type: Type of diagram generated.
        title: Suggested diagram title.
        description: Brief description of the diagram.
    """

    mermaid_code: str
    diagram_type: DiagramType
    title: str
    description: str


class DiagramGeneratorAgent(SDKBaseAgent[DiagramGeneratorInput, DiagramGeneratorOutput]):
    """Generates Mermaid diagrams from textual descriptions.

    Uses Claude Sonnet for code generation with precise syntax.

    Attributes:
        AGENT_NAME: Unique identifier for this agent.
        DEFAULT_MODEL: Claude Sonnet 4 for code quality.
        MAX_TOKENS: 2048 for diagram code.
    """

    AGENT_NAME = "diagram_generator"
    DEFAULT_MODEL = "claude-sonnet-4-20250514"
    MAX_TOKENS = 2048

    def __init__(
        self,
        tool_registry: ToolRegistry,
        provider_selector: ProviderSelector,
        cost_tracker: CostTracker,
        resilient_executor: ResilientExecutor,
    ) -> None:
        """Initialize diagram generator agent.

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
        input_data: DiagramGeneratorInput,
        context: AgentContext,
    ) -> DiagramGeneratorOutput:
        """Execute diagram generation.

        Args:
            input_data: Diagram generation parameters.
            context: Execution context.

        Returns:
            Generated Mermaid diagram.

        Raises:
            AIConfigurationError: If Anthropic API key not configured.
        """
        # Validate input
        if not input_data.description:
            raise ValueError("description is required")

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
        system_prompt = self._get_system_prompt(input_data.diagram_type)

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

        return self._parse_response(content, input_data.diagram_type)

    def _build_prompt(self, input_data: DiagramGeneratorInput) -> str:
        """Build diagram generation prompt.

        Args:
            input_data: Input parameters.

        Returns:
            Formatted prompt.
        """
        prompt = f"""Generate a {input_data.diagram_type.value} diagram in Mermaid syntax.

Description: {input_data.description}
"""

        if input_data.source_id:
            prompt += f"\nSource ID: {input_data.source_id}"

        if input_data.style_preferences:
            prompt += f"\nStyle Preferences: {input_data.style_preferences}"

        prompt += """

Requirements:
- Use valid Mermaid syntax that renders correctly
- Keep it clear and readable
- Use meaningful node/edge labels
- Include a title comment

Return only the Mermaid code, optionally with a brief description.
"""

        return prompt

    def _get_system_prompt(self, diagram_type: DiagramType) -> str:
        """Get system prompt for diagram type.

        Args:
            diagram_type: Type of diagram.

        Returns:
            System prompt string.
        """
        base_prompt = """You are an expert at creating Mermaid diagrams.

Generate valid Mermaid syntax that renders correctly.
Follow Mermaid best practices for the specific diagram type.
Use clear, descriptive labels and maintain visual clarity.
"""

        type_specific = {
            DiagramType.FLOWCHART: """
For flowcharts:
- Use flowchart TD (top-down) or LR (left-right)
- Use appropriate node shapes: [] for processes, {} for decisions, () for start/end
- Connect nodes with --> or --- with optional labels
- Keep the flow logical and easy to follow
""",
            DiagramType.SEQUENCE: """
For sequence diagrams:
- Use sequenceDiagram keyword
- Define participants clearly
- Show message flow with arrows
- Use activation boxes for processing
- Include notes where helpful
""",
            DiagramType.CLASS: """
For class diagrams:
- Use classDiagram keyword
- Define classes with attributes and methods
- Show relationships (inheritance, composition, association)
- Use proper UML notation
""",
            DiagramType.ERD: """
For entity relationship diagrams:
- Use erDiagram keyword
- Define entities with attributes
- Show relationships with cardinality
- Use proper ERD notation
""",
            DiagramType.STATE: """
For state diagrams:
- Use stateDiagram-v2 keyword
- Define states clearly
- Show transitions with events
- Include initial and final states
""",
        }

        return base_prompt + type_specific.get(diagram_type, "")

    def _parse_response(
        self, content: str, diagram_type: DiagramType
    ) -> DiagramGeneratorOutput:
        """Parse diagram response.

        Args:
            content: Generated content.
            diagram_type: Diagram type.

        Returns:
            Parsed diagram output.
        """
        # Extract Mermaid code from response
        mermaid_code = content
        description = ""

        # If response contains markdown code block
        if "```mermaid" in content:
            start = content.find("```mermaid") + 10
            end = content.find("```", start)
            mermaid_code = content[start:end].strip()

            # Description is text before code block
            before_code = content[:content.find("```mermaid")].strip()
            if before_code:
                description = before_code
        elif "```" in content:
            # Generic code block
            start = content.find("```") + 3
            end = content.find("```", start)
            mermaid_code = content[start:end].strip()

        # Extract title from first line comment if present
        title = f"{diagram_type.value.title()} Diagram"
        lines = mermaid_code.split("\n")
        if lines and lines[0].strip().startswith("%%"):
            # Extract from comment
            title = lines[0].strip().lstrip("%").strip()

        if not description:
            description = f"Generated {diagram_type.value} diagram"

        return DiagramGeneratorOutput(
            mermaid_code=mermaid_code,
            diagram_type=diagram_type,
            title=title,
            description=description,
        )


__all__ = [
    "DiagramGeneratorAgent",
    "DiagramGeneratorInput",
    "DiagramGeneratorOutput",
    "DiagramType",
]
