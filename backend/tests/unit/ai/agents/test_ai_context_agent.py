"""Unit tests for AIContextAgent.

Tests the new PilotSpaceAgent-delegating AIContextAgent that replaces
the standalone AIContextSubagent (DD-086).

Covers:
- Data class construction and serialization
- Prompt building (generation vs refinement modes)
- Response parsing into AIContextOutput
- Error handling
- SSE text extraction
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from pilot_space.ai.agents.agent_base import AgentContext
from pilot_space.ai.agents.ai_context_agent import (
    AIContextAgent,
    AIContextInput,
    AIContextOutput,
    CodeReference,
    RelatedItem,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def workspace_id() -> UUID:
    return uuid4()


@pytest.fixture
def user_id() -> UUID:
    return uuid4()


@pytest.fixture
def agent_context(workspace_id: UUID, user_id: UUID) -> AgentContext:
    return AgentContext(
        workspace_id=workspace_id,
        user_id=user_id,
        operation_id=None,
        metadata={"correlation_id": "test-123"},
    )


@pytest.fixture
def sample_input(workspace_id: UUID) -> AIContextInput:
    return AIContextInput(
        issue_id=str(uuid4()),
        issue_title="Implement rate limiting",
        issue_description="Add rate limiting middleware to API endpoints",
        issue_identifier="PILOT-42",
        workspace_id=str(workspace_id),
        project_name="Backend",
        related_issues=[
            RelatedItem(
                id=str(uuid4()),
                type="issue",
                title="Add Redis caching",
                relevance_score=0.8,
                excerpt="Implement Redis-based caching for API responses",
                identifier="PILOT-40",
                state="Done",
            ),
        ],
        related_notes=[
            RelatedItem(
                id=str(uuid4()),
                type="note",
                title="Architecture Notes",
                relevance_score=0.6,
                excerpt="Rate limiting design discussion",
            ),
        ],
        code_references=[
            CodeReference(
                file_path="backend/src/middleware/auth.py",
                description="Existing middleware pattern",
                relevance="high",
            ),
        ],
        api_key="test-key-123",
    )


@pytest.fixture
def mock_pilotspace_agent() -> MagicMock:
    agent = MagicMock()
    agent.execute = AsyncMock()
    agent.stream = AsyncMock()
    return agent


@pytest.fixture
def mock_deps() -> dict[str, MagicMock]:
    return {
        "tool_registry": MagicMock(),
        "provider_selector": MagicMock(),
        "cost_tracker": MagicMock(),
        "resilient_executor": MagicMock(),
    }


@pytest.fixture
def agent(mock_pilotspace_agent: MagicMock, mock_deps: dict[str, MagicMock]) -> AIContextAgent:
    return AIContextAgent(
        pilotspace_agent=mock_pilotspace_agent,
        **mock_deps,
    )


# =============================================================================
# Data Class Tests
# =============================================================================


class TestRelatedItem:
    """Test RelatedItem data class."""

    def test_minimal_construction(self) -> None:
        item = RelatedItem(id="123", type="issue", title="Test", relevance_score=0.5)
        assert item.id == "123"
        assert item.type == "issue"
        assert item.excerpt == ""
        assert item.identifier is None
        assert item.state is None

    def test_full_construction(self) -> None:
        item = RelatedItem(
            id="456",
            type="note",
            title="Design Doc",
            relevance_score=0.9,
            excerpt="Important notes",
            identifier="PILOT-10",
            state="In Progress",
        )
        assert item.identifier == "PILOT-10"
        assert item.state == "In Progress"


class TestCodeReference:
    """Test CodeReference data class."""

    def test_minimal_construction(self) -> None:
        ref = CodeReference(file_path="src/main.py")
        assert ref.file_path == "src/main.py"
        assert ref.description == ""
        assert ref.line_range is None
        assert ref.relevance == "medium"

    def test_with_line_range(self) -> None:
        ref = CodeReference(
            file_path="src/api.py",
            description="API handler",
            line_range=(10, 50),
            relevance="high",
        )
        assert ref.line_range == (10, 50)


class TestAIContextInput:
    """Test AIContextInput data class."""

    def test_minimal_construction(self) -> None:
        inp = AIContextInput(
            issue_id="123",
            issue_title="Test",
            issue_description=None,
            issue_identifier="PS-1",
            workspace_id="ws-1",
        )
        assert inp.related_issues == []
        assert inp.related_notes == []
        assert inp.code_references == []
        assert inp.conversation_history == []
        assert inp.refinement_query is None
        assert inp.api_key == ""

    def test_refinement_mode(self) -> None:
        inp = AIContextInput(
            issue_id="123",
            issue_title="Test",
            issue_description="Desc",
            issue_identifier="PS-1",
            workspace_id="ws-1",
            refinement_query="How long would this take?",
            conversation_history=[
                {"role": "assistant", "content": "Previous answer"},
            ],
        )
        assert inp.refinement_query is not None


class TestAIContextOutput:
    """Test AIContextOutput data class."""

    def test_to_content_dict(self) -> None:
        output = AIContextOutput(
            summary="Test summary",
            analysis="Test analysis",
            complexity="medium",
            estimated_effort="M",
            tasks_checklist=[{"id": "task-1", "description": "Do thing"}],
            related_issues=[],
            related_notes=[],
        )
        content = output.to_content_dict()
        assert content == {
            "summary": "Test summary",
            "analysis": "Test analysis",
            "complexity": "medium",
            "estimated_effort": "M",
        }

    def test_defaults(self) -> None:
        output = AIContextOutput(
            summary="s",
            analysis="a",
            complexity="low",
            estimated_effort="S",
            tasks_checklist=[],
            related_issues=[],
            related_notes=[],
        )
        assert output.related_pages == []
        assert output.code_references == []
        assert output.conversation_history == []
        assert output.claude_code_prompt is None


# =============================================================================
# Prompt Building Tests
# =============================================================================


class TestPromptBuilding:
    """Test prompt construction for generation and refinement modes."""

    def test_generation_prompt_includes_skill_prefix(
        self, agent: AIContextAgent, sample_input: AIContextInput
    ) -> None:
        prompt = agent._build_prompt(sample_input)
        assert prompt.startswith("/ai-context")

    def test_generation_prompt_includes_issue_details(
        self, agent: AIContextAgent, sample_input: AIContextInput
    ) -> None:
        prompt = agent._build_prompt(sample_input)
        assert "PILOT-42" in prompt
        assert "Implement rate limiting" in prompt

    def test_generation_prompt_includes_related_issues(
        self, agent: AIContextAgent, sample_input: AIContextInput
    ) -> None:
        prompt = agent._build_prompt(sample_input)
        assert "PILOT-40" in prompt
        assert "Add Redis caching" in prompt

    def test_generation_prompt_includes_code_files(
        self, agent: AIContextAgent, sample_input: AIContextInput
    ) -> None:
        prompt = agent._build_prompt(sample_input)
        assert "backend/src/middleware/auth.py" in prompt

    def test_refinement_prompt_uses_query(
        self, agent: AIContextAgent, sample_input: AIContextInput
    ) -> None:
        sample_input.refinement_query = "How long would this take?"
        sample_input.conversation_history = [
            {"role": "assistant", "content": "Previous context generated."},
        ]
        prompt = agent._build_prompt(sample_input)
        assert "How long would this take?" in prompt
        assert "/ai-context" not in prompt  # Refinement doesn't use skill prefix

    def test_refinement_with_empty_history(
        self, agent: AIContextAgent, sample_input: AIContextInput
    ) -> None:
        sample_input.refinement_query = "More details?"
        sample_input.conversation_history = []
        prompt = agent._build_prompt(sample_input)
        assert "More details?" in prompt


# =============================================================================
# Response Parsing Tests
# =============================================================================


class TestResponseParsing:
    """Test parsing PilotSpaceAgent response into AIContextOutput."""

    def test_parse_valid_json_response(
        self, agent: AIContextAgent, sample_input: AIContextInput
    ) -> None:
        response = """Here is the context:
```json
{
  "summary": "Rate limiting implementation required",
  "analysis": "Need middleware with Redis backend",
  "complexity": "medium",
  "estimated_effort": "M",
  "key_considerations": ["Redis availability"],
  "suggested_approach": "Sliding window pattern",
  "potential_blockers": ["Redis not configured"],
  "tasks": [
    {"id": "task-1", "description": "Create limiter class", "order": 1, "estimated_effort": "M", "dependencies": []}
  ],
  "claude_code_sections": {
    "context": "Adding rate limiting",
    "code_references": ["src/middleware/"],
    "instructions": "Implement sliding window",
    "constraints": "Follow existing patterns"
  }
}
```"""
        output = agent._parse_response(response, sample_input)
        assert output.summary == "Rate limiting implementation required"
        assert output.complexity == "medium"
        assert len(output.tasks_checklist) == 1
        assert output.tasks_checklist[0]["id"] == "task-1"
        assert output.claude_code_prompt is not None
        assert "PILOT-42" in output.claude_code_prompt

    def test_parse_response_preserves_related_items(
        self, agent: AIContextAgent, sample_input: AIContextInput
    ) -> None:
        response = '{"summary": "Test", "analysis": "", "complexity": "low", "estimated_effort": "S", "tasks": [], "claude_code_sections": {}}'
        output = agent._parse_response(response, sample_input)
        assert len(output.related_issues) == 1
        assert output.related_issues[0]["identifier"] == "PILOT-40"
        assert len(output.related_notes) == 1
        assert len(output.code_references) == 1

    def test_parse_response_fallback_on_bad_json(
        self, agent: AIContextAgent, sample_input: AIContextInput
    ) -> None:
        response = "This is just plain text with no JSON at all."
        output = agent._parse_response(response, sample_input)
        assert output.summary == "Unable to generate summary."
        assert output.complexity == "medium"


# =============================================================================
# SSE Text Extraction Tests
# =============================================================================


class TestSSEExtraction:
    """Test extracting text from SSE event chunks."""

    def test_extract_text_delta(self) -> None:
        chunk = 'event: text_delta\ndata: {"delta": "Hello world"}\n\n'
        assert AIContextAgent._extract_text_from_sse(chunk) == "Hello world"

    def test_extract_plain_data(self) -> None:
        chunk = "data: Some plain text\n\n"
        assert AIContextAgent._extract_text_from_sse(chunk) == "Some plain text"

    def test_extract_from_error_event(self) -> None:
        chunk = 'event: error\ndata: {"errorCode": "sdk_error", "message": "fail"}\n\n'
        assert AIContextAgent._extract_text_from_sse(chunk) is None  # No delta or text key

    def test_extract_from_message_stop(self) -> None:
        chunk = 'event: message_stop\ndata: {"stopReason": "end_turn"}\n\n'
        assert AIContextAgent._extract_text_from_sse(chunk) is None

    def test_extract_empty_chunk(self) -> None:
        assert AIContextAgent._extract_text_from_sse("") is None


# =============================================================================
# Agent Run Tests
# =============================================================================


class TestAgentRun:
    """Test AIContextAgent.run() integration with PilotSpaceAgent."""

    @pytest.mark.asyncio
    async def test_run_success(
        self,
        agent: AIContextAgent,
        mock_pilotspace_agent: MagicMock,
        sample_input: AIContextInput,
        agent_context: AgentContext,
    ) -> None:
        mock_pilotspace_agent.execute.return_value = MagicMock(
            response='{"summary": "Test", "analysis": "Analysis", "complexity": "low", "estimated_effort": "S", "tasks": [], "claude_code_sections": {}}',
            session_id=uuid4(),
            metadata={"input_tokens": 100, "output_tokens": 200, "cost_usd": 0.01},
        )

        result = await agent.run(sample_input, agent_context)

        assert result.success is True
        assert result.output is not None
        assert result.output.summary == "Test"
        assert result.output.complexity == "low"
        assert result.input_tokens == 100
        assert result.output_tokens == 200
        mock_pilotspace_agent.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_failure_returns_error(
        self,
        agent: AIContextAgent,
        mock_pilotspace_agent: MagicMock,
        sample_input: AIContextInput,
        agent_context: AgentContext,
    ) -> None:
        mock_pilotspace_agent.execute.side_effect = RuntimeError("SDK connection failed")

        result = await agent.run(sample_input, agent_context)

        assert result.success is False
        assert result.error is not None
        assert "SDK connection failed" in result.error


class TestAgentRunStream:
    """Test AIContextAgent.run_stream() SSE streaming delegation."""

    @pytest.mark.asyncio
    async def test_stream_yields_text_chunks(
        self,
        agent: AIContextAgent,
        mock_pilotspace_agent: MagicMock,
        sample_input: AIContextInput,
        agent_context: AgentContext,
    ) -> None:
        sample_input.refinement_query = "Tell me more"
        sample_input.conversation_history = [
            {"role": "assistant", "content": "Previous answer"},
        ]

        async def mock_stream(*_args: Any, **_kwargs: Any):  # type: ignore[no-untyped-def]
            yield 'event: text_delta\ndata: {"delta": "Here "}\n\n'
            yield 'event: text_delta\ndata: {"delta": "you go"}\n\n'
            yield 'event: message_stop\ndata: {"stopReason": "end_turn"}\n\n'

        mock_pilotspace_agent.stream = mock_stream

        chunks: list[str] = []
        async for chunk in agent.run_stream(sample_input, agent_context):
            chunks.append(chunk)

        assert chunks == ["Here ", "you go"]

    @pytest.mark.asyncio
    async def test_stream_filters_non_text_events(
        self,
        agent: AIContextAgent,
        mock_pilotspace_agent: MagicMock,
        sample_input: AIContextInput,
        agent_context: AgentContext,
    ) -> None:
        sample_input.refinement_query = "More details"

        async def mock_stream(*_args: Any, **_kwargs: Any):  # type: ignore[no-untyped-def]
            yield 'event: message_start\ndata: {"sessionId": "abc"}\n\n'
            yield 'event: text_delta\ndata: {"delta": "Content"}\n\n'
            yield 'event: tool_use\ndata: {"toolName": "search"}\n\n'

        mock_pilotspace_agent.stream = mock_stream

        chunks: list[str] = []
        async for chunk in agent.run_stream(sample_input, agent_context):
            chunks.append(chunk)

        assert chunks == ["Content"]
