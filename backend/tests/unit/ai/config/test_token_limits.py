"""Tests for token limit configuration.

T318: Token limits configuration tests.
"""

from __future__ import annotations

import pytest

from pilot_space.ai.config.token_limits import (
    AGENT_TOKEN_LIMITS,
    TokenLimit,
    get_all_limits,
    get_token_limit,
    validate_token_request,
)


class TestAgentTokenLimits:
    """Tests for AGENT_TOKEN_LIMITS constant."""

    def test_contains_all_expected_agents(self) -> None:
        """Verify all key agents have token limits defined."""
        expected_agents = [
            "ghost_text",
            "margin_annotation",
            "issue_extractor",
            "pr_review",
            "ai_context",
            "conversation",
            "task_decomposer",
            "doc_generator",
        ]

        for agent in expected_agents:
            assert agent in AGENT_TOKEN_LIMITS, f"Missing token limit for {agent}"

    def test_ghost_text_has_lowest_limit(self) -> None:
        """Verify ghost_text has the lowest token limit (brief suggestions)."""
        ghost_text_limit = AGENT_TOKEN_LIMITS["ghost_text"].max_tokens

        # Should be very low for inline suggestions
        assert ghost_text_limit <= 100

    def test_ai_context_has_highest_limit(self) -> None:
        """Verify ai_context has high token limit (comprehensive analysis)."""
        ai_context_limit = AGENT_TOKEN_LIMITS["ai_context"].max_tokens

        # Should be high for comprehensive context
        assert ai_context_limit >= 8000

    def test_all_limits_have_descriptions(self) -> None:
        """Verify all token limits have rationale descriptions."""
        for agent_name, limit in AGENT_TOKEN_LIMITS.items():
            assert limit.description, f"{agent_name} missing description"
            assert len(limit.description) > 10, f"{agent_name} description too short"

    def test_all_limits_are_positive(self) -> None:
        """Verify all token limits are positive integers."""
        for agent_name, limit in AGENT_TOKEN_LIMITS.items():
            assert limit.max_tokens > 0, f"{agent_name} has non-positive limit"
            assert isinstance(limit.max_tokens, int), f"{agent_name} limit not an integer"


class TestTokenLimit:
    """Tests for TokenLimit dataclass."""

    def test_creates_valid_token_limit(self) -> None:
        """Verify TokenLimit can be created with valid data."""
        limit = TokenLimit(
            max_tokens=1024,
            description="Test agent limit",
        )

        assert limit.max_tokens == 1024
        assert limit.description == "Test agent limit"

    def test_is_immutable(self) -> None:
        """Verify TokenLimit is immutable (frozen dataclass)."""
        limit = TokenLimit(max_tokens=512, description="Test")

        with pytest.raises(AttributeError):
            limit.max_tokens = 1024  # type: ignore[misc]


class TestGetTokenLimit:
    """Tests for get_token_limit function."""

    def test_returns_correct_limit_for_known_agent(self) -> None:
        """Verify returns correct token limit for known agents."""
        ghost_text_limit = get_token_limit("ghost_text")
        assert ghost_text_limit == AGENT_TOKEN_LIMITS["ghost_text"].max_tokens

        pr_review_limit = get_token_limit("pr_review")
        assert pr_review_limit == AGENT_TOKEN_LIMITS["pr_review"].max_tokens

    def test_returns_default_for_unknown_agent(self) -> None:
        """Verify returns default limit for unknown agents."""
        unknown_limit = get_token_limit("unknown_agent")
        assert unknown_limit == 2048  # Default value

    def test_default_is_reasonable_middle_ground(self) -> None:
        """Verify default limit is a reasonable middle ground."""
        default = get_token_limit("unknown_agent")

        # Should be between ghost_text and ai_context
        assert default > AGENT_TOKEN_LIMITS["ghost_text"].max_tokens
        assert default < AGENT_TOKEN_LIMITS["ai_context"].max_tokens


class TestGetAllLimits:
    """Tests for get_all_limits function."""

    def test_returns_all_agent_limits(self) -> None:
        """Verify returns dictionary of all agent limits."""
        all_limits = get_all_limits()

        assert isinstance(all_limits, dict)
        assert len(all_limits) == len(AGENT_TOKEN_LIMITS)

        # Verify all agents are included
        for agent_name in AGENT_TOKEN_LIMITS:
            assert agent_name in all_limits

    def test_returns_only_max_tokens_values(self) -> None:
        """Verify returns only the max_tokens integers, not TokenLimit objects."""
        all_limits = get_all_limits()

        for agent_name, limit in all_limits.items():
            assert isinstance(limit, int), f"{agent_name} limit not an int"
            assert limit > 0


class TestValidateTokenRequest:
    """Tests for validate_token_request function."""

    def test_returns_requested_when_below_limit(self) -> None:
        """Verify returns requested tokens when below agent limit."""
        # ghost_text limit is 50
        result = validate_token_request("ghost_text", 30)
        assert result == 30

    def test_caps_at_agent_limit_when_above(self) -> None:
        """Verify caps at agent limit when requested exceeds it."""
        # ghost_text limit is 50
        result = validate_token_request("ghost_text", 100)
        assert result == AGENT_TOKEN_LIMITS["ghost_text"].max_tokens

    def test_returns_exact_limit_when_equal(self) -> None:
        """Verify returns exact limit when requested equals it."""
        ghost_text_limit = AGENT_TOKEN_LIMITS["ghost_text"].max_tokens
        result = validate_token_request("ghost_text", ghost_text_limit)
        assert result == ghost_text_limit

    def test_uses_default_limit_for_unknown_agent(self) -> None:
        """Verify uses default limit for unknown agents."""
        # Default is 2048
        result = validate_token_request("unknown_agent", 5000)
        assert result == 2048

    def test_handles_zero_requested_tokens(self) -> None:
        """Verify handles edge case of zero requested tokens."""
        result = validate_token_request("ghost_text", 0)
        assert result == 0

    def test_handles_negative_requested_tokens(self) -> None:
        """Verify handles edge case of negative requested tokens."""
        result = validate_token_request("ghost_text", -10)
        assert result == -10  # Returns minimum (though this is invalid input)


class TestTokenLimitReasonableness:
    """Tests to verify token limits are reasonable for their use cases."""

    def test_streaming_agents_have_reasonable_limits(self) -> None:
        """Verify streaming agents have appropriate limits."""
        # Ghost text should be very low (real-time typing)
        assert AGENT_TOKEN_LIMITS["ghost_text"].max_tokens <= 100

        # Margin annotation should be moderate (sidebar comments)
        assert 256 <= AGENT_TOKEN_LIMITS["margin_annotation"].max_tokens <= 1024

    def test_analysis_agents_have_generous_limits(self) -> None:
        """Verify analysis agents have generous limits for comprehensive output."""
        # PR review needs space for multi-dimensional analysis
        assert AGENT_TOKEN_LIMITS["pr_review"].max_tokens >= 4000

        # AI context needs space for aggregation and prompts
        assert AGENT_TOKEN_LIMITS["ai_context"].max_tokens >= 8000

    def test_extraction_agents_have_moderate_limits(self) -> None:
        """Verify extraction agents have moderate limits."""
        # Issue extractor creates structured issues
        assert 1500 <= AGENT_TOKEN_LIMITS["issue_extractor"].max_tokens <= 3000

        # Task decomposer creates hierarchies
        assert 2000 <= AGENT_TOKEN_LIMITS["task_decomposer"].max_tokens <= 4000

    def test_all_limits_are_multiples_of_256(self) -> None:
        """Verify limits are reasonable multiples (easier to tune)."""
        for agent_name, limit in AGENT_TOKEN_LIMITS.items():
            # Most should be multiples of 256 or 512 for easy adjustment
            # Allow some flexibility for very small limits like ghost_text
            if limit.max_tokens >= 256:
                remainder = limit.max_tokens % 256
                assert remainder == 0 or limit.max_tokens % 512 == 0, (
                    f"{agent_name} limit {limit.max_tokens} is not a clean multiple"
                )
