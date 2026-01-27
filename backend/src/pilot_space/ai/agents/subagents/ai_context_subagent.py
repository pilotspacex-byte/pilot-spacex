"""AI Context Subagent for interactive issue context aggregation.

Provides conversational interface for:
- Related document discovery
- Code snippet retrieval
- Task breakdown suggestions
- Dependency identification

Reference: docs/architect/ai-layer.md
Design Decision: DD-055 (AI Context Architecture)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pilot_space.ai.agents.sdk_base import AgentContext, StreamingSDKBaseAgent

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@dataclass
class AIContextInput:
    """Input for AI context subagent.

    Attributes:
        issue_id: Issue UUID to build context for
        include_code: Include related code snippets
        include_docs: Include related documentation
        include_tasks: Include task breakdown
    """

    issue_id: UUID
    include_code: bool = True
    include_docs: bool = True
    include_tasks: bool = True


@dataclass
class AIContextOutput:
    """Output from AI context aggregation.

    Attributes:
        summary: Context summary
        related_documents: Related notes and documents
        code_snippets: Relevant code snippets with explanations
        task_breakdown: Suggested task decomposition
        dependencies: Issue dependencies identified
    """

    summary: str
    related_documents: list[dict[str, Any]]
    code_snippets: list[dict[str, Any]]
    task_breakdown: list[dict[str, Any]]
    dependencies: list[dict[str, Any]]


class AIContextSubagent(StreamingSDKBaseAgent[AIContextInput, AIContextOutput]):
    """Subagent for interactive AI context conversations.

    Provides multi-turn context building with semantic search,
    code analysis, and task planning.

    Usage:
        subagent = AIContextSubagent(...)
        async for chunk in subagent.execute_stream(input_data, context):
            yield chunk
    """

    AGENT_NAME = "ai_context_subagent"
    DEFAULT_MODEL = "claude-sonnet-4-20250514"

    def get_system_prompt(self) -> str:
        """Get system prompt for AI context.

        Returns:
            System prompt string with context guidelines
        """
        return """You are an AI assistant helping developers understand issue context.

Your role:
1. **Discover Related Content**: Find relevant notes, docs, code, issues
2. **Explain Connections**: Clarify how pieces relate to current issue
3. **Suggest Tasks**: Break down issue into actionable subtasks
4. **Identify Dependencies**: Find blocking issues or prerequisites

Use available tools to:
- Search semantic knowledge base for related content
- Query codebase for relevant implementations
- Find similar resolved issues for reference
- Retrieve linked PRs and commits

Format responses:
- Use bullet points for lists
- Include file paths and line numbers for code
- Provide clickable issue/PR references
- Highlight confidence level (RECOMMENDED | DEFAULT | CURRENT | ALTERNATIVE)

Be concise but thorough. Focus on actionable insights."""

    def get_tools(self) -> list[dict[str, Any]]:
        """Get MCP tools for AI context.

        Returns:
            List of tool definitions for search and analysis
        """
        return [
            {
                "name": "search_related_notes",
                "description": "Search for related notes using semantic similarity",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "limit": {"type": "integer", "default": 5},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "search_codebase",
                "description": "Search codebase for relevant code snippets",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "language": {"type": "string"},
                        "limit": {"type": "integer", "default": 5},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "find_similar_issues",
                "description": "Find similar resolved issues",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "issue_id": {"type": "string"},
                        "limit": {"type": "integer", "default": 5},
                    },
                    "required": ["issue_id"],
                },
            },
            {
                "name": "get_issue_history",
                "description": "Get issue activity history and linked PRs",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "issue_id": {"type": "string"},
                    },
                    "required": ["issue_id"],
                },
            },
        ]

    async def stream(
        self,
        input_data: AIContextInput,
        context: AgentContext,  # noqa: ARG002
    ) -> AsyncIterator[str]:
        """Execute AI context with streaming.

        Args:
            input_data: AI context input
            context: Agent execution context

        Yields:
            SSE chunks with context discoveries
        """
        # Implementation will use ClaudeSDKClient for streaming
        yield "Building AI context...\n"
        yield f"Issue: {input_data.issue_id}\n"
        yield "Searching for related content...\n"
