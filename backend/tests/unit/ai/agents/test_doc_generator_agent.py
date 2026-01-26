"""Unit tests for DocGeneratorAgent.

T081-T082: DocGeneratorAgent tests.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from pilot_space.ai.agents.doc_generator_agent import (
    DocGeneratorAgent,
    DocGeneratorInput,
    DocType,
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
def doc_generator_agent(mock_infrastructure: dict) -> DocGeneratorAgent:
    """Create DocGeneratorAgent with mocked dependencies."""
    return DocGeneratorAgent(**mock_infrastructure)


@pytest.fixture
def agent_context() -> AgentContext:
    """Create test agent context."""
    return AgentContext(
        workspace_id=uuid4(),
        user_id=uuid4(),
        metadata={"anthropic_api_key": "test-key"},
    )


class TestDocGeneratorAgent:
    """Test suite for DocGeneratorAgent."""

    def test_agent_initialization(self, doc_generator_agent: DocGeneratorAgent) -> None:
        """Verify agent initializes with correct configuration."""
        assert doc_generator_agent.AGENT_NAME == "doc_generator"
        assert doc_generator_agent.DEFAULT_MODEL == "claude-sonnet-4-20250514"
        assert doc_generator_agent.MAX_TOKENS == 8192

    def test_build_prompt_basic(self, doc_generator_agent: DocGeneratorAgent) -> None:
        """Verify prompt building with basic input."""
        input_data = DocGeneratorInput(
            doc_type=DocType.README,
        )

        prompt = doc_generator_agent._build_prompt(input_data)

        assert "generate readme documentation" in prompt.lower()
        assert "comprehensive" in prompt.lower()

    def test_build_prompt_with_context(
        self, doc_generator_agent: DocGeneratorAgent
    ) -> None:
        """Verify prompt building with project context."""
        input_data = DocGeneratorInput(
            doc_type=DocType.API_DOCS,
            source_id="issue-123",
            project_context="FastAPI REST API for project management",
            template="# API\n\n## Endpoints",
        )

        prompt = doc_generator_agent._build_prompt(input_data)

        assert "api_docs" in prompt
        assert "issue-123" in prompt
        assert "FastAPI REST API" in prompt
        assert "# API" in prompt

    def test_get_system_prompt_readme(
        self, doc_generator_agent: DocGeneratorAgent
    ) -> None:
        """Verify system prompt for README type."""
        system_prompt = doc_generator_agent._get_system_prompt(DocType.README)

        assert "README" in system_prompt
        assert "installation" in system_prompt.lower()
        assert "usage examples" in system_prompt.lower()

    def test_get_system_prompt_api_docs(
        self, doc_generator_agent: DocGeneratorAgent
    ) -> None:
        """Verify system prompt for API docs type."""
        system_prompt = doc_generator_agent._get_system_prompt(DocType.API_DOCS)

        assert "API" in system_prompt
        assert "endpoint" in system_prompt.lower()
        assert "request/response" in system_prompt.lower()

    def test_parse_response_basic(
        self, doc_generator_agent: DocGeneratorAgent
    ) -> None:
        """Verify response parsing with basic content."""
        content = """# My Project

## Overview

This is a test project.

## Installation

Run `npm install`.

## Usage

Import and use the API.
"""

        output = doc_generator_agent._parse_response(content, DocType.README)

        assert output.content == content
        assert output.format == "markdown"
        assert len(output.sections) == 4  # My Project, Overview, Installation, Usage
        assert "My Project" in output.sections
        assert "Overview" in output.sections
        assert "Installation" in output.sections
        assert output.estimated_reading_time >= 1

    def test_parse_response_long_content(
        self, doc_generator_agent: DocGeneratorAgent
    ) -> None:
        """Verify reading time estimation for long content."""
        # Create content with ~400 words (should be ~2 min read at 200 wpm)
        long_content = "# Title\n\n" + " ".join(["word"] * 400)

        output = doc_generator_agent._parse_response(long_content, DocType.README)

        assert output.estimated_reading_time >= 2

    @pytest.mark.asyncio
    async def test_execute_requires_api_key(
        self,
        doc_generator_agent: DocGeneratorAgent,
    ) -> None:
        """Verify execution fails without API key."""
        input_data = DocGeneratorInput(doc_type=DocType.README)
        context = AgentContext(
            workspace_id=uuid4(),
            user_id=uuid4(),
            metadata={},  # No API key
        )

        with pytest.raises(Exception) as exc_info:
            await doc_generator_agent.execute(input_data, context)

        assert "api key" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_execute_validates_input(
        self,
        doc_generator_agent: DocGeneratorAgent,
        agent_context: AgentContext,
    ) -> None:
        """Verify execution validates required fields."""
        input_data = DocGeneratorInput(doc_type=None)  # type: ignore[arg-type]

        with pytest.raises(ValueError) as exc_info:
            await doc_generator_agent.execute(input_data, agent_context)

        assert "required" in str(exc_info.value).lower()


__all__ = ["TestDocGeneratorAgent"]
