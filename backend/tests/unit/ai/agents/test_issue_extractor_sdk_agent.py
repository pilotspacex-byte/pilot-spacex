"""Unit tests for IssueExtractorAgent SDK implementation.

T060: Unit tests with confidence tag validation.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from pilot_space.ai.agents.issue_extractor_sdk_agent import (
    ConfidenceTag,
    ExtractedIssue,
    IssueExtractorAgent,
    IssueExtractorInput,
    IssueExtractorOutput,
)
from pilot_space.ai.agents.sdk_base import AgentContext


@pytest.fixture
def agent_deps():
    """Create mock dependencies for agent."""
    return {
        "tool_registry": MagicMock(),
        "provider_selector": MagicMock(
            select=MagicMock(return_value=("anthropic", "claude-sonnet-4-20250514"))
        ),
        "cost_tracker": MagicMock(
            track=AsyncMock(
                return_value=MagicMock(cost_usd=0.05, input_tokens=100, output_tokens=200)
            )
        ),
        "resilient_executor": MagicMock(
            execute=AsyncMock(side_effect=lambda operation: operation())
        ),
        "key_storage": AsyncMock(get_api_key=AsyncMock(return_value="test-api-key-123")),
    }


@pytest.fixture
def context():
    """Create agent context."""
    return AgentContext(
        workspace_id=uuid4(),
        user_id=uuid4(),
    )


@pytest.fixture
def input_data():
    """Create input data."""
    return IssueExtractorInput(
        note_id=uuid4(),
        project_id=uuid4(),
        max_issues=5,
        min_confidence=0.5,
    )


class TestIssueExtractorAgent:
    """Test suite for IssueExtractorAgent."""

    @pytest.mark.asyncio
    @patch("pilot_space.ai.agents.issue_extractor_sdk_agent.AsyncAnthropic")
    async def test_extracts_issues_with_confidence_tags(
        self, mock_anthropic_cls, agent_deps, context, input_data
    ):
        """Verify extraction with all confidence tag types."""
        # Mock Anthropic API response with multiple confidence levels
        response_text = json.dumps(
            {
                "issues": [
                    {
                        "title": "Fix login error",
                        "description": "Users see 500 error on login",
                        "labels": ["bug"],
                        "priority": 1,
                        "confidence_tag": "recommended",
                        "confidence_score": 0.95,
                        "source_block_ids": ["block-1"],
                        "rationale": "Clear error report with reproduction steps",
                    },
                    {
                        "title": "Improve search performance",
                        "description": "Search could be faster for large datasets",
                        "labels": ["enhancement"],
                        "priority": 2,
                        "confidence_tag": "default",
                        "confidence_score": 0.7,
                        "source_block_ids": ["block-2"],
                        "rationale": "Performance improvement suggestion",
                    },
                    {
                        "title": "Consider dark mode",
                        "description": "Maybe we should add dark mode support?",
                        "labels": ["feature"],
                        "priority": 3,
                        "confidence_tag": "alternative",
                        "confidence_score": 0.5,
                        "source_block_ids": ["block-3"],
                        "rationale": "Speculative feature that needs stakeholder input",
                    },
                ],
                "extraction_summary": "Found 3 issues: 1 bug, 1 enhancement, 1 feature",
            }
        )

        mock_response = MagicMock(
            content=[MagicMock(text=response_text)],
            usage=MagicMock(input_tokens=100, output_tokens=200),
        )

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic_cls.return_value = mock_client

        agent = IssueExtractorAgent(**agent_deps)
        result = await agent.execute(input_data, context)

        # Verify all issues extracted
        assert len(result.issues) == 3
        assert result.total_count == 3
        assert result.recommended_count == 1

        # Verify confidence tags
        assert result.issues[0].confidence_tag == ConfidenceTag.RECOMMENDED
        assert result.issues[0].confidence_score == 0.95
        assert result.issues[1].confidence_tag == ConfidenceTag.DEFAULT
        assert result.issues[1].confidence_score == 0.7
        assert result.issues[2].confidence_tag == ConfidenceTag.ALTERNATIVE
        assert result.issues[2].confidence_score == 0.5

        # Verify Anthropic client was called with system prompt
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["model"] == "claude-sonnet-4-20250514"
        assert "system" in call_kwargs
        assert "RECOMMENDED" in call_kwargs["system"]
        assert len(call_kwargs["messages"]) == 1
        assert call_kwargs["messages"][0]["role"] == "user"

    @pytest.mark.asyncio
    @patch("pilot_space.ai.agents.issue_extractor_sdk_agent.AsyncAnthropic")
    async def test_parses_json_from_markdown_code_block(
        self, mock_anthropic_cls, agent_deps, context, input_data
    ):
        """Verify JSON extraction from markdown code block."""
        response_text = """Here are the extracted issues:

```json
{
  "issues": [
    {
      "title": "Test Issue",
      "description": "Test description",
      "labels": ["test"],
      "priority": 2,
      "confidence_tag": "default",
      "confidence_score": 0.6,
      "source_block_ids": ["block-1"],
      "rationale": "Test rationale"
    }
  ],
  "extraction_summary": "Found 1 issue"
}
```

Let me know if you need any adjustments!"""

        mock_response = MagicMock(
            content=[MagicMock(text=response_text)],
            usage=MagicMock(input_tokens=100, output_tokens=200),
        )

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic_cls.return_value = mock_client

        agent = IssueExtractorAgent(**agent_deps)
        result = await agent.execute(input_data, context)

        assert len(result.issues) == 1
        assert result.issues[0].title == "Test Issue"
        assert result.issues[0].confidence_tag == ConfidenceTag.DEFAULT

    @pytest.mark.asyncio
    @patch("pilot_space.ai.agents.issue_extractor_sdk_agent.AsyncAnthropic")
    async def test_handles_missing_confidence_tag(
        self, mock_anthropic_cls, agent_deps, context, input_data
    ):
        """Verify fallback to score-based tag when tag is missing."""
        response_text = json.dumps(
            {
                "issues": [
                    {
                        "title": "Issue without tag",
                        "description": "Test",
                        "labels": [],
                        "priority": 2,
                        "confidence_score": 0.85,  # Should be RECOMMENDED
                        "source_block_ids": [],
                        "rationale": "Test",
                    }
                ],
                "extraction_summary": "Found 1 issue",
            }
        )

        mock_response = MagicMock(
            content=[MagicMock(text=response_text)],
            usage=MagicMock(input_tokens=100, output_tokens=200),
        )

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic_cls.return_value = mock_client

        agent = IssueExtractorAgent(**agent_deps)
        result = await agent.execute(input_data, context)

        assert len(result.issues) == 1
        # Should fallback to RECOMMENDED based on score >= 0.8
        assert result.issues[0].confidence_tag == ConfidenceTag.RECOMMENDED

    @pytest.mark.asyncio
    @patch("pilot_space.ai.agents.issue_extractor_sdk_agent.AsyncAnthropic")
    async def test_handles_invalid_json(self, mock_anthropic_cls, agent_deps, context, input_data):
        """Verify graceful handling of invalid JSON response."""
        mock_response = MagicMock(
            content=[MagicMock(text="This is not valid JSON at all!")],
            usage=MagicMock(input_tokens=100, output_tokens=200),
        )

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic_cls.return_value = mock_client

        agent = IssueExtractorAgent(**agent_deps)
        result = await agent.execute(input_data, context)

        # Should return empty result
        assert len(result.issues) == 0
        assert "Failed to parse response" in result.extraction_summary

    @pytest.mark.asyncio
    @patch("pilot_space.ai.agents.issue_extractor_sdk_agent.AsyncAnthropic")
    async def test_tracks_token_usage(self, mock_anthropic_cls, agent_deps, context, input_data):
        """Verify token usage is tracked."""
        response_text = json.dumps({"issues": [], "extraction_summary": "No issues found"})

        mock_response = MagicMock(
            content=[MagicMock(text=response_text)],
            usage=MagicMock(input_tokens=150, output_tokens=50),
        )

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic_cls.return_value = mock_client

        agent = IssueExtractorAgent(**agent_deps)
        await agent.execute(input_data, context)

        # Verify cost tracker was called
        agent_deps["cost_tracker"].track.assert_called_once()
        call_kwargs = agent_deps["cost_tracker"].track.call_args.kwargs
        assert call_kwargs["input_tokens"] == 150
        assert call_kwargs["output_tokens"] == 50

    def test_system_prompt_includes_confidence_definitions(self, agent_deps):
        """Verify system prompt includes DD-048 confidence definitions."""
        agent = IssueExtractorAgent(**agent_deps)
        prompt = agent._get_system_prompt()

        assert "RECOMMENDED" in prompt
        assert "DEFAULT" in prompt
        assert "CURRENT" in prompt
        assert "ALTERNATIVE" in prompt
        assert "DD-048" not in prompt  # Don't leak internal references
        assert "confidence_tag" in prompt
        assert "confidence_score" in prompt

    def test_build_prompt_includes_parameters(self, agent_deps):
        """Verify prompt includes all input parameters."""
        agent = IssueExtractorAgent(**agent_deps)
        input_data = IssueExtractorInput(
            note_id=uuid4(),
            project_id=uuid4(),
            max_issues=10,
            min_confidence=0.6,
        )

        prompt = agent._build_prompt(input_data)

        assert str(input_data.note_id) in prompt
        assert str(input_data.project_id) in prompt
        assert "10" in prompt  # max_issues
        assert "0.6" in prompt  # min_confidence

    @pytest.mark.asyncio
    @patch("pilot_space.ai.agents.issue_extractor_sdk_agent.AsyncAnthropic")
    async def test_handles_sdk_exception(self, mock_anthropic_cls, agent_deps, context, input_data):
        """Verify graceful handling of API exceptions."""
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(side_effect=Exception("API connection error"))
        mock_anthropic_cls.return_value = mock_client

        agent = IssueExtractorAgent(**agent_deps)
        result = await agent.execute(input_data, context)

        # Should return empty result with error message
        assert len(result.issues) == 0
        assert "Extraction failed" in result.extraction_summary


class TestExtractedIssue:
    """Test suite for ExtractedIssue dataclass."""

    def test_to_dict_conversion(self):
        """Verify to_dict produces correct structure."""
        issue = ExtractedIssue(
            title="Test Issue",
            description="Test description",
            labels=["bug", "high-priority"],
            priority=1,
            confidence_tag=ConfidenceTag.RECOMMENDED,
            confidence_score=0.9,
            source_block_ids=["block-1", "block-2"],
            rationale="Clear bug report",
        )

        result = issue.to_dict()

        assert result["title"] == "Test Issue"
        assert result["description"] == "Test description"
        assert result["labels"] == ["bug", "high-priority"]
        assert result["priority"] == 1
        assert result["confidence_tag"] == "recommended"
        assert result["confidence_score"] == 0.9
        assert result["source_block_ids"] == ["block-1", "block-2"]
        assert result["rationale"] == "Clear bug report"


class TestIssueExtractorOutput:
    """Test suite for IssueExtractorOutput dataclass."""

    def test_recommended_count(self):
        """Verify recommended_count property."""
        output = IssueExtractorOutput(
            issues=[
                ExtractedIssue(
                    title="High",
                    description="",
                    labels=[],
                    priority=1,
                    confidence_tag=ConfidenceTag.RECOMMENDED,
                    confidence_score=0.9,
                    source_block_ids=[],
                    rationale="",
                ),
                ExtractedIssue(
                    title="Medium",
                    description="",
                    labels=[],
                    priority=2,
                    confidence_tag=ConfidenceTag.DEFAULT,
                    confidence_score=0.7,
                    source_block_ids=[],
                    rationale="",
                ),
                ExtractedIssue(
                    title="High2",
                    description="",
                    labels=[],
                    priority=1,
                    confidence_tag=ConfidenceTag.RECOMMENDED,
                    confidence_score=0.85,
                    source_block_ids=[],
                    rationale="",
                ),
            ]
        )

        assert output.recommended_count == 2
        assert output.total_count == 3
