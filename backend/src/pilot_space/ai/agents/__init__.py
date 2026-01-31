"""AI agents for Pilot Space.

Architecture (005-conversational-agent-arch):
- PilotSpaceAgent: Unified conversational orchestrator (replaces 13 siloed agents)
- Skills: Lightweight one-shot tasks loaded from filesystem
- Subagents: Complex multi-turn tasks (PR review, AI context, doc generation)

All routing is handled by PilotSpaceAgent via Claude Agent SDK.
"""

from pilot_space.ai.agents.agent_base import (
    AgentContext,
    AgentResult,
    SDKBaseAgent,
    StreamingSDKBaseAgent,
)

__all__ = [
    "AgentContext",
    "AgentResult",
    "SDKBaseAgent",
    "StreamingSDKBaseAgent",
]
