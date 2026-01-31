"""Unit tests for AIContextAgent.

T203: Test migrated AIContextAgent using Claude Agent SDK.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from pilot_space.ai.agents.ai_context_agent import (
    AIContextAgent,
    AIContextInput,
    AIContextOutput,
    CodeReference,
    RelatedItem,
)
from pilot_space.ai.agents.agent_base import AgentContext


@pytest.fixture
def mock_tool_registry() -> MagicMock:
    """Mock tool registry."""
    return MagicMock()


@pytest.fixture
def mock_provider_selector() -> MagicMock:
    """Mock provider selector."""
    return MagicMock()


@pytest.fixture
def mock_cost_tracker() -> AsyncMock:
    """Mock cost tracker."""
    tracker = AsyncMock()
    tracker.track = AsyncMock(return_value=MagicMock(cost_usd=0.05))
    return tracker


@pytest.fixture
def mock_resilient_executor() -> MagicMock:
    """Mock resilient executor."""
    return MagicMock()


@pytest.fixture
def ai_context_agent(
    mock_tool_registry: MagicMock,
    mock_provider_selector: MagicMock,
    mock_cost_tracker: AsyncMock,
    mock_resilient_executor: MagicMock,
) -> AIContextAgent:
    """Create AIContextAgent instance with mocked dependencies."""
    return AIContextAgent(
        tool_registry=mock_tool_registry,
        provider_selector=mock_provider_selector,
        cost_tracker=mock_cost_tracker,
        resilient_executor=mock_resilient_executor,
    )


@pytest.fixture
def sample_input() -> AIContextInput:
    """Create sample input for testing."""
    return AIContextInput(
        issue_id=str(uuid4()),
        issue_title="Implement authentication service",
        issue_description="Build JWT-based auth with refresh tokens",
        issue_identifier="PILOT-123",
        workspace_id=str(uuid4()),
        project_name="Pilot Space",
        api_key="test-api-key",  # pragma: allowlist secret
        related_issues=[
            RelatedItem(
                id=str(uuid4()),
                type="issue",
                title="Add user registration",
                relevance_score=0.85,
                excerpt="User signup flow",
                identifier="PILOT-100",
                state="completed",
            )
        ],
        related_notes=[
            RelatedItem(
                id=str(uuid4()),
                type="note",
                title="Auth Architecture Notes",
                relevance_score=0.90,
                excerpt="JWT token design decisions...",
            )
        ],
        code_references=[
            CodeReference(
                file_path="src/auth/service.py",
                line_range=(10, 50),
                description="Existing auth scaffolding",
                relevance="high",
            )
        ],
    )


@pytest.fixture
def sample_context() -> AgentContext:
    """Create sample agent context."""
    return AgentContext(
        workspace_id=uuid4(),
        user_id=uuid4(),
        operation_id=uuid4(),
    )


@pytest.fixture
def mock_anthropic_response() -> MagicMock:
    """Create mock Anthropic API response."""
    response = MagicMock()
    response.usage.input_tokens = 1000
    response.usage.output_tokens = 500
    response.content = [
        MagicMock(
            type="text",
            text="""{
  "summary": "Implement JWT-based authentication service with refresh tokens",
  "analysis": "This task requires building secure authentication flows",
  "complexity": "high",
  "estimated_effort": "L",
  "key_considerations": [
    "Token expiration and refresh logic",
    "Secure password hashing",
    "CSRF protection"
  ],
  "suggested_approach": "Use FastAPI dependencies for auth middleware",
  "potential_blockers": [
    "Need to integrate with user database",
    "Rate limiting for login attempts"
  ],
  "tasks": [
    {
      "id": "task-1",
      "description": "Create JWT token generation utility",
      "dependencies": [],
      "estimated_effort": "M",
      "order": 1
    },
    {
      "id": "task-2",
      "description": "Implement refresh token rotation",
      "dependencies": ["task-1"],
      "estimated_effort": "L",
      "order": 2
    }
  ],
  "claude_code_sections": {
    "context": "JWT authentication implementation",
    "code_references": ["src/auth/service.py"],
    "instructions": "Follow OAuth 2.0 best practices",
    "constraints": "Use PyJWT library, no custom crypto"
  }
}""",
        )
    ]
    return response


class TestAIContextAgent:
    """Test suite for AIContextAgent."""

    def test_agent_name_and_model(
        self,
        ai_context_agent: AIContextAgent,
    ) -> None:
        """Verify agent configuration."""
        assert ai_context_agent.AGENT_NAME == "ai_context"
        assert ai_context_agent.DEFAULT_MODEL == "claude-opus-4-5-20251101"

        provider, model = ai_context_agent.get_model()
        assert provider == "anthropic"
        assert model == "claude-opus-4-5-20251101"

    def test_validate_input_success(
        self,
        ai_context_agent: AIContextAgent,
        sample_input: AIContextInput,
    ) -> None:
        """Verify input validation succeeds for valid input."""
        ai_context_agent._validate_input(sample_input)

    def test_validate_input_missing_issue_id(
        self,
        ai_context_agent: AIContextAgent,
    ) -> None:
        """Verify validation fails when issue_id is missing."""
        invalid_input = AIContextInput(
            issue_id="",
            issue_title="Test",
            issue_description=None,
            issue_identifier="PILOT-1",
            workspace_id=str(uuid4()),
            api_key="test-key",  # pragma: allowlist secret
        )

        with pytest.raises(ValueError, match="issue_id is required"):
            ai_context_agent._validate_input(invalid_input)

    def test_validate_input_missing_api_key(
        self,
        ai_context_agent: AIContextAgent,
    ) -> None:
        """Verify validation fails when API key is missing."""
        invalid_input = AIContextInput(
            issue_id=str(uuid4()),
            issue_title="Test",
            issue_description=None,
            issue_identifier="PILOT-1",
            workspace_id=str(uuid4()),
            api_key=None,
        )

        with pytest.raises(ValueError, match="Anthropic API key is required"):
            ai_context_agent._validate_input(invalid_input)

    @pytest.mark.asyncio
    async def test_execute_generation_success(
        self,
        ai_context_agent: AIContextAgent,
        sample_input: AIContextInput,
        sample_context: AgentContext,
        mock_anthropic_response: MagicMock,
    ) -> None:
        """Verify successful context generation."""
        with patch("anthropic.AsyncAnthropic") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_anthropic_response)
            mock_client_class.return_value = mock_client

            output = await ai_context_agent.execute(sample_input, sample_context)

            # Verify output structure
            assert isinstance(output, AIContextOutput)
            assert (
                output.summary == "Implement JWT-based authentication service with refresh tokens"
            )
            assert output.complexity == "high"
            assert output.estimated_effort == "L"
            assert len(output.key_considerations) == 3
            assert len(output.tasks_checklist) == 2
            assert output.claude_code_prompt != ""

            # Verify API was called with correct parameters
            mock_client.messages.create.assert_called_once()
            call_args = mock_client.messages.create.call_args
            assert call_args.kwargs["model"] == "claude-opus-4-5-20251101"
            assert call_args.kwargs["max_tokens"] == 4096

    @pytest.mark.asyncio
    async def test_execute_refinement_success(
        self,
        ai_context_agent: AIContextAgent,
        sample_input: AIContextInput,
        sample_context: AgentContext,
    ) -> None:
        """Verify successful context refinement."""
        # Add refinement query to input
        sample_input.refinement_query = "Can you add more detail about CSRF protection?"
        sample_input.conversation_history = [
            {
                "role": "user",
                "content": "Generate context",
                "timestamp": "2026-01-26T10:00:00Z",
            },
            {
                "role": "assistant",
                "content": "Here is the context...",
                "timestamp": "2026-01-26T10:00:05Z",
            },
        ]

        # Mock response
        mock_response = MagicMock()
        mock_response.usage.input_tokens = 800
        mock_response.usage.output_tokens = 300
        mock_response.content = [
            MagicMock(
                type="text",
                text="CSRF protection should use SameSite cookies and token validation...",
            )
        ]

        with patch("anthropic.AsyncAnthropic") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            output = await ai_context_agent.execute(sample_input, sample_context)

            # Verify output
            assert isinstance(output, AIContextOutput)
            assert len(output.conversation_history) == 4  # 2 existing + 2 new
            assert output.conversation_history[-2]["role"] == "user"
            assert output.conversation_history[-2]["content"] == sample_input.refinement_query
            assert output.conversation_history[-1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_stream_success(
        self,
        ai_context_agent: AIContextAgent,
        sample_input: AIContextInput,
        sample_context: AgentContext,
    ) -> None:
        """Verify streaming works correctly."""
        sample_input.refinement_query = "Tell me more about JWT tokens"

        # Mock streaming response
        async def mock_text_stream():
            """Mock async text stream."""
            chunks = ["JWT ", "tokens ", "are ", "used ", "for ", "authentication"]
            for chunk in chunks:
                yield chunk

        mock_stream_context = MagicMock()
        mock_stream_context.text_stream = mock_text_stream()
        mock_stream_context.__aenter__ = AsyncMock(return_value=mock_stream_context)
        mock_stream_context.__aexit__ = AsyncMock(return_value=None)

        with patch("anthropic.AsyncAnthropic") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.messages.stream = MagicMock(return_value=mock_stream_context)
            mock_client_class.return_value = mock_client

            chunks: list[str] = []
            async for chunk in ai_context_agent.stream(sample_input, sample_context):
                chunks.append(chunk)

            # Verify all chunks received
            assert len(chunks) == 6
            assert "".join(chunks) == "JWT tokens are used for authentication"

    @pytest.mark.asyncio
    async def test_stream_without_refinement_query_fails(
        self,
        ai_context_agent: AIContextAgent,
        sample_input: AIContextInput,
        sample_context: AgentContext,
    ) -> None:
        """Verify streaming fails without refinement query."""
        # Don't set refinement_query
        sample_input.refinement_query = None

        with pytest.raises(ValueError, match="refinement_query is required for streaming"):
            async for _ in ai_context_agent.stream(sample_input, sample_context):
                pass


class TestRelatedItem:
    """Test RelatedItem data class."""

    def test_to_dict(self) -> None:
        """Verify to_dict conversion."""
        item = RelatedItem(
            id=str(uuid4()),
            type="issue",
            title="Test Issue",
            relevance_score=0.75,
            excerpt="Test excerpt",
            identifier="PILOT-1",
            state="open",
        )

        result = item.to_dict()

        assert result["type"] == "issue"
        assert result["title"] == "Test Issue"
        assert result["relevance_score"] == 0.75
        assert result["identifier"] == "PILOT-1"
        assert result["state"] == "open"


class TestCodeReference:
    """Test CodeReference data class."""

    def test_to_dict_with_line_range(self) -> None:
        """Verify to_dict with line range."""
        ref = CodeReference(
            file_path="src/main.py",
            line_range=(10, 20),
            description="Main function",
            relevance="high",
        )

        result = ref.to_dict()

        assert result["file_path"] == "src/main.py"
        assert result["line_start"] == 10
        assert result["line_end"] == 20
        assert result["description"] == "Main function"
        assert result["relevance"] == "high"

    def test_to_dict_without_line_range(self) -> None:
        """Verify to_dict without line range."""
        ref = CodeReference(
            file_path="src/utils.py",
            description="Utility module",
        )

        result = ref.to_dict()

        assert result["file_path"] == "src/utils.py"
        assert result["line_start"] is None
        assert result["line_end"] is None
        assert result["description"] == "Utility module"


class TestAIContextOutput:
    """Test AIContextOutput data class."""

    def test_to_content_dict(self) -> None:
        """Verify to_content_dict conversion."""
        output = AIContextOutput(
            summary="Test summary",
            analysis="Test analysis",
            complexity="medium",
            estimated_effort="M",
            key_considerations=["Point 1", "Point 2"],
            suggested_approach="Use FastAPI",
            potential_blockers=["Blocker 1"],
        )

        result = output.to_content_dict()

        assert result["summary"] == "Test summary"
        assert result["analysis"] == "Test analysis"
        assert result["complexity"] == "medium"
        assert result["estimated_effort"] == "M"
        assert result["model_used"] == "claude-opus-4-5-20251101"
        assert "generation_timestamp" in result
