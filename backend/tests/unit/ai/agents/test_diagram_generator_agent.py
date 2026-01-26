"""Unit tests for DiagramGeneratorAgent.

T085-T086: DiagramGeneratorAgent tests.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from pilot_space.ai.agents.diagram_generator_agent import (
    DiagramGeneratorAgent,
    DiagramGeneratorInput,
    DiagramType,
)
from pilot_space.ai.agents.sdk_base import AgentContext


@pytest.fixture
def mock_infrastructure() -> dict:
    """Create mock infrastructure dependencies."""
    return {
        "tool_registry": MagicMock(),
        "provider_selector": MagicMock(),
        "cost_tracker": AsyncMock(),
        "resilient_executor": AsyncMock(),
    }


@pytest.fixture
def diagram_generator_agent(mock_infrastructure: dict) -> DiagramGeneratorAgent:
    """Create DiagramGeneratorAgent with mocked dependencies."""
    return DiagramGeneratorAgent(**mock_infrastructure)


@pytest.fixture
def agent_context() -> AgentContext:
    """Create test agent context."""
    return AgentContext(
        workspace_id=uuid4(),
        user_id=uuid4(),
        metadata={"anthropic_api_key": "test-key"},
    )


class TestDiagramGeneratorAgent:
    """Test suite for DiagramGeneratorAgent."""

    def test_agent_initialization(
        self, diagram_generator_agent: DiagramGeneratorAgent
    ) -> None:
        """Verify agent initializes with correct configuration."""
        assert diagram_generator_agent.AGENT_NAME == "diagram_generator"
        assert diagram_generator_agent.DEFAULT_MODEL == "claude-sonnet-4-20250514"
        assert diagram_generator_agent.MAX_TOKENS == 2048

    def test_build_prompt_basic(
        self, diagram_generator_agent: DiagramGeneratorAgent
    ) -> None:
        """Verify prompt building with basic input."""
        input_data = DiagramGeneratorInput(
            diagram_type=DiagramType.FLOWCHART,
            description="User login flow",
        )

        prompt = diagram_generator_agent._build_prompt(input_data)

        assert "flowchart" in prompt
        assert "User login flow" in prompt
        assert "Mermaid" in prompt

    def test_build_prompt_with_context(
        self, diagram_generator_agent: DiagramGeneratorAgent
    ) -> None:
        """Verify prompt building with additional context."""
        input_data = DiagramGeneratorInput(
            diagram_type=DiagramType.SEQUENCE,
            description="API authentication sequence",
            source_id="issue-789",
            style_preferences="Use blue for client, green for server",
        )

        prompt = diagram_generator_agent._build_prompt(input_data)

        assert "sequence" in prompt
        assert "API authentication" in prompt
        assert "issue-789" in prompt
        assert "blue for client" in prompt

    def test_get_system_prompt_flowchart(
        self, diagram_generator_agent: DiagramGeneratorAgent
    ) -> None:
        """Verify system prompt for flowchart type."""
        system_prompt = diagram_generator_agent._get_system_prompt(
            DiagramType.FLOWCHART
        )

        assert "flowchart" in system_prompt.lower()
        assert "TD" in system_prompt or "top-down" in system_prompt.lower()
        assert "node shapes" in system_prompt.lower()

    def test_get_system_prompt_sequence(
        self, diagram_generator_agent: DiagramGeneratorAgent
    ) -> None:
        """Verify system prompt for sequence diagram type."""
        system_prompt = diagram_generator_agent._get_system_prompt(DiagramType.SEQUENCE)

        assert "sequence" in system_prompt.lower()
        assert "participants" in system_prompt.lower()
        assert "message flow" in system_prompt.lower()

    def test_parse_response_basic_mermaid(
        self, diagram_generator_agent: DiagramGeneratorAgent
    ) -> None:
        """Verify parsing of basic Mermaid code."""
        content = """flowchart TD
    A[Start] --> B{Decision}
    B -->|Yes| C[Action]
    B -->|No| D[End]"""

        output = diagram_generator_agent._parse_response(content, DiagramType.FLOWCHART)

        assert "flowchart TD" in output.mermaid_code
        assert output.diagram_type == DiagramType.FLOWCHART
        assert "Flowchart" in output.title

    def test_parse_response_markdown_wrapped(
        self, diagram_generator_agent: DiagramGeneratorAgent
    ) -> None:
        """Verify parsing of Mermaid code in markdown block."""
        content = """Here's the diagram:

```mermaid
%% Login Flow
sequenceDiagram
    User->>Server: Login Request
    Server->>Database: Validate
    Database-->>Server: User Data
    Server-->>User: Success
```

This shows the login process."""

        output = diagram_generator_agent._parse_response(content, DiagramType.SEQUENCE)

        assert "sequenceDiagram" in output.mermaid_code
        assert "Login Request" in output.mermaid_code
        assert output.diagram_type == DiagramType.SEQUENCE
        assert "Login Flow" in output.title
        # Description is text before code block
        assert "diagram" in output.description.lower()

    def test_parse_response_with_comment_title(
        self, diagram_generator_agent: DiagramGeneratorAgent
    ) -> None:
        """Verify title extraction from Mermaid comment."""
        content = """```mermaid
%% System Architecture
flowchart LR
    A --> B
    B --> C
```"""

        output = diagram_generator_agent._parse_response(content, DiagramType.FLOWCHART)

        assert "System Architecture" in output.title

    def test_parse_response_generic_code_block(
        self, diagram_generator_agent: DiagramGeneratorAgent
    ) -> None:
        """Verify parsing of generic code block."""
        content = """```
graph TD
    A[Node 1]
    B[Node 2]
    A --> B
```"""

        output = diagram_generator_agent._parse_response(content, DiagramType.FLOWCHART)

        assert "graph TD" in output.mermaid_code
        assert "Node 1" in output.mermaid_code

    @pytest.mark.asyncio
    async def test_execute_requires_api_key(
        self,
        diagram_generator_agent: DiagramGeneratorAgent,
    ) -> None:
        """Verify execution fails without API key."""
        input_data = DiagramGeneratorInput(
            diagram_type=DiagramType.FLOWCHART,
            description="Test diagram",
        )
        context = AgentContext(
            workspace_id=uuid4(),
            user_id=uuid4(),
            metadata={},  # No API key
        )

        with pytest.raises(Exception) as exc_info:
            await diagram_generator_agent.execute(input_data, context)

        assert "api key" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_execute_validates_input(
        self,
        diagram_generator_agent: DiagramGeneratorAgent,
        agent_context: AgentContext,
    ) -> None:
        """Verify execution validates required fields."""
        input_data = DiagramGeneratorInput(
            diagram_type=DiagramType.FLOWCHART,
            description="",  # Empty description
        )

        with pytest.raises(ValueError) as exc_info:
            await diagram_generator_agent.execute(input_data, agent_context)

        assert "required" in str(exc_info.value).lower()


__all__ = ["TestDiagramGeneratorAgent"]
