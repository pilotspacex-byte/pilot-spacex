"""Comprehensive mock response library for Anthropic API testing.

Provides realistic mock responses for all Claude Agent SDK event types,
tool executions, and streaming patterns.

Reference: https://github.com/anthropics/claude-agent-sdk
"""

from __future__ import annotations

from typing import Any

# =============================================================================
# STREAMING EVENT MOCKS (SDK Event Types)
# =============================================================================


class MockStreamEvent:
    """Base class for mock SDK stream events."""

    def __init__(self, event_type: str, **kwargs: Any) -> None:
        self.type = event_type
        for key, value in kwargs.items():
            setattr(self, key, value)


def create_message_start_event(session_id: str = "test-session-123") -> MockStreamEvent:
    """Create message_start system event."""
    return MockStreamEvent(
        "system",
        subtype="init",
        session_id=session_id,
    )


def create_text_delta_event(text: str) -> MockStreamEvent:
    """Create text_delta content event."""
    return MockStreamEvent(
        "text_delta",
        delta=text,
    )


def create_thinking_delta_event(thinking: str) -> MockStreamEvent:
    """Create thinking_delta event (extended thinking)."""
    return MockStreamEvent(
        "thinking_delta",
        delta=thinking,
    )


def create_tool_use_event(
    tool_name: str,
    tool_input: dict[str, Any],
    tool_use_id: str = "toolu_123",
) -> MockStreamEvent:
    """Create tool_use event."""
    return MockStreamEvent(
        "tool_use",
        tool_name=tool_name,
        tool_input=tool_input,
        tool_use_id=tool_use_id,
    )


def create_tool_result_event(
    tool_use_id: str,
    result: str | dict[str, Any],
    is_error: bool = False,
) -> MockStreamEvent:
    """Create tool_result event."""
    return MockStreamEvent(
        "tool_result",
        tool_use_id=tool_use_id,
        result=result,
        is_error=is_error,
    )


def create_message_stop_event() -> MockStreamEvent:
    """Create message_stop event."""
    return MockStreamEvent("stop")


# =============================================================================
# CONVERSATION SCENARIO MOCKS
# =============================================================================

MOCK_SCENARIOS = {
    "hello": {
        "description": "Simple greeting conversation",
        "events": [
            create_message_start_event(),
            create_text_delta_event("Hello"),
            create_text_delta_event("!"),
            create_text_delta_event(" I'm"),
            create_text_delta_event(" Claude"),
            create_text_delta_event(","),
            create_text_delta_event(" an"),
            create_text_delta_event(" AI"),
            create_text_delta_event(" assistant"),
            create_text_delta_event("."),
            create_text_delta_event(" How"),
            create_text_delta_event(" can"),
            create_text_delta_event(" I"),
            create_text_delta_event(" help"),
            create_text_delta_event(" you"),
            create_text_delta_event(" today"),
            create_text_delta_event("?"),
            create_message_stop_event(),
        ],
    },
    "fastapi": {
        "description": "Technical explanation about FastAPI",
        "events": [
            create_message_start_event(),
            create_text_delta_event("FastAPI"),
            create_text_delta_event(" is"),
            create_text_delta_event(" a"),
            create_text_delta_event(" modern"),
            create_text_delta_event(","),
            create_text_delta_event(" fast"),
            create_text_delta_event(" ("),
            create_text_delta_event("high"),
            create_text_delta_event("-"),
            create_text_delta_event("performance"),
            create_text_delta_event(")"),
            create_text_delta_event(" web"),
            create_text_delta_event(" framework"),
            create_text_delta_event(" for"),
            create_text_delta_event(" building"),
            create_text_delta_event(" APIs"),
            create_text_delta_event(" with"),
            create_text_delta_event(" Python"),
            create_text_delta_event(" 3"),
            create_text_delta_event("."),
            create_text_delta_event("8"),
            create_text_delta_event("+"),
            create_text_delta_event(" based"),
            create_text_delta_event(" on"),
            create_text_delta_event(" standard"),
            create_text_delta_event(" Python"),
            create_text_delta_event(" type"),
            create_text_delta_event(" hints"),
            create_text_delta_event("."),
            create_message_stop_event(),
        ],
    },
    "with_thinking": {
        "description": "Response with extended thinking",
        "events": [
            create_message_start_event(),
            create_thinking_delta_event("Let me analyze this problem..."),
            create_thinking_delta_event(" I should consider multiple approaches."),
            create_text_delta_event("Based"),
            create_text_delta_event(" on"),
            create_text_delta_event(" my"),
            create_text_delta_event(" analysis"),
            create_text_delta_event(","),
            create_text_delta_event(" I"),
            create_text_delta_event(" recommend"),
            create_text_delta_event("..."),
            create_message_stop_event(),
        ],
    },
    "tool_execution": {
        "description": "Response with Read tool execution",
        "events": [
            create_message_start_event(),
            create_text_delta_event("Let"),
            create_text_delta_event(" me"),
            create_text_delta_event(" read"),
            create_text_delta_event(" the"),
            create_text_delta_event(" file"),
            create_text_delta_event("."),
            create_tool_use_event(
                "Read",
                {"file_path": "/app/src/main.py"},
                "toolu_read_001",
            ),
            create_tool_result_event(
                "toolu_read_001",
                "def main():\n    print('Hello')\n",
            ),
            create_text_delta_event("The"),
            create_text_delta_event(" file"),
            create_text_delta_event(" contains"),
            create_text_delta_event(" a"),
            create_text_delta_event(" simple"),
            create_text_delta_event(" main"),
            create_text_delta_event(" function"),
            create_text_delta_event("."),
            create_message_stop_event(),
        ],
    },
    "multi_tool": {
        "description": "Response with multiple tool executions",
        "events": [
            create_message_start_event(),
            create_text_delta_event("I'll"),
            create_text_delta_event(" search"),
            create_text_delta_event(" for"),
            create_text_delta_event(" the"),
            create_text_delta_event(" files"),
            create_text_delta_event("."),
            create_tool_use_event(
                "Glob",
                {"pattern": "**/*.py"},
                "toolu_glob_001",
            ),
            create_tool_result_event(
                "toolu_glob_001",
                {"files": ["main.py", "utils.py", "tests.py"]},
            ),
            create_text_delta_event("Now"),
            create_text_delta_event(" let"),
            create_text_delta_event(" me"),
            create_text_delta_event(" read"),
            create_text_delta_event(" the"),
            create_text_delta_event(" main"),
            create_text_delta_event(" file"),
            create_text_delta_event("."),
            create_tool_use_event(
                "Read",
                {"file_path": "main.py"},
                "toolu_read_002",
            ),
            create_tool_result_event(
                "toolu_read_002",
                "def main():\n    pass\n",
            ),
            create_text_delta_event("Found"),
            create_text_delta_event(" 3"),
            create_text_delta_event(" Python"),
            create_text_delta_event(" files"),
            create_text_delta_event("."),
            create_message_stop_event(),
        ],
    },
    "skill_extract_issues": {
        "description": "Extract issues skill invocation",
        "events": [
            create_message_start_event(),
            create_text_delta_event("I'll"),
            create_text_delta_event(" extract"),
            create_text_delta_event(" issues"),
            create_text_delta_event(" from"),
            create_text_delta_event(" the"),
            create_text_delta_event(" text"),
            create_text_delta_event("."),
            create_text_delta_event("\n\n"),
            create_text_delta_event("**"),
            create_text_delta_event("Issue"),
            create_text_delta_event(" 1"),
            create_text_delta_event(":**"),
            create_text_delta_event(" Implement"),
            create_text_delta_event(" user"),
            create_text_delta_event(" authentication"),
            create_text_delta_event("\n"),
            create_text_delta_event("-"),
            create_text_delta_event(" **"),
            create_text_delta_event("Confidence"),
            create_text_delta_event(":**"),
            create_text_delta_event(" RECOMMENDED"),
            create_text_delta_event("\n"),
            create_text_delta_event("-"),
            create_text_delta_event(" **"),
            create_text_delta_event("Rationale"),
            create_text_delta_event(":**"),
            create_text_delta_event(" Clear"),
            create_text_delta_event(" implementation"),
            create_text_delta_event(" task"),
            create_text_delta_event(" with"),
            create_text_delta_event(" specific"),
            create_text_delta_event(" requirements"),
            create_text_delta_event("\n"),
            create_text_delta_event("-"),
            create_text_delta_event(" **"),
            create_text_delta_event("Labels"),
            create_text_delta_event(":**"),
            create_text_delta_event(" backend"),
            create_text_delta_event(","),
            create_text_delta_event(" security"),
            create_text_delta_event("\n"),
            create_text_delta_event("-"),
            create_text_delta_event(" **"),
            create_text_delta_event("Priority"),
            create_text_delta_event(":**"),
            create_text_delta_event(" high"),
            create_message_stop_event(),
        ],
    },
    "subagent_delegation": {
        "description": "Subagent spawning via Task tool",
        "events": [
            create_message_start_event(),
            create_text_delta_event("I'll"),
            create_text_delta_event(" spawn"),
            create_text_delta_event(" a"),
            create_text_delta_event(" specialized"),
            create_text_delta_event(" agent"),
            create_text_delta_event(" for"),
            create_text_delta_event(" this"),
            create_text_delta_event("."),
            create_tool_use_event(
                "Task",
                {
                    "description": "Review code for security",
                    "prompt": "Analyze main.py for security vulnerabilities",
                    "subagent_type": "security-analyzer",
                },
                "toolu_task_001",
            ),
            create_tool_result_event(
                "toolu_task_001",
                {
                    "task_id": "task_abc123",
                    "status": "in_progress",
                    "output_file": "/tmp/task_abc123.txt",
                },
            ),
            create_text_delta_event("The"),
            create_text_delta_event(" security"),
            create_text_delta_event(" analyzer"),
            create_text_delta_event(" is"),
            create_text_delta_event(" running"),
            create_text_delta_event("."),
            create_message_stop_event(),
        ],
    },
    "error_handling": {
        "description": "Error during tool execution",
        "events": [
            create_message_start_event(),
            create_text_delta_event("Let"),
            create_text_delta_event(" me"),
            create_text_delta_event(" try"),
            create_text_delta_event(" to"),
            create_text_delta_event(" read"),
            create_text_delta_event(" that"),
            create_text_delta_event("."),
            create_tool_use_event(
                "Read",
                {"file_path": "/nonexistent.txt"},
                "toolu_read_error",
            ),
            create_tool_result_event(
                "toolu_read_error",
                "FileNotFoundError: /nonexistent.txt not found",
                is_error=True,
            ),
            create_text_delta_event("The"),
            create_text_delta_event(" file"),
            create_text_delta_event(" doesn't"),
            create_text_delta_event(" exist"),
            create_text_delta_event("."),
            create_text_delta_event(" I'll"),
            create_text_delta_event(" search"),
            create_text_delta_event(" for"),
            create_text_delta_event(" similar"),
            create_text_delta_event(" files"),
            create_text_delta_event("."),
            create_message_stop_event(),
        ],
    },
}


# =============================================================================
# SKILL-SPECIFIC MOCK RESPONSES
# =============================================================================

SKILL_RESPONSES = {
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
        ],
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
        ],
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


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def get_scenario_events(scenario_name: str) -> list[MockStreamEvent]:
    """Get mock events for a scenario.

    Args:
        scenario_name: Name of scenario (hello, fastapi, tool_execution, etc.)

    Returns:
        List of MockStreamEvent objects
    """
    scenario = MOCK_SCENARIOS.get(scenario_name)
    if not scenario:
        # Default to hello scenario
        scenario = MOCK_SCENARIOS["hello"]

    return scenario["events"]


def get_skill_response(skill_name: str) -> dict[str, Any]:
    """Get mock response for a skill.

    Args:
        skill_name: Name of skill (extract-issues, enhance-issue, etc.)

    Returns:
        Dictionary with skill response data
    """
    return SKILL_RESPONSES.get(skill_name, {})


def match_scenario_from_prompt(prompt: str) -> str:
    """Match appropriate scenario based on prompt content.

    Args:
        prompt: User prompt text

    Returns:
        Scenario name to use for mock response
    """
    prompt_lower = prompt.lower()

    # Skill detection
    if "extract" in prompt_lower and "issue" in prompt_lower:
        return "skill_extract_issues"

    # Tool detection
    if any(word in prompt_lower for word in ["read", "open", "show"]):
        return "tool_execution"

    # Subagent detection
    if any(word in prompt_lower for word in ["@", "agent", "task"]):
        return "subagent_delegation"

    # Technical topics
    if "fastapi" in prompt_lower:
        return "fastapi"

    # Thinking mode (complex questions)
    if any(word in prompt_lower for word in ["analyze", "compare", "evaluate"]):
        return "with_thinking"

    # Multiple operations
    if "and" in prompt_lower or "then" in prompt_lower:
        return "multi_tool"

    # Default greeting
    return "hello"


__all__ = [
    "MOCK_SCENARIOS",
    "SKILL_RESPONSES",
    "MockStreamEvent",
    "create_message_start_event",
    "create_message_stop_event",
    "create_text_delta_event",
    "create_thinking_delta_event",
    "create_tool_result_event",
    "create_tool_use_event",
    "get_scenario_events",
    "get_skill_response",
    "match_scenario_from_prompt",
]
