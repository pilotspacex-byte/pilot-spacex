"""Mock fixtures for Anthropic API responses.

Provides fixtures for testing without requiring real Anthropic API keys.
Uses respx to mock HTTP requests made by the Claude Agent SDK.

Reference: claude-agent-sdk uses httpx internally to call Anthropic API.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, patch

import pytest
import respx
from httpx import Response

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


# Mock Anthropic API responses for common scenarios
MOCK_CHAT_RESPONSES = {
    "hello": {
        "id": "msg_01ABC123",
        "type": "message",
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "Hello! I'm Claude, an AI assistant. How can I help you today?",
            }
        ],
        "model": "claude-sonnet-4-20250514",
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {"input_tokens": 10, "output_tokens": 20},
    },
    "what_is_fastapi": {
        "id": "msg_02DEF456",
        "type": "message",
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "FastAPI is a modern, fast (high-performance) web framework for building APIs with Python 3.8+ based on standard Python type hints.",
            }
        ],
        "model": "claude-sonnet-4-20250514",
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {"input_tokens": 15, "output_tokens": 35},
    },
    "extract_issues": {
        "id": "msg_03GHI789",
        "type": "message",
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "Based on the note content, I've identified the following issues:\n\n1. **Implement user authentication** (RECOMMENDED)\n   - Description: Add OAuth2 authentication to the application\n   - Priority: High\n   - Labels: backend, security\n\n2. **Set up JWT token handling** (RECOMMENDED)\n   - Description: Configure JWT tokens with refresh token support\n   - Priority: High\n   - Labels: backend, security",
            }
        ],
        "model": "claude-sonnet-4-20250514",
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {"input_tokens": 50, "output_tokens": 120},
    },
}

# Mock streaming responses (SSE format)
MOCK_STREAMING_CHUNKS = {
    "hello": [
        {
            "type": "message_start",
            "message": {"id": "msg_01ABC123", "type": "message", "role": "assistant"},
        },
        {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": "Hello"},
        },
        {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "!"}},
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": " I'm"},
        },
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": " Claude"},
        },
        {"type": "content_block_stop", "index": 0},
        {"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence": None}},
        {"type": "message_stop"},
    ],
    "what_is_fastapi": [
        {
            "type": "message_start",
            "message": {"id": "msg_02DEF456", "type": "message", "role": "assistant"},
        },
        {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": "FastAPI"},
        },
        {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": " is"}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": " a"}},
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": " modern"},
        },
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": " web"},
        },
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": " framework"},
        },
        {"type": "content_block_stop", "index": 0},
        {"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence": None}},
        {"type": "message_stop"},
    ],
}


@pytest.fixture
def mock_anthropic_api(respx_mock: respx.MockRouter) -> respx.MockRouter:
    """Mock Anthropic API endpoints.

    Uses respx to intercept HTTP requests to api.anthropic.com and return
    predefined responses for testing without requiring real API keys.

    Args:
        respx_mock: respx mock router (auto-injected by respx pytest plugin).

    Returns:
        Configured respx mock router.

    Example:
        async def test_chat(mock_anthropic_api):
            # Anthropic API calls will be mocked automatically
            response = await client.post("/api/v1/ai/chat", json={"message": "Hello"})
            assert response.status_code == 200
    """
    # Mock non-streaming chat completion
    respx_mock.post("https://api.anthropic.com/v1/messages").mock(
        return_value=Response(
            200,
            json=MOCK_CHAT_RESPONSES["hello"],
            headers={"content-type": "application/json"},
        )
    )

    # Mock streaming chat completion
    respx_mock.post("https://api.anthropic.com/v1/messages").mock(
        return_value=Response(
            200,
            content=_generate_sse_stream(MOCK_STREAMING_CHUNKS["hello"]),
            headers={"content-type": "text/event-stream"},
        )
    )

    return respx_mock


@pytest.fixture
def mock_anthropic_streaming() -> AsyncGenerator[AsyncMock, None]:
    """Mock Claude Agent SDK ClaudeSDKClient streaming responses.

    Patches ClaudeSDKClient to return mock streaming events
    instead of spawning a real subprocess.

    Yields:
        AsyncMock of ClaudeSDKClient with simulated streaming events.

    Example:
        async def test_streaming(mock_anthropic_streaming):
            client = ClaudeSDKClient(options)
            await client.connect()
            await client.send_message("Hello")
            async for message in client.receive_messages():
                assert message  # Mock events will be yielded
    """
    mock_events = [
        type("StreamEvent", (), {"type": "text_delta", "delta": "Hello"}),
        type("StreamEvent", (), {"type": "text_delta", "delta": "!"}),
        type("StreamEvent", (), {"type": "text_delta", "delta": " I'm"}),
        type("StreamEvent", (), {"type": "text_delta", "delta": " Claude"}),
        type("StreamEvent", (), {"type": "stop"}),
    ]

    async def mock_receive_messages() -> AsyncGenerator[Any, None]:
        for event in mock_events:
            yield event

    mock_client = AsyncMock()
    mock_client.connect = AsyncMock()
    mock_client.disconnect = AsyncMock()
    mock_client.query = AsyncMock()
    mock_client.receive_response = mock_receive_messages
    mock_client.receive_messages = mock_receive_messages
    mock_client.interrupt = AsyncMock()

    with patch("claude_agent_sdk.ClaudeSDKClient", return_value=mock_client):
        yield mock_client


@pytest.fixture
def mock_anthropic_skill_responses() -> dict[str, dict[str, Any]]:
    """Mock responses for skill invocations.

    Returns:
        Dictionary mapping skill names to mock responses.

    Example:
        def test_extract_issues(mock_anthropic_skill_responses):
            expected = mock_anthropic_skill_responses["extract-issues"]
            # Use expected response for assertions
    """
    return {
        "extract-issues": {
            "issues": [
                {
                    "name": "Implement user authentication",
                    "description": "Add OAuth2 authentication to the application",
                    "confidence": "RECOMMENDED",
                    "rationale": "Clear implementation task with specific requirements",
                    "labels": ["backend", "security"],
                    "priority": "high",
                },
                {
                    "name": "Set up JWT token handling",
                    "description": "Configure JWT tokens with refresh token support",
                    "confidence": "RECOMMENDED",
                    "rationale": "Required for authentication flow",
                    "labels": ["backend", "security"],
                    "priority": "high",
                },
            ]
        },
        "enhance-issue": {
            "enhanced_description": "Add OAuth2 authentication with support for Google, GitHub, and email/password login. Implement JWT tokens with 15-minute expiry and refresh tokens with 7-day expiry.",
            "labels": ["backend", "security", "authentication"],
            "priority": "high",
            "confidence": "RECOMMENDED",
            "rationale": "Security-critical feature with clear scope",
        },
        "recommend-assignee": {
            "user_id": "user-123",
            "user_email": "alice@example.com",
            "confidence": "RECOMMENDED",
            "rationale": "Primary backend engineer, authored 80% of auth module",
            "expertise_match": 0.92,
        },
        "find-duplicates": {
            "duplicates": [],
            "confidence": "RECOMMENDED",
            "rationale": "No similar issues found in workspace",
        },
        "decompose-tasks": {
            "tasks": [
                {
                    "name": "Set up Supabase Auth",
                    "description": "Configure Supabase Auth with OAuth providers",
                    "confidence": "RECOMMENDED",
                    "dependencies": [],
                },
                {
                    "name": "Implement JWT token handling",
                    "description": "Add JWT token generation and validation",
                    "confidence": "RECOMMENDED",
                    "dependencies": ["Set up Supabase Auth"],
                },
                {
                    "name": "Add authentication middleware",
                    "description": "Protect API endpoints with auth middleware",
                    "confidence": "RECOMMENDED",
                    "dependencies": ["Implement JWT token handling"],
                },
            ]
        },
        "generate-diagram": {
            "diagram": """```mermaid
graph TD
    A[User] -->|Login Request| B[Auth Service]
    B -->|Validate| C[Supabase Auth]
    C -->|Generate| D[JWT Token]
    D -->|Return| A
```""",
            "confidence": "RECOMMENDED",
            "rationale": "Standard authentication flow diagram",
        },
        "improve-writing": {
            "improved_text": "Implement OAuth2 authentication with support for multiple identity providers (Google, GitHub, email/password). Configure JWT tokens with secure expiry times and implement refresh token rotation.",
            "confidence": "RECOMMENDED",
            "rationale": "Enhanced clarity and specificity",
        },
        "summarize": {
            "summary": "Add authentication feature with OAuth2 support for Google and GitHub, plus email/password login. Use JWT tokens with refresh token rotation for secure session management.",
            "confidence": "RECOMMENDED",
            "format": "brief",
        },
    }


def _generate_sse_stream(chunks: list[dict[str, Any]]) -> bytes:
    """Generate SSE stream from chunks.

    Args:
        chunks: List of SSE event dictionaries.

    Returns:
        Bytes representing SSE stream.
    """
    import json

    lines = []
    for chunk in chunks:
        event_type = chunk.get("type", "message")
        lines.append(f"event: {event_type}\n")
        lines.append(f"data: {json.dumps(chunk)}\n\n")

    return "".join(lines).encode()


@pytest.fixture
async def mock_claude_sdk_demo_mode() -> AsyncGenerator[None, None]:
    """Enable demo mode for Claude Agent SDK.

    Patches the SDK to use mock responses instead of real API calls.
    This allows running E2E tests without ANTHROPIC_API_KEY configured.

    Uses comprehensive mock response library from mock_responses.py.

    Example:
        async def test_chat_flow(mock_claude_sdk_demo_mode, e2e_client):
            # SDK will use mock responses automatically
            response = await e2e_client.post("/api/v1/ai/chat", json={"message": "Hello"})
            assert response.status_code == 200
    """
    import os

    from tests.fixtures.mock_responses import get_scenario_events, match_scenario_from_prompt

    async def mock_query_stream(prompt: str, options: Any = None) -> AsyncGenerator[Any, None]:
        """Mock query function that yields streaming events."""
        # Match scenario based on prompt content
        scenario_name = match_scenario_from_prompt(prompt)
        events = get_scenario_events(scenario_name)

        # Yield all events for the matched scenario
        for event in events:
            yield event

    # Set ANTHROPIC_API_KEY environment variable to avoid API key errors
    original_api_key = os.getenv("ANTHROPIC_API_KEY")
    os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test-mock-key-for-e2e-testing"

    # Patch where query is actually used (in PilotSpaceAgent module)
    with patch("pilot_space.ai.agents.pilotspace_agent.query", side_effect=mock_query_stream):
        yield

    # Restore original API key
    if original_api_key:
        os.environ["ANTHROPIC_API_KEY"] = original_api_key
    elif "ANTHROPIC_API_KEY" in os.environ:
        del os.environ["ANTHROPIC_API_KEY"]


__all__ = [
    "MOCK_CHAT_RESPONSES",
    "MOCK_STREAMING_CHUNKS",
    "mock_anthropic_api",
    "mock_anthropic_skill_responses",
    "mock_anthropic_streaming",
    "mock_claude_sdk_demo_mode",
]
