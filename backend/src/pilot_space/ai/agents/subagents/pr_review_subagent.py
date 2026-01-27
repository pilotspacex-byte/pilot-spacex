"""PR Review Subagent for multi-turn code review conversations.

Provides interactive PR review with:
- Architecture analysis
- Security scanning
- Code quality assessment
- Performance analysis
- Documentation review

Reference: docs/architect/ai-layer.md
Design Decision: DD-006 (Unified AI PR Review)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pilot_space.ai.agents.sdk_base import AgentContext, StreamingSDKBaseAgent

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@dataclass
class PRReviewInput:
    """Input for PR review subagent.

    Attributes:
        repository_id: Repository UUID
        pr_number: Pull request number
        include_architecture: Include architecture review
        include_security: Include security scanning
        include_performance: Include performance analysis
    """

    repository_id: UUID
    pr_number: int
    include_architecture: bool = True
    include_security: bool = True
    include_performance: bool = True


@dataclass
class PRReviewOutput:
    """Output from PR review.

    Attributes:
        summary: High-level review summary
        approval_status: APPROVED | CHANGES_REQUESTED | COMMENTED
        architecture_findings: Architecture-level concerns
        security_findings: Security vulnerabilities found
        code_quality_findings: Code quality issues
        performance_findings: Performance concerns
        documentation_findings: Documentation gaps
    """

    summary: str
    approval_status: str
    architecture_findings: list[dict[str, Any]]
    security_findings: list[dict[str, Any]]
    code_quality_findings: list[dict[str, Any]]
    performance_findings: list[dict[str, Any]]
    documentation_findings: list[dict[str, Any]]


class PRReviewSubagent(StreamingSDKBaseAgent[PRReviewInput, PRReviewOutput]):
    """Subagent for interactive PR review conversations.

    Provides multi-turn streaming review with Claude Agent SDK.
    Inherits from StreamingSDKBaseAgent for SSE support.

    Usage:
        subagent = PRReviewSubagent(...)
        async for chunk in subagent.execute_stream(input_data, context):
            yield chunk
    """

    AGENT_NAME = "pr_review_subagent"
    DEFAULT_MODEL = "claude-sonnet-4-20250514"

    def get_system_prompt(self) -> str:
        """Get system prompt for PR review.

        Returns:
            System prompt string with review guidelines
        """
        return """You are a senior software engineer conducting a thorough PR review.

Review the pull request across these dimensions:
1. **Architecture**: Design patterns, separation of concerns, maintainability
2. **Security**: OWASP vulnerabilities, authentication, authorization, data validation
3. **Code Quality**: Readability, naming, complexity, error handling
4. **Performance**: Algorithmic complexity, database queries, caching
5. **Documentation**: Code comments, API docs, README updates

For each finding:
- Severity: 🔴 CRITICAL | 🟡 WARNING | 🔵 SUGGESTION
- Location: File path and line number
- Rationale: Why this is an issue
- Fix: Specific code suggestion

Be constructive and specific. Focus on significant issues that impact
production reliability, security, or maintainability."""

    def get_tools(self) -> list[dict[str, Any]]:
        """Get MCP tools for PR review.

        Returns:
            List of tool definitions for GitHub and code analysis
        """
        return [
            {
                "name": "get_pr_diff",
                "description": "Get full diff for pull request",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "repository_id": {"type": "string"},
                        "pr_number": {"type": "integer"},
                    },
                    "required": ["repository_id", "pr_number"],
                },
            },
            {
                "name": "get_pr_files",
                "description": "Get list of changed files in PR",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "repository_id": {"type": "string"},
                        "pr_number": {"type": "integer"},
                    },
                    "required": ["repository_id", "pr_number"],
                },
            },
            {
                "name": "add_review_comment",
                "description": "Add inline comment to specific line in PR",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "repository_id": {"type": "string"},
                        "pr_number": {"type": "integer"},
                        "file_path": {"type": "string"},
                        "line_number": {"type": "integer"},
                        "severity": {"enum": ["critical", "warning", "suggestion"]},
                        "comment": {"type": "string"},
                        "fix_suggestion": {"type": "string"},
                    },
                    "required": [
                        "repository_id",
                        "pr_number",
                        "file_path",
                        "line_number",
                        "severity",
                        "comment",
                    ],
                },
            },
        ]

    async def stream(
        self,
        input_data: PRReviewInput,
        context: AgentContext,  # noqa: ARG002
    ) -> AsyncIterator[str]:
        """Execute PR review with streaming.

        Args:
            input_data: PR review input
            context: Agent execution context

        Yields:
            SSE chunks with review findings
        """
        # Implementation will use ClaudeSDKClient for streaming
        # For now, yield placeholder
        yield "Starting PR review...\n"
        yield f"Repository: {input_data.repository_id}\n"
        yield f"PR #{input_data.pr_number}\n"
