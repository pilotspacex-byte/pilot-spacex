"""Specialized subagents for complex multi-turn tasks.

Subagents provide interactive, conversational interfaces for complex
AI tasks that benefit from multi-turn dialogue and streaming responses.

All subagents inherit from StreamingSDKBaseAgent and use ClaudeSDKClient
for streaming SSE responses.

Reference: docs/architect/ai-layer.md
Design Decision: DD-058 (SDK mode selection)

Available Subagents:
- PRReviewSubagent: Interactive code review with architecture/security/performance analysis
- AIContextSubagent: Conversational issue context aggregation
- DocGeneratorSubagent: Interactive documentation generation

Usage:
    from pilot_space.ai.agents.subagents import PRReviewSubagent

    subagent = PRReviewSubagent(...)
    async for chunk in subagent.execute_stream(input_data, context):
        yield chunk  # Stream to client via SSE
"""

from pilot_space.ai.agents.subagents.ai_context_subagent import AIContextSubagent
from pilot_space.ai.agents.subagents.doc_generator_subagent import DocGeneratorSubagent
from pilot_space.ai.agents.subagents.pr_review_subagent import PRReviewSubagent

__all__ = [
    "AIContextSubagent",
    "DocGeneratorSubagent",
    "PRReviewSubagent",
]
