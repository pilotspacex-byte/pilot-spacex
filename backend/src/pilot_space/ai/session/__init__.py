"""AI Session Management.

This package handles multi-turn conversation state for agents
that support iterative refinement (e.g., AIContextAgent).

Session Features:
- Redis-backed storage with TTL
- User/workspace scoping
- Cost accumulation tracking
- Automatic expiration (30 minutes)

Sessions are used by ClaudeSDKClient-based agents that need
to maintain conversation history across multiple turns.

References:
- T005: Create ai/session/__init__.py module initialization
- T014: SessionManager class with Redis storage
- specs/004-mvp-agents-build/tasks/P1-T001-T005.md
- docs/architect/claude-agent-sdk-architecture.md
"""

from pilot_space.ai.session.session_manager import (
    SESSION_TTL_SECONDS,
    AIMessage,
    AISession,
    SessionExpiredError,
    SessionManager,
    SessionNotFoundError,
)

__all__ = [
    "SESSION_TTL_SECONDS",
    "AIMessage",
    "AISession",
    "SessionExpiredError",
    "SessionManager",
    "SessionNotFoundError",
]
