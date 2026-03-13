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

import json
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import structlog
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

from pilot_space.ai.agents.agent_base import AgentContext, StreamingSDKBaseAgent
from pilot_space.ai.context import clear_context, set_workspace_context
from pilot_space.ai.sdk.config import MODEL_SONNET, build_sdk_env

_logger = structlog.get_logger(__name__)

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
        partial_review: Whether this was a partial review
        files_reviewed: Number of files reviewed
        files_skipped: Number of files skipped
    """

    summary: str
    approval_status: str
    architecture_findings: list[dict[str, Any]]
    security_findings: list[dict[str, Any]]
    code_quality_findings: list[dict[str, Any]]
    performance_findings: list[dict[str, Any]]
    documentation_findings: list[dict[str, Any]]
    partial_review: bool = False
    files_reviewed: int = 0
    files_skipped: int = 0

    @property
    def approval_recommendation(self) -> str:
        """Alias for approval_status (backward compatibility)."""
        return self.approval_status

    @property
    def comments(self) -> list[dict[str, Any]]:
        """Flatten findings into comments list."""
        all_comments: list[dict[str, Any]] = []
        category_map = [
            (self.architecture_findings, "architecture"),
            (self.security_findings, "security"),
            (self.code_quality_findings, "quality"),
            (self.performance_findings, "performance"),
            (self.documentation_findings, "documentation"),
        ]
        for findings, category in category_map:
            for finding in findings:
                all_comments.append(
                    {
                        "file_path": finding.get("file_path", ""),
                        "line_number": finding.get("line_number", 0),
                        "end_line": finding.get("end_line"),
                        "severity": finding.get("severity", "info"),
                        "category": category,
                        "message": finding.get("message", ""),
                        "suggestion": finding.get("suggestion"),
                        "code_snippet": finding.get("code_snippet"),
                    }
                )
        return all_comments

    @property
    def critical_count(self) -> int:
        """Count of critical findings."""
        return sum(1 for c in self.comments if c.get("severity") == "critical")

    @property
    def warning_count(self) -> int:
        """Count of warning findings."""
        return sum(1 for c in self.comments if c.get("severity") == "warning")

    @property
    def suggestion_count(self) -> int:
        """Count of suggestion findings."""
        return sum(1 for c in self.comments if c.get("severity") == "suggestion")

    @property
    def info_count(self) -> int:
        """Count of info findings."""
        return sum(1 for c in self.comments if c.get("severity") == "info")


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
    DEFAULT_MODEL = MODEL_SONNET

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

        Registered tool names from github_tools.py via @register_tool("github"):
        - get_pr_details: PR metadata (title, author, labels, merge status)
        - get_pr_diff: Changed files with unified diff patches
        - post_pr_comment: Post general or line-specific review comment

        Returns:
            List of tool definitions for GitHub code review
        """
        return [
            {
                "name": "get_pr_details",
                "description": "Get pull request metadata including title, description, author, and merge status",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pr_number": {"type": "integer"},
                        "integration_id": {"type": "string"},
                    },
                    "required": ["pr_number"],
                },
            },
            {
                "name": "get_pr_diff",
                "description": "Get changed files with unified diff patches for code review analysis",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pr_number": {"type": "integer"},
                        "integration_id": {"type": "string"},
                    },
                    "required": ["pr_number"],
                },
            },
            {
                "name": "post_pr_comment",
                "description": "Post a general or line-specific review comment on the pull request",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pr_number": {"type": "integer"},
                        "body": {"type": "string"},
                        "integration_id": {"type": "string"},
                        "path": {"type": "string"},
                        "line": {"type": "integer"},
                    },
                    "required": ["pr_number", "body"],
                },
            },
        ]

    async def _get_api_key(self, workspace_id: UUID | None) -> str:
        """Get Anthropic API key for this request.

        AIGOV-05 BYOK enforcement:
        - workspace_id provided → BYOK required; raises AINotConfiguredError if missing.
          No env fallback — using the platform key for workspace calls violates BYOK.
        - workspace_id=None → system agent; env key permitted.

        Args:
            workspace_id: Workspace UUID, or None for system-level operations.

        Returns:
            Decrypted API key string.

        Raises:
            AINotConfiguredError: If workspace has no BYOK key or system has no env key.
        """
        from pilot_space.ai.exceptions import AINotConfiguredError

        if workspace_id is not None:
            # Workspace-scoped call: BYOK required, no env fallback (AIGOV-05).
            # TODO Phase 4 (04-07): Wire key_storage via DI; for now raise immediately
            # when workspace_id is provided and there's no env override for tests.
            raise AINotConfiguredError(workspace_id=workspace_id)

        # System-only: env key permitted
        api_key = os.getenv("ANTHROPIC_API_KEY")  # _SYSTEM_ONLY: never for workspace calls
        if not api_key:
            raise AINotConfiguredError(workspace_id=None)
        return api_key

    def _build_prompt(self, input_data: PRReviewInput) -> str:
        """Build PR review prompt from input data.

        Args:
            input_data: PR review input

        Returns:
            Formatted prompt string
        """
        review_dimensions = []
        if input_data.include_architecture:
            review_dimensions.append("architecture analysis")
        if input_data.include_security:
            review_dimensions.append("security scanning")
        if input_data.include_performance:
            review_dimensions.append("performance analysis")

        dimensions_str = (
            ", ".join(review_dimensions) if review_dimensions else "comprehensive review"
        )

        return f"""Review Pull Request #{input_data.pr_number} in repository {input_data.repository_id}.

Focus on: {dimensions_str}

Provide detailed findings with:
- Severity level (🔴 CRITICAL | 🟡 WARNING | 🔵 SUGGESTION)
- File path and line number
- Clear rationale
- Specific fix recommendations

Use available tools to:
1. Call get_pr_details to retrieve PR metadata (title, author, labels)
2. Call get_pr_diff to retrieve changed files with unified diff patches
3. Call post_pr_comment to post inline or general review comments
4. Call search_code_in_repo to look up related code context

Be constructive and focus on production reliability, security, and maintainability."""

    def _create_agent_options(self, context: AgentContext) -> ClaudeAgentOptions:
        """Create Claude SDK options for PR review.

        Builds a "github" MCP server from the db_session stored in
        context.metadata["db_session"] (set by the router) so the agent
        can call mcp__github__* tools backed by real GitHubClient calls.

        Args:
            context: Agent execution context (metadata["db_session"] required)

        Returns:
            ClaudeAgentOptions configured for PR review
        """
        from pilot_space.ai.mcp.github_server import create_github_tools_server
        from pilot_space.ai.tools.mcp_server import ToolContext

        db_session = context.metadata.get("db_session")
        mcp_servers = {}
        if db_session is not None:
            tool_context = ToolContext(
                db_session=db_session,
                workspace_id=str(context.workspace_id),
                user_id=str(context.user_id),
            )
            mcp_servers["github"] = create_github_tools_server(tool_context)

        return ClaudeAgentOptions(  # type: ignore[call-arg]
            model=self.DEFAULT_MODEL,
            allowed_tools=[
                "mcp__github__get_pr_details",
                "mcp__github__get_pr_diff",
                "mcp__github__post_pr_comment",
            ],
            mcp_servers=mcp_servers,  # type: ignore[arg-type]
            setting_sources=["project"],  # type: ignore[call-arg]
        )

    def _transform_sdk_message(self, message: Any, context: AgentContext) -> str | None:
        """Transform Claude SDK message to SSE event.

        Handles real Claude Agent SDK message types:
        - SystemMessage: skip (init event)
        - AssistantMessage: content is list[TextBlock]
        - ResultMessage: completion signal

        Args:
            message: SDK message object (SystemMessage | AssistantMessage | ResultMessage)
            context: Agent execution context

        Returns:
            SSE-formatted string or None if message should be ignored
        """
        msg_type = type(message).__name__

        # SystemMessage: skip (init event)
        if msg_type == "SystemMessage":
            return None

        # AssistantMessage: content is list[TextBlock]
        if msg_type == "AssistantMessage":
            content = getattr(message, "content", None)
            if content is None:
                return None
            if isinstance(content, list):
                parts = []
                for block in content:
                    if isinstance(block, dict):
                        parts.append(block.get("text", ""))
                    elif hasattr(block, "text"):
                        parts.append(block.text)
                text_content = " ".join(parts)
            else:
                text_content = str(content)
            if not text_content.strip():
                return None
            return f"event: text_delta\ndata: {json.dumps({'messageId': str(uuid4()), 'delta': text_content})}\n\n"

        # ResultMessage: completion
        if msg_type == "ResultMessage":
            return f"event: message_stop\ndata: {json.dumps({'messageId': str(uuid4()), 'stopReason': 'end_turn'})}\n\n"

        return None

    async def stream(
        self,
        input_data: PRReviewInput,
        context: AgentContext,
    ) -> AsyncIterator[str]:
        """Execute PR review with streaming.

        Args:
            input_data: PR review input
            context: Agent execution context

        Yields:
            SSE chunks with review findings
        """
        try:
            # Get API key from context
            api_key = await self._get_api_key(context.workspace_id)

            # Build prompt specific to PR review
            prompt = self._build_prompt(input_data)

            # Create SDK options with env parameter (no os.environ mutation)
            sdk_options = self._create_agent_options(context)
            sdk_options.env = build_sdk_env(api_key)

            # Set context for observability
            set_workspace_context(context.workspace_id, context.user_id)

            client = ClaudeSDKClient(sdk_options)
            try:
                await client.connect()
                await client.query(prompt)
                async for message in client.receive_response():
                    sse_event = self._transform_sdk_message(message, context)
                    if sse_event:
                        yield sse_event
            finally:
                await client.disconnect()
                clear_context()

        except Exception:
            _logger.exception("pr_review_subagent_error")
            error_data = {
                "type": "error",
                "error_type": "pr_review_error",
                "message": "PR review failed. Please try again.",
            }
            yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
